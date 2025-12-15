package main

import (
	"net/http"
    "github.com/gin-gonic/gin"
	"time"
	"strconv"
	"strings"
	"sync"
	"os"
)

var spaces = make(map[string]space)
var rwmu sync.RWMutex

type space struct {
	SpaceID			string		`json:"spaceID" binding:"required"`
	RoomCode		int			`json:"roomCode" binding:"required"`
	BuildingCode	string		`json:"buildingCode" binding:"required"`
	Capacity 		int			`json:"capacity"` // default behavior is no limit
	OpenTime		time.Time	`json:"openTime"`
	CloseTime		time.Time	`json:"closeTime"`
	// TODO: MAKE THESE STRINGS, we only care about H:M:S
	// For now, we say time does not matter
}

type err struct {
    ErrCode  string
    Message string
    Details string
}

var SPACE_CAPACITY = 100000000000 // optional way to limit space traffic and max users

// var SERVER_ADDRESS = ""

var USER_SERVICE = os.Getenv("USER_SERVICE_URL")
var AVAIL_SERVICE = os.Getenv("AVAIL_SERVICE_URL")

func main() {
	router := gin.Default()

	router.GET("/space/health", func(c *gin.Context) {
    c.String(200, "OK")
    })
	router.POST("/space", createSpace)
	router.GET("/space/:spaceId", getSpaceById)

	router.Run(":8080")
}

func readSpace(spaceId string) (space, bool) {
	rwmu.RLock()
    value, exists := spaces[spaceId]
	rwmu.RUnlock()

	return value, exists
}

func writeSpace(spaceId string, space space) {
	rwmu.Lock()
    spaces[spaceId] = space
	rwmu.Unlock()
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
		e := err{ErrCode: "SESSION EXPIRED", Message: "user session has expired", Details: "Please log in again and revalidate credentials"}
        return e
	}
	defer resp.Body.Close()
	if (resp.StatusCode != 200) {
		e := err{ErrCode: "SESSION EXPIRED", Message: "user session has expired", Details: "Please log in again and revalidate credentials"}
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
    _, exists := readSpace(spaceID)

	// Limit the number of total spaces, replicable with Dynamo DB ?
    if (exists) {
        e := err{ErrCode: "DUPLICATE", Message: "Space already exists", Details: "This space already exists"}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
    }

	if (len(spaces) == SPACE_CAPACITY) {
        e := err{ErrCode: "CAPACITY", Message: "Too many spaces", Details: "Max spaces reached. Wait and retry"}
        c.IndentedJSON(http.StatusInternalServerError, e)
        return
    }

	// Define a user with the new space ID
	newSpace := space{SpaceID: spaceID, RoomCode: tempSpace.RoomCode, BuildingCode: tempSpace.BuildingCode, Capacity: tempSpace.Capacity, OpenTime: tempSpace.OpenTime, CloseTime: tempSpace.CloseTime}
    writeSpace(spaceID, newSpace)
    c.IndentedJSON(http.StatusCreated, spaceID)
    return

}

// INPUT: Space ID
func getSpaceById(c *gin.Context) {
	// Parameter input: spaceId
	spaceId := c.Param("spaceId")

	// check if a user of the provided ID exists
	value, found := readSpace(spaceId)
	if (!found) {
        e := err{ErrCode: "NOT_FOUND", Message: "Space Not Found", Details: "The provided space id does not exist"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

    c.IndentedJSON(http.StatusOK, value)
    return

}
