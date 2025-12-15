package main

import (
	"net/http"
    "github.com/gin-gonic/gin"
	"time"
	"strconv"
	"strings"
	"sync"
	"math/rand"
	"io"
	"encoding/json"
	"os"
)

// Map of { Date1: {Booking1: Booking, B2: Booking2}, D2: {}, ...}
var bookings = make(map[string](map[int]booking))

var rwmu sync.RWMutex

type booking struct {
	BookingID		int			`json:"bookingID" binding:"required"`
	SpaceID			string		`json:"spaceID" binding:"required"`
	Date			string		`json:"date" binding:"required"` // "YYYY-MM-DD"
	UserID 			int			`json:"userID" binding:"required"`
	Occupants 		int			`json:"occupants" binding:"required"` // default behavior is no limit
	StartTime		time.Time	`json:"startTime" binding:"required"`
	EndTime			time.Time	`json:"endTime" binding:"required"`
}

type err struct {
    ErrCode  string
    Message string
    Details string
}

var BOOKING_CAPACITY = 100000000000 // optional way to limit space traffic and max users
// var SERVER_ADDRESS = "localhost"
var USER_SERVICE = os.Getenv("USER_SERVICE_URL")
var AVAIL_SERVICE = os.Getenv("AVAIL_SERVICE_URL")

func main() {
	router := gin.Default()

	router.GET("/booking/health", func(c *gin.Context) {
    c.String(200, "OK")
    })
	router.POST("/booking", createBooking)
	router.GET("/booking/:date/:bookingId", getBooking)
	router.DELETE("/booking/:date/:bookingId", deleteBooking)
	// update reservation

	router.Run(":8080")
}

func readBookingDate(date string) (map[int]booking, bool) {
	rwmu.RLock()
    bookByDay, exists := bookings[date]
	rwmu.RUnlock()

	return bookByDay, exists
}

func readBooking(date string, bookingId int) (booking, bool) {
	rwmu.RLock()
    bookByDay, exists := bookings[date]

	if (!exists) {
		return booking{}, false
	}

	value, exists := bookByDay[bookingId]

	rwmu.RUnlock()

	return value, exists
}

func writeBooking(date string, bookingId int, space booking) {
	
	_, exists := readBookingDate(date)

	if !(exists) {
		bookings[date] = make(map[int]booking)
		bookings[date][bookingId] = space
	} else {
		bookings[date][bookingId] = space
	}

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

func validateBooking(booking booking) err {
	url := AVAIL_SERVICE + "/" + booking.SpaceID
	resp, er := http.Get(url)
    if er != nil {
		e := err{ErrCode: "INVALID SPACE", Message: "Space ID is invalid", Details: "Please provide a valid space id"}
        return e
	}
	defer resp.Body.Close()

	if (resp.StatusCode != 200) {
		e := err{ErrCode: "INVALID SPACE", Message: "Space ID is invalid", Details: "Please provide a valid space id"}
        return e
	}

	// Read the response body
	type spaceTemp struct {
		SpaceID			string		`json:"spaceID" binding:"required"`
		RoomCode		int			`json:"roomCode" binding:"required"`
		BuildingCode	string		`json:"buildingCode" binding:"required"`
		Capacity		int			`json:"capacity"`
		OpenTime		time.Time	`json:"openTime"`
		CloseTime		time.Time	`json:"closeTime"`
	}
	var tempSpace spaceTemp

	body, er := io.ReadAll(resp.Body)
	if er != nil {
		e := err{ErrCode: "INVALID", Message: "Error reading response body", Details: er.Error()}
        return e
	}
	er = json.Unmarshal(body, &tempSpace)
	if er != nil {
		e := err{ErrCode: "INVALID", Message: "Error reading response body", Details: er.Error()}
        return e
	}

	// check number of occupants
	if booking.Occupants > tempSpace.Capacity {
		e := err{ErrCode: "INVALID", Message: "Too many occupants", Details: "Space capacity exceeded"}
        return e
	} 

	// check start and end time
	if !correctTimeOrder(tempSpace.OpenTime, booking.StartTime) && !correctTimeOrder(booking.EndTime, tempSpace.CloseTime) {
		e := err{ErrCode: "INVALID", Message: "Building not open", Details: "Time constraints not met"}
        return e
	}
	return err{}
}

func correctTimeOrder(timeBefore time.Time, timeAfter time.Time) bool {
	if (timeBefore.Hour() != timeAfter.Hour()) { // 9 < 10
		// fmt.Printf("%v less than %v", timeBefore.Hour(), timeAfter.Hour())
		return timeBefore.Hour() < timeAfter.Hour()
	} else if (timeBefore.Minute() != timeAfter.Minute()) { // 00 < 30
		// fmt.Printf("%v less than %v", timeBefore.Minute(), timeAfter.Minute())
		return timeBefore.Minute() < timeAfter.Minute()
	} else if (timeBefore.Second() != timeAfter.Second()) { // 
		// fmt.Printf("%v less than %v", timeBefore.Second(), timeAfter.Second())
		return timeBefore.Second() < timeAfter.Second()
	} 
	return true

}

func createBooking(c *gin.Context) {
	//Get user ID, confirm authorization
	// Authorize that user is logged in
	username, userId, ok := c.Request.BasicAuth()
	if er := authorizeUser(username, userId, ok, false); er != (err{}) {
		c.IndentedJSON(http.StatusBadRequest, er)
		return
	}

	//Create temp booking with all but booking ID
	type bookingTemp struct {
		SpaceID			string		`json:"spaceID" binding:"required"`
		Date			string		`json:"date" binding:"required"` // "YYYY-MM-DD"
		UserID 			int			`json:"userID" binding:"required"`
		Occupants 		int			`json:"occupants" binding:"required"` // default behavior is no limit
		StartTime		time.Time	`json:"startTime" binding:"required"`
	EndTime			time.Time	`json:"endTime" binding:"required"`
	}
	var tempBooking bookingTemp

	if er := c.BindJSON(&tempBooking); er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema for a new booking", Details: "A new space requires a space, date, user, occupants, start, and end time"}
		c.IndentedJSON(http.StatusBadRequest, e)
		return
	}

	// Verify user is logged in user
	if strconv.Itoa(tempBooking.UserID) != userId {
		e := err{ErrCode: "INPUT_ERR", Message: "User ID does not match", Details: "Can only create a reservation for yourself"}
		c.IndentedJSON(http.StatusBadRequest, e)
		return
	}

	// Verify date is in format 'YYYY-MM-DD'
	if _, er := time.Parse("2006-01-02", tempBooking.Date); er != nil {
		e := err{ErrCode: "INPUT_ERR", Message: "Date must be formatted as YYYY-MM-DD", Details: er.Error()}
		c.IndentedJSON(http.StatusBadRequest, e)
		return
	}

	// Check booking validity against availability service

	//Get all bookings with matching date
	// filter out bookings with a matching space id
	bookingsByDay, dayExists := readBookingDate(tempBooking.Date)
	
	if (dayExists) {
	// for each booking
		for _, b := range bookingsByDay {
			if (b.SpaceID != tempBooking.SpaceID) {
				continue
			}
			if (tempBooking.StartTime.Before(b.EndTime) || tempBooking.EndTime.After(b.StartTime)) {
				e := err{ErrCode: "CONFLICT", Message: "Scheduling conflict", Details: "Your booking overlaps with another"}
				c.IndentedJSON(http.StatusBadRequest, e)
				return
			}
		}
	}
	
	// Generate booking ID
	// Iterate until booking ID is unique
	// Check booking capacity
	// Randomly generate a space ID, ensuring that it does not exist
	bookingId := rand.Intn(BOOKING_CAPACITY-1)
    _, exists := readBooking(tempBooking.Date, bookingId)

	// Limit the number of total spaces, replicable with Dynamo DB ?
    for (exists) {
        bookingId := rand.Intn(BOOKING_CAPACITY-1)
    	_, exists = readBooking(tempBooking.Date, bookingId)
    }

	if (len(bookings) == BOOKING_CAPACITY) {
        e := err{ErrCode: "CAPACITY", Message: "Too many bookings", Details: "Max bookings reached. Wait and retry"}
        c.IndentedJSON(http.StatusInternalServerError, e)
        return
    }

	// write booking to dictionary
	newBooking := booking{
		BookingID: bookingId,
		SpaceID: tempBooking.SpaceID,
		Date: tempBooking.Date,
		UserID: tempBooking.UserID,
		Occupants: tempBooking.Occupants,
		StartTime: tempBooking.StartTime,
		EndTime: tempBooking.EndTime,
	}

	if er := validateBooking(newBooking); er != (err{}) {
		c.IndentedJSON(http.StatusBadRequest, er)
		return
	}

    writeBooking(newBooking.Date, bookingId, newBooking)
    c.IndentedJSON(http.StatusCreated, bookingId)
    return

}

func getBooking(c *gin.Context) {
	idStr := c.Param("bookingId")
	date := c.Param("date")

	bookingId, er := strconv.Atoi(idStr) // Convert string "123" to int 123
	if er != nil {
		e := err{ErrCode: "INPUT_ERROR", Message: "Unable to detect a booking id", Details: er.Error()}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
	}

	// // Use date and booking ID to parse input
	// type bookingTemp struct {
	// 	Date		string	`json:"date" binding:"required"`
	// 	BookingId	int		`json:"bookingId" binding:"required"`
	// }

	// var tempBooking bookingTemp

	// if er := c.BindJSON(&tempBooking); er != nil {
	// 	e := err{ErrCode: "INPUT_ERR", Message: "incorrect schema for a retrieval", Details: "A new user requires a date and bookingId"}
	// 	c.IndentedJSON(http.StatusBadRequest, e)
	// 	return
	// }

	value, found := readBooking(date, bookingId)
	//value, found := readBooking(tempBooking.Date, tempBooking.BookingId)
	if (!found) {
        e := err{ErrCode: "NOT_FOUND", Message: "Booking Not Found", Details: "The provided space id does not exist"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

	c.IndentedJSON(http.StatusOK, value)
    return
}

func deleteBooking(c *gin.Context) {
	idStr := c.Param("bookingId")
	date := c.Param("date")

	bookingId, er := strconv.Atoi(idStr) // Convert string "123" to int 123
	if er != nil {
		e := err{ErrCode: "INPUT_ERROR", Message: "Unable to detect a booking id", Details: er.Error()}
        c.IndentedJSON(http.StatusBadRequest, e)
        return
	}

	_, found := readBookingDate(date)
	if (!found) {
        e := err{ErrCode: "NOT_FOUND", Message: "Booking Date Not Found", Details: "The provided date does not exist"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

	_, bFound := readBooking(date, bookingId)
	if (!bFound) {
        e := err{ErrCode: "NOT_FOUND", Message: "Booking ID Not Found", Details: "The provided booking id does not exist"}
        c.IndentedJSON(http.StatusNotFound, e)
        return
    }

	delete(bookings[date], bookingId)

	c.IndentedJSON(http.StatusOK, "Deleted")
    return
}