package main

import (
	"net/http"
    "github.com/gin-gonic/gin"
	"time"
	"strconv"
	"strings"
	"sync"
	"context"
	"os"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

var spaces = make(map[string]space)
var rwmu sync.RWMutex
var TABLE_NAME = "SpacesTable"

type space struct {
	SpaceID			string		`dynamodbav:"spaceID" json:"spaceID" binding:"required"`
	RoomCode		int			`dynamodbav:"roomCode" json:"roomCode" binding:"required"`
	BuildingCode	string		`dynamodbav:"buildingCode" json:"buildingCode" binding:"required"`
	Capacity 		int			`dynamodbav:"capacity" json:"capacity"` // default behavior is no limit
	OpenTime		time.Time	`dynamodbav:"openTime" json:"openTime"`
	CloseTime		time.Time	`dynamodbav:"closeTime" json:"closeTime"`
	// TODO: MAKE THESE STRINGS, we only care about H:M:S
	// For now, we say time does not matter
}

type err struct {
    ErrCode  string
    Message string
    Details string
}

var SPACE_CAPACITY = 100000000000 // optional way to limit space traffic and max users

var USER_SERVICE = os.Getenv("USER_SERVICE_URL")

func main() {
	router := gin.Default()

	router.GET("/space/health", func(c *gin.Context) {
    c.String(200, "OK")
    })
	router.POST("/space", createSpace)
	router.GET("/space/:spaceId", getSpaceById)

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

func getSpace(spaceId string) (*dynamodb.GetItemOutput, err) {
	client, _ := getDynamoDbConfig()

	result, er := client.GetItem(context.TODO(), &dynamodb.GetItemInput{
        TableName: aws.String(TABLE_NAME),
        Key: map[string]types.AttributeValue{
            "spaceID": &types.AttributeValueMemberS{Value: spaceId},
        },
    })

	if er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "Unable to find space with provided key", Details: er.Error()}
        return nil, e
    }

    return result, err{}
}

func existsAndReturn(spaceId string) (bool, space, err) {
    result, e := getSpace(spaceId)

	if e != (err{}) {
        return false, space{}, e
    }

    if result.Item == nil {
		e := err{ErrCode: "NOT_FOUND", Message: "Space Not Found", Details: "The provided space id does not exist"}
        return false, space{}, e
    }

	var s space
	_ = attributevalue.UnmarshalMap(result.Item, &s)

    return true, s, err{}
}

func checkItemExists(spaceId string) (bool) {
    result, e := getSpace(spaceId)

    if e != (err{}) {
        return false
    }

    if result.Item == nil {
        return false
    }
    return true
}


func addItemToTable(newSpace space) (map[string]types.AttributeValue, err) {
    // Get Dynamo DB AWS configuration
    client, _ := getDynamoDbConfig()

    // Marshal
    item, er := attributevalue.MarshalMap(newSpace)
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

func authorizeUser(username string, userId string, ok bool, mustBeAdmin bool) err {
	// FOR NOW - allow password to be empty, since we only check if the session has expired

	// if request is malformed
	if !ok {
		e := err{ErrCode: "MALFORMED", Message: "basic auth is missing or malformed", Details: "ensure that a username and/or password are provided"}
		return e	
	}

	// if user is not an admin
	if (mustBeAdmin && strings.ToLower(username) != "admin") {
		e := err{ErrCode: "UNAUTHORIZED", Message: "Not an admin", Details: "Only admin users can use this operation"}
		return e
	}

	url := USER_SERVICE + "/" + userId
	resp, er := http.Get(url)
    if er != nil {
		e := err{ErrCode: "SESSION ERROR", Message: fmt.Sprintf("Unable to fetch a valid session from %v", url), Details: er.Error()}
        return e
	}
	defer resp.Body.Close()
	if (resp.StatusCode != 200) {
		e := err{ErrCode: "SESSION EXPIRED", Message: "user session has expired", Details: er.Error()}
        return e
	}

	return err{}
}

// INPUT: Space Name
func createSpace(c *gin.Context) {
	// Authorize that user is logged in and an admin
	username, userId, ok := c.Request.BasicAuth()
	if er := authorizeUser(username, userId, ok, true); er != (err{}) {
		c.IndentedJSON(http.StatusBadRequest, er)
		return
	}

	// Define temporary space struct without a space ID and unmarshall
	type spaceTemp struct {
		RoomCode		int			`json:"roomCode" binding:"required"`
		BuildingCode	string		`json:"buildingCode" binding:"required"`
		Capacity		int			`json:"capacity"`
		OpenTime		time.Time	`json:"openTime"`
		CloseTime		time.Time	`json:"closeTime"`
	}

	var tempSpace spaceTemp

	if er := c.BindJSON(&tempSpace); er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema for a new space", Details: "A new space requires a building and room"}
		c.IndentedJSON(http.StatusBadRequest, e)
		return
	}

	// Randomly generate a space ID, ensuring that it does not exist
	spaceID := strings.Replace((tempSpace.BuildingCode + "-" + strconv.Itoa(tempSpace.RoomCode)), " ", "_", -1)
	exists := checkItemExists(spaceID)

	// Limit the number of total spaces, replicable with Dynamo DB ?
    if (exists) {
        e := err{ErrCode: "DUPLICATE", Message: "Space already exists", Details: "This space already exists"}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
    }

	if (len(spaces) == SPACE_CAPACITY) {
        e := err{ErrCode: "CAPACITY", Message: "Too many spaces", Details: "Max spaces reached. Wait and retry"}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
    }

	// Define a user with the new space ID
	newSpace := space{SpaceID: spaceID, RoomCode: tempSpace.RoomCode, BuildingCode: tempSpace.BuildingCode, Capacity: tempSpace.Capacity, OpenTime: tempSpace.OpenTime, CloseTime: tempSpace.CloseTime}
	_, e := addItemToTable(newSpace)
	if e != (err{}) {
        c.IndentedJSON(http.StatusBadRequest, e)
	}
    c.IndentedJSON(http.StatusCreated, spaceID)
    return

}

// INPUT: Space ID
func getSpaceById(c *gin.Context) {
	// Parameter input: spaceId
	spaceId := c.Param("spaceId")

	// conversion to int
    // spaceId, er := strconv.Atoi(idStr) // Convert string "123" to int 123
	// if er != nil {
	// 	e := err{ErrCode: "INPUT_ERROR", Message: "Unable to detect a space id", Details: er.Error()}
    //     c.IndentedJSON(http.StatusBadRequest, e)
    //     return
	// }

	// check if a user of the provided ID exists
	found, value, e := existsAndReturn(spaceId)
	if (!found) {
        
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

    c.IndentedJSON(http.StatusOK, value)
    return

}
