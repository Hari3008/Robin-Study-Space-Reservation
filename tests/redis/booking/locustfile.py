#!/usr/bin/env python3
"""
locust_cache_test.py - Performance test for booking service with cache
"""

from locust import HttpUser, task, between
from datetime import datetime, timedelta
import random
import json

# Test user
ALICE = {
    "user_id": 6036687152,
    "username": "alice",
    "password": "password123"
}

# Popular spaces to test cache
SPACES = ["Library-101", "Library-102", "Library-103"]

class BookingCacheUser(HttpUser):
    wait_time = between(0.5, 2)
    host = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com"
    
    def on_start(self):
        """Login once per simulated user"""
        resp = self.client.post(
            f"/user/{ALICE['user_id']}",
            json={"username": ALICE['username'], "userPassword": ALICE['password']},
            name="/user/login"
        )
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
        self.auth = (ALICE['username'], str(ALICE['user_id']))
        self.created_bookings = []

    @task(5)
    def create_popular_booking(self):
        """Create a booking for a popular space (should hit cache)"""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        start_hour = random.randint(9, 16)
        payload = {
            "spaceID": "Library-101",
            "date": date,
            "userID": ALICE['user_id'],
            "occupants": random.randint(1, 4),
            "startTime": f"{date}T{start_hour:02d}:00:00Z",
            "endTime": f"{date}T{start_hour+1:02d}:00:00Z"
        }
        resp = self.client.post("/booking", auth=self.auth, json=payload, name="/booking (cache)")
        if resp.status_code == 201:
            try:
                booking_id = json.loads(resp.text)
                self.created_bookings.append((date, booking_id))
            except:
                pass

    @task(3)
    def create_random_booking(self):
        """Create random booking to simulate normal load"""
        date = (datetime.now() + timedelta(days=random.randint(2, 7))).strftime("%Y-%m-%d")
        start_hour = random.randint(9, 16)
        payload = {
            "spaceID": random.choice(SPACES),
            "date": date,
            "userID": ALICE['user_id'],
            "occupants": random.randint(1, 4),
            "startTime": f"{date}T{start_hour:02d}:00:00Z",
            "endTime": f"{date}T{start_hour+1:02d}:00:00Z"
        }
        self.client.post("/booking", auth=self.auth, json=payload, name="/booking (random)")

    @task(2)
    def get_existing_booking(self):
        """Get booking details to simulate cache hits on validation"""
        if self.created_bookings:
            date, booking_id = random.choice(self.created_bookings)
            self.client.get(f"/booking/{date}/{booking_id}", name="/booking/:date/:id")

    @task(1)
    def health_check(self):
        """Check service health"""
        self.client.get("/booking/health", name="/health")
