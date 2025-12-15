#!/usr/bin/env python3
"""
cache_consistency_test.py
Tests cache correctness for Booking Service across:
 - Read-after-write
 - Write-after-write
 - Invalidation
 - Stale read detection
"""

import requests
import time
from datetime import datetime, timedelta

BASE_URL = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com"

ALICE = {"user_id": 6036687152, "username": "alice", "password": "password123"}
BOB   = {"user_id": 50723387644, "username": "bob",   "password": "password123"}

def login(user):
    r = requests.post(
        f"{BASE_URL}/user/{user['user_id']}",
        json={"username": user["username"], "userPassword": user["password"]}
    )
    if r.status_code != 200:
        raise Exception(f"Login failed for {user['username']}: {r.text}")
    return (user["username"], str(user["user_id"]))


def make_booking(auth, space, start_hour):
    date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {
        "spaceID": space,
        "date": date,
        "userID": int(auth[1]),
        "occupants": 2,
        "startTime": f"{date}T{start_hour:02d}:00:00Z",
        "endTime": f"{date}T{start_hour+1:02d}:00:00Z",
    }
    r = requests.post(f"{BASE_URL}/booking", json=payload, auth=auth)
    return r, date


def get_booking(auth, date, booking_id):
    return requests.get(f"{BASE_URL}/booking/{date}/{booking_id}", auth=auth)


# -----------------------------
#        TEST 1  
# READ-AFTER-WRITE CONSISTENCY
# -----------------------------
def test_read_after_write():
    print("\nTEST 1: Read-after-write")

    alice_auth = login(ALICE)
    resp, date = make_booking(alice_auth, "Library-101", 10)

    if resp.status_code != 201:
        print("Booking failed:", resp.text)
        return

    booking_id = resp.json()
    print("Created booking:", booking_id)

    # Immediate fetch
    r2 = get_booking(alice_auth, date, booking_id)
    print("Immediate read:", r2.status_code, r2.text)


# -----------------------------
#        TEST 2  
# WRITE-AFTER-WRITE CONSISTENCY
# -----------------------------
def test_write_after_write():
    print("\nTEST 2: Write-after-write")

    alice_auth = login(ALICE)
    resp, date = make_booking(alice_auth, "Library-102", 11)

    if resp.status_code != 201:
        print("Initial booking failed:", resp.text)
        return

    booking_id = resp.json()

    print("Initial booking:", booking_id)

    # Try creating an overlapping booking (should fail)
    print("Creating conflicting booking...")
    resp2, _ = make_booking(alice_auth, "Library-102", 11)
    print("Response:", resp2.status_code, resp2.text)


# -----------------------------
#        TEST 3  
# CACHE INVALIDATION (ANOTHER USER)
# -----------------------------
def test_cross_user_invalidation():
    print("\nTEST 3: Cross-user cache invalidation")

    alice_auth = login(ALICE)
    bob_auth = login(BOB)

    resp, date = make_booking(alice_auth, "Library-103", 13)

    if resp.status_code != 201:
        print("Alice booking failed:", resp.text)
        return

    booking_id = resp.json()
    print("Alice created:", booking_id)

    # Bob reads (should get fresh data)
    r = get_booking(bob_auth, date, booking_id)
    print("Bob read:", r.status_code, r.text)


# -----------------------------
#        TEST 4  
# STALE READ DETECTION
# -----------------------------
def test_stale_read():
    print("\nTEST 4: Stale read detection")

    alice_auth = login(ALICE)

    # Alice creates a booking
    resp, date = make_booking(alice_auth, "Library-101", 15)
    if resp.status_code != 201:
        print("Booking failed:", resp.text)
        return

    booking_id = resp.json()

    # First read (warm cache)
    r1 = get_booking(alice_auth, date, booking_id)
    print("Warm cache read:", r1.status_code)

    # Simulate cache expiration
    print("Waiting for cache TTL to expire (5 seconds)...")
    time.sleep(5)

    # Second read — should fetch fresh
    r2 = get_booking(alice_auth, date, booking_id)
    print("Post-TTL read:", r2.status_code)


# -----------------------------
# Run everything
# -----------------------------
if __name__ == "__main__":
    test_read_after_write()
    test_write_after_write()
    test_cross_user_invalidation()
    test_stale_read()
