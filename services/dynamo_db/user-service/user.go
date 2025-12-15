package main

import (
	"net/http"
    "github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
	"math/rand"
	"sync"
	"time"
	"context"
	"strconv"

	"fmt"
	"github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

//	"services-shared/myutility"

)

var users = make(map[int]user)
var rwmu sync.RWMutex
var TABLE_NAME = "UsersTable"

type user struct {
	UserId		int 		`dynamodbav:"userId" json:"userId" binding:"required"`
	Username	string		`dynamodbav:"username" json:"username" binding:"required"`
	Email		string		`dynamodbav:"userEmail" json:"userEmail"`
	Password	string		`dynamodbav:"userPassword" json:"userPassword" binding:"required"`
	LastAuth	time.Time 	`dynamodbav:"lastAccess" json:"lastAccess"`
}


type err struct {
    ErrCode  string
    Message string
    Details string
}

var USER_CAPACITY = 100000000000 // optional way to limit user traffic and max users

func main() {
	router := gin.Default()

	router.GET("/user/health", func(c *gin.Context) {
    	c.String(200, "OK")
    })

	router.POST("/user", createUser)
	router.POST("/user/:userId", loginUser)
	router.GET("/user/:userId", validateUserSession)

	router.Run(":8080")
}

func getDynamoDbConfig() (*dynamodb.Client, err) {
    cfg, er := config.LoadDefaultConfig(context.TODO(),
        config.WithRegion("us-east-1"),
    )
    if er != nil {
        e := err{ErrCode: "INPUT_ERR", Message: "Unable to extract Dynamo DB Configuration", Details: er.Error()}
        return nil, e
    }
    client := dynamodb.NewFromConfig(cfg)
    return client, err{}
}

func getUser(userId int) (*dynamodb.GetItemOutput, err) {
	client, _ := getDynamoDbConfig()

	result, er := client.GetItem(context.TODO(), &dynamodb.GetItemInput{
        TableName: aws.String(TABLE_NAME),
        Key: map[string]types.AttributeValue{
            "userId": &types.AttributeValueMemberN{Value: strconv.Itoa(userId)},
        },
    })

	if er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "Unable to find user with provided key", Details: er.Error()}
        return nil, e
    }

    return result, err{}

}

func existsAndReturn(userId int) (bool, user, err) {
    result, e := getUser(userId)

	if e != (err{}) {
        return false, user{}, e
    }

    if result.Item == nil {
        return false, user{}, err{}
    }

	var u user
	_ = attributevalue.UnmarshalMap(result.Item, &u)

    return true, u, err{}
}

func checkItemExists(userId int) (bool) {
    result, e := getUser(userId)

    if e != (err{}) {
        return false
    }

    if result.Item == nil {
        return false
    }
    return true
}

func addItemToTable(newUser user) (map[string]types.AttributeValue, err) {
    // Get Dynamo DB AWS configuration
    client, _ := getDynamoDbConfig()

    // Marshal
    item, er := attributevalue.MarshalMap(newUser)
    if er != nil {
        e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema", Details: er.Error()}
        return nil, e
    }

    // Add to table
    result, er := client.PutItem(context.TODO(), &dynamodb.PutItemInput{
        TableName: aws.String(TABLE_NAME),
        Item:      item,
    })
    if er != nil {
        e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema", Details: er.Error()}
        return nil, e
    }

    return result.Attributes, err{}
}

func hashPassword(password string) (string, error) {
    bytes, err := bcrypt.GenerateFromPassword([]byte(password), 14)
    return string(bytes), err
}

func verifyPassword(password, hash string) error {
    err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
    return err
}

func validateUserSession(c *gin.Context) {
	// Parameter input: user ID
	idStr := c.Param("userId")

	// Implicit input: current time
	currTime := time.Now()

	// conversion to int
    userId, er := strconv.Atoi(idStr) // Convert string "123" to int 123
	if er != nil {
		e := err{ErrCode: "INPUT_ERROR", Message: "Unable to detect a user id", Details: er.Error()}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
	}

	// check if a user of the provided ID exists
	found, value, _ := existsAndReturn(userId)
	if (!found) {
        e := err{ErrCode: "NOT_FOUND", Message: "User Not Found", Details: "The provided user id does not exist"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

	// Get last access time PLUS ONE HOUR = session expiry time
	lastAuthExpiry := value.LastAuth.Add(time.Hour)

	if (currTime.After(lastAuthExpiry)) {
		e := err{ErrCode: "EXPIRED", Message: "Last Session Expired", Details: "Last Authorization Expired, please try again"}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
	} else {
		c.IndentedJSON(http.StatusOK, "Session has not yet expired")
    	return
	}

}

// INPUT: username, password; userId (param)
func loginUser(c *gin.Context) {
	// Parameter input: user ID
	idStr := c.Param("userId")

	// Body input: username, password
	type userTemp struct {
		Username	string	`json:"username" binding:"required"`
		Password	string	`json:"userPassword" binding:"required"`
	}

	// conversion to int
    userId, er := strconv.Atoi(idStr) // Convert string "123" to int 123
	if er != nil {
		e := err{ErrCode: "INPUT_ERROR", Message: "Unable to detect a user id", Details: er.Error()}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
	}

	// Conversion to userTemp
	var tempUser userTemp
	if er := c.BindJSON(&tempUser); er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema for a user", Details: "You must provide a username and password"}
		c.IndentedJSON(http.StatusBadRequest, e)
		return
	}

	// check if a user of the provided ID exists
	found, value, _ := existsAndReturn(userId)
	if (!found) {
        e := err{ErrCode: "NOT_FOUND", Message: "User Not Found", Details: "The provided user id does not exist"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

	// validate provided username
	if (value.Username != tempUser.Username) {
		e := err{ErrCode: "NOT_FOUND", Message: "Username Not Found", Details: "The provided username does not exist for the given user id"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
	}

	// validate provided username (value password is hashed)
	if er := verifyPassword(tempUser.Password, value.Password); er != nil {
		e := err{ErrCode: "INVALID", Message: "Password Does Not Match", Details: er.Error()}
        c.IndentedJSON(http.StatusNotFound, e)
        return
	}

	// Update last access time - use update instead of writing straight to object
	newUser := user{UserId: value.UserId, Username: value.Username, Email: value.Email, Password: value.Password, LastAuth: time.Now()}
    _, e := addItemToTable(newUser)
	if e != (err{}) {
        c.IndentedJSON(http.StatusInternalServerError, e)
	}

	returnString := fmt.Sprintf("[%v] session created. Valid from %v to %v", userId, newUser.LastAuth, newUser.LastAuth.Add(time.Hour))

	c.IndentedJSON(http.StatusOK, returnString)
    return
}

// INPUT: username, password, email (optional)
func createUser(c *gin.Context) {
	// Define temporary user struct without a user ID and unmarshall
	type userTemp struct {
		Username	string	`json:"username" binding:"required"`
		Email		string	`json:"userEmail"`
		Password	string	`json:"userPassword" binding:"required"`
	}

	var tempUser userTemp

	if er := c.BindJSON(&tempUser); er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema for a new user", Details: "A new user requires a username and password"}
		c.IndentedJSON(http.StatusBadRequest, e)
		return
	}

	// Randomly generate a user ID, ensuring that it does not exist
	userId := rand.Intn(USER_CAPACITY-1)

    exists := checkItemExists(userId)

	// Limit the number of total users, replicable with Dynamo DB ?
    for (exists) {
        userId := rand.Intn(USER_CAPACITY-1)
    	exists = checkItemExists(userId)
    }

	if (len(users) == USER_CAPACITY) {
        e := err{ErrCode: "CAPACITY", Message: "Too many users", Details: "Max users reached. Wait and retry"}
        c.IndentedJSON(http.StatusInternalServerError, e)
        return
    }

	// Define password hash to use
	hashedPassword, er := hashPassword(tempUser.Password)
	if er != nil {
		e := err{ErrCode: "HASH ERROR", Message: "Unable to hash provided password", Details: er.Error()}
        c.IndentedJSON(http.StatusInternalServerError, e)
	}

	// Define a user with the new user ID
	newUser := user{UserId: userId, Username: tempUser.Username, Email: tempUser.Email, Password: hashedPassword, LastAuth: time.Now()}
    _, e := addItemToTable(newUser)
	if e != (err{}) {
        c.IndentedJSON(http.StatusInternalServerError, e)
	}

    c.IndentedJSON(http.StatusCreated, userId)
    return
}