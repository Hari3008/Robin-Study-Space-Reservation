package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// Configuration - Base URLs only, endpoints added in functions
var (
	BASE_URL = getEnvOrDefault("BASE_URL", "http://cs6650l2-alb-2044995355.us-west-2.elb.amazonaws.com")
)

type Metrics struct {
	TotalRequests      int64
	SuccessfulBookings int64
	Conflicts          int64
	RetryCount         int64
	Latencies          []time.Duration
	mu                 sync.Mutex
}

func main() {
	fmt.Println("=== DYNAMODB BURST RESERVATION TEST ===")
	fmt.Printf("Testing against: %s\n\n", BASE_URL)


	// Setup phase
	fmt.Println("\nCreating test data...")
	adminID := createAdmin()
	if adminID == 0 {
		fmt.Println("Failed to create admin. Exiting.")
		return
	}

	spaces := createSpaces(adminID, 3)
	if len(spaces) == 0 {
		fmt.Println("Failed to create spaces. Exiting.")
		return
	}

	users := createUsers(100) // Start with just 10 for testing
	if len(users) == 0 {
		fmt.Println("Failed to create users. Exiting.")
		return
	}

	// Run burst test
	fmt.Println("\n--- Starting Burst Test ---")
	testDate := time.Now().Add(24 * time.Hour).Format("2006-01-02")
	runBurstTest(len(users), users, spaces, testDate)
}

func createAdmin() int {
	fmt.Print("Creating admin user... ")

	body, _ := json.Marshal(map[string]string{
		"username":     "admin",
		"userPassword": "adminpass123",
	})

	url := BASE_URL + "/user"
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Printf("\nError: %v\n", err)
		return 0
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != 201 {
		fmt.Printf("\nFailed. Status: %d, Response: %s\n", resp.StatusCode, string(respBody))
		return 0
	}

	var adminID int
	json.Unmarshal(respBody, &adminID)
	fmt.Printf("ID: %d\n", adminID)

	// Login admin to test
	if loginAdmin(adminID) {
		fmt.Println("Admin login successful")
	} else {
		fmt.Println("Warning: Admin login failed")
	}

	return adminID
}

func loginAdmin(adminID int) bool {
	body, _ := json.Marshal(map[string]string{
		"username":     "admin",
		"userPassword": "adminpass123",
	})

	url := fmt.Sprintf("%s/user/%d", BASE_URL, adminID)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == 200
}

func createSpaces(adminID int, count int) []string {
	fmt.Printf("Creating %d spaces... ", count)
	spaces := make([]string, 0)

	// Login admin first
	loginAdmin(adminID)

	for i := 0; i < count; i++ {
		// Create space data
		spaceData := map[string]interface{}{
			"roomCode":     100 + i,
			"buildingCode": "TEST",
			"capacity":     20,
			"openTime":     "2000-01-01T08:00:00Z",
			"closeTime":    "2000-01-01T22:00:00Z",
		}

		body, _ := json.Marshal(spaceData)

		// Create request with auth
		url := BASE_URL + "/space"
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		req.SetBasicAuth("admin", fmt.Sprintf("%d", adminID))

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(req)
		if err != nil {
			fmt.Printf("\n  Error creating space %d: %v\n", i, err)
			continue
		}

		respBody, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode != 201 {
			fmt.Printf("\nFailed space %d. Status: %d, Response: %s\n",
				i, resp.StatusCode, string(respBody))
			continue
		}

		var spaceID string
		json.Unmarshal(respBody, &spaceID)
		spaces = append(spaces, spaceID)
	}

	fmt.Printf("Created: %v\n", spaces)
	return spaces
}

func createUsers(count int) []int {
	fmt.Printf("Creating %d users... ", count)
	users := make([]int, 0)

	for i := 0; i < count; i++ {
		userData := map[string]string{
			"username":     fmt.Sprintf("testuser%d", i),
			"userPassword": "testpass123",
		}

		body, _ := json.Marshal(userData)

		url := BASE_URL + "/user"
		resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
		if err != nil {
			continue
		}

		respBody, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode == 201 {
			var userID int
			json.Unmarshal(respBody, &userID)
			users = append(users, userID)

			// Test login
			loginUser(userID, i)
		}
	}

	fmt.Printf("Created %d users\n", len(users))
	return users
}

func loginUser(userID int, idx int) bool {
	body, _ := json.Marshal(map[string]string{
		"username":     fmt.Sprintf("testuser%d", idx),
		"userPassword": "testpass123",
	})

	url := fmt.Sprintf("%s/user/%d", BASE_URL, userID)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == 200
}

func runBurstTest(numUsers int, users []int, spaces []string, date string) {
	metrics := &Metrics{
		Latencies: make([]time.Duration, 0),
	}

	// Generate test slots
	slots := generateSlots(spaces, date)
	fmt.Printf("Generated %d booking slots for date %s\n", len(slots), date)

	var wg sync.WaitGroup
	startTime := time.Now()

	// Launch concurrent users
	for idx, userID := range users {
		wg.Add(1)
		go func(uid int, index int) {
			defer wg.Done()

			// Try 2 bookings per user
			for attempt := 0; attempt < 2; attempt++ {
				slot := slots[rand.Intn(len(slots))]
				attemptBooking(uid, index, slot, metrics)
				time.Sleep(time.Duration(100+rand.Intn(200)) * time.Millisecond)
			}
		}(userID, idx)
	}

	wg.Wait()
	duration := time.Since(startTime)

	// Print results
	printResults(metrics, duration, numUsers)
}

func attemptBooking(userID int, userIdx int, slot map[string]interface{}, metrics *Metrics) {
	start := time.Now()

	// Login first
	if !loginUser(userID, userIdx) {
		fmt.Printf("Login failed for user %d\n", userID)
		return
	}

	// Prepare booking with user's ID
	slot["userID"] = userID
	body, _ := json.Marshal(slot)

	// Create booking request
	url := BASE_URL + "/booking"
	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	// Use correct username format for auth
	username := fmt.Sprintf("testuser%d", userIdx)
	req.SetBasicAuth(username, fmt.Sprintf("%d", userID))

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)

	latency := time.Since(start)
	metrics.mu.Lock()
	metrics.Latencies = append(metrics.Latencies, latency)
	metrics.mu.Unlock()

	atomic.AddInt64(&metrics.TotalRequests, 1)

	if err != nil {
		fmt.Printf(" Request error for user %d: %v\n", userID, err)
		return
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode == 201 {
		atomic.AddInt64(&metrics.SuccessfulBookings, 1)
		fmt.Printf("Booking success for user %d\n", userID)
	} else {
		var errResp map[string]string
		json.Unmarshal(respBody, &errResp)

		if errResp["ErrCode"] == "CONFLICT" {
			atomic.AddInt64(&metrics.Conflicts, 1)
			fmt.Printf("Conflict for user %d\n", userID)
		} else {
			fmt.Printf("Booking failed for user %d: [%s] %s\n",
				userID, errResp["ErrCode"], errResp["Message"])
		}
	}
}

func generateSlots(spaces []string, date string) []map[string]interface{} {
	slots := make([]map[string]interface{}, 0)

	// Create various time slots (some overlapping)
	times := []struct{ start, end string }{
		{"2000-01-01T09:00:00Z", "2000-01-01T11:00:00Z"},
		{"2000-01-01T10:00:00Z", "2000-01-01T12:00:00Z"}, // Overlaps
		{"2000-01-01T14:00:00Z", "2000-01-01T16:00:00Z"},
		{"2000-01-01T15:00:00Z", "2000-01-01T17:00:00Z"}, // Overlaps
	}

	for _, space := range spaces {
		for _, t := range times {
			startTime, _ := time.Parse(time.RFC3339, t.start)
			endTime, _ := time.Parse(time.RFC3339, t.end)

			slot := map[string]interface{}{
				"spaceID":   space,
				"date":      date,
				"occupants": 5,
				"startTime": startTime.Format(time.RFC3339),
				"endTime":   endTime.Format(time.RFC3339),
			}
			slots = append(slots, slot)
		}
	}

	return slots
}

func printResults(metrics *Metrics, duration time.Duration, numUsers int) {
	fmt.Println("\n=== RESULTS ===")
	total := atomic.LoadInt64(&metrics.TotalRequests)
	successful := atomic.LoadInt64(&metrics.SuccessfulBookings)
	conflicts := atomic.LoadInt64(&metrics.Conflicts)

	fmt.Printf("Total Requests:     %d\n", total)
	fmt.Printf("Successful:         %d\n", successful)
	fmt.Printf("Conflicts:          %d\n", conflicts)

	if total > 0 {
		fmt.Printf("Success Rate:       %.1f%%\n", float64(successful)/float64(total)*100)
		fmt.Printf("Conflict Rate:      %.1f%%\n", float64(conflicts)/float64(total)*100)
	}

	// Calculate latency percentiles
	if len(metrics.Latencies) > 0 {
		sort.Slice(metrics.Latencies, func(i, j int) bool {
			return metrics.Latencies[i] < metrics.Latencies[j]
		})

		p50 := metrics.Latencies[len(metrics.Latencies)*50/100]
		p95 := metrics.Latencies[len(metrics.Latencies)*95/100]

		fmt.Printf("P50 Latency:        %v\n", p50)
		fmt.Printf("P95 Latency:        %v\n", p95)
	}

	fmt.Printf("Test Duration:      %v\n", duration)
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
