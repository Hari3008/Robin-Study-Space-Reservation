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
	"encoding/json"

	"github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/go-redis/redis/v8"
)

var spaces = make(map[string]space)
var rwmu sync.RWMutex
var TABLE_NAME = "SpacesTable"

// Redis variables
var redisClient *redis.Client
var ctx = context.Background()

type space struct {
	SpaceID			string		`dynamodbav:"spaceID" json:"spaceID" binding:"required"`
	RoomCode		int			`dynamodbav:"roomCode" json:"roomCode" binding:"required"`
	BuildingCode	string		`dynamodbav:"buildingCode" json:"buildingCode" binding:"required"`
	Capacity 		int			`dynamodbav:"capacity" json:"capacity"`
	OpenTime		time.Time	`dynamodbav:"openTime" json:"openTime"`
	CloseTime		time.Time	`dynamodbav:"closeTime" json:"closeTime"`
}

type err struct {
    ErrCode  string
    Message string
    Details string
}

var SPACE_CAPACITY = 100000000000
var USER_SERVICE = os.Getenv("USER_SERVICE_URL")

func initRedis() {
    redisEndpoint := os.Getenv("REDIS_ENDPOINT")
    if redisEndpoint == "" {
        fmt.Println("REDIS_ENDPOINT not set, running without cache")
        return
    }
    
    redisClient = redis.NewClient(&redis.Options{
        Addr:     redisEndpoint,  // e.g. "your-cluster.cache.amazonaws.com:6379"
        Password: "",
        DB:       0,
        PoolSize: 10,
    })
    
    _, er := redisClient.Ping(ctx).Result()
    if er != nil {
        fmt.Printf("Redis connection failed, continuing without cache: %v\n", er)
        redisClient = nil
    } else {
        fmt.Println("Redis connected successfully")
    }
}

func main() {
	// Initialize Redis
	initRedis()
	
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

	// Generate space ID
	spaceID := strings.Replace((tempSpace.BuildingCode + "-" + strconv.Itoa(tempSpace.RoomCode)), " ", "_", -1)
	exists := checkItemExists(spaceID)

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

	// Create new space
	newSpace := space{
		SpaceID: spaceID, 
		RoomCode: tempSpace.RoomCode, 
		BuildingCode: tempSpace.BuildingCode, 
		Capacity: tempSpace.Capacity, 
		OpenTime: tempSpace.OpenTime, 
		CloseTime: tempSpace.CloseTime,
	}
	
	_, e := addItemToTable(newSpace)
	if e != (err{}) {
        c.IndentedJSON(http.StatusBadRequest, e)
		return
	}
	
	// Clear cache for this space if it exists (invalidation)
	if redisClient != nil {
		cacheKey := fmt.Sprintf("space:%s", spaceID)
		redisClient.Del(ctx, cacheKey).Err()
	}
	
    c.IndentedJSON(http.StatusCreated, spaceID)
    return
}

func getSpaceById(c *gin.Context) {
	spaceId := c.Param("spaceId")
	
	// Try Redis cache first
	if redisClient != nil {
		cacheKey := fmt.Sprintf("space:%s", spaceId)
		cached, er := redisClient.Get(ctx, cacheKey).Result()
		if er == nil {
			// Cache hit - parse and return
			var cachedSpace space
			if json.Unmarshal([]byte(cached), &cachedSpace) == nil {
				// Log cache hit for monitoring
				fmt.Printf("Cache hit for space: %s\n", spaceId)
				c.IndentedJSON(http.StatusOK, cachedSpace)
				return
			}
		} else if er != redis.Nil {
			// Log Redis error but continue
			fmt.Printf("Redis error: %v\n", er)
		}
	}
	
	// Cache miss or no Redis - get from DynamoDB
	found, value, e := existsAndReturn(spaceId)
	if (!found) {
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }
	
	// Store in cache for next time (1 hour TTL)
	if redisClient != nil {
		jsonData, er := json.Marshal(value)
		if er == nil {
			cacheKey := fmt.Sprintf("space:%s", spaceId)
			// Set with 1 hour TTL
			er := redisClient.Set(ctx, cacheKey, jsonData, time.Hour).Err()
			if er != nil {
				fmt.Printf("Failed to cache space %s: %v\n", spaceId, er)
			} else {
				fmt.Printf("Cached space: %s\n", spaceId)
			}
		}
	}

    c.IndentedJSON(http.StatusOK, value)
    return
}
