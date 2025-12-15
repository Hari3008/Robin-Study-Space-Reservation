#!/usr/bin/env python3
"""Test Booking Service error scenarios"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
ALB_URL = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com"

# Credentials
ALICE = {
    "user_id": "6036687152",
    "username": "alice",
    "password": "password123"
}

ADMIN = {
    "user_id": "70215313471",
    "username": "admin",
    "password": "admin123"
}

def login_user(user_creds):
    """Login user to activate session"""
    resp = requests.post(
        f"{ALB_URL}/user/{user_creds['user_id']}", 
        json={
            "username": user_creds['username'], 
            "userPassword": user_creds['password']
        })
    return resp.status_code == 200

def test_booking_errors():
    print("=== BOOKING SERVICE ERROR TESTS ===\n")
    
    # Login alice first
    if login_user(ALICE):
        print("✓ Alice logged in successfully\n")
    else:
        print("✗ Failed to login Alice\n")
    
    auth = (ALICE['username'], ALICE['user_id'])
    
    # Test 1: Missing required fields
    print("1. Missing required fields:")
    resp = requests.post(f"{ALB_URL}/booking", 
        auth=auth,
        json={"spaceID": "Library-101"})
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 2: Invalid date format
    print("2. Invalid date format:")
    resp = requests.post(f"{ALB_URL}/booking", 
        auth=auth,
        json={
            "spaceID": "Library-101",
            "date": "12-15-2024",  # Wrong format
            "userID": int(ALICE['user_id']),
            "occupants": 2,
            "startTime": "2024-12-15T14:00:00Z",
            "endTime": "2024-12-15T16:00:00Z"
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 3: User ID mismatch
    print("3. User ID mismatch:")
    resp = requests.post(f"{ALB_URL}/booking", 
        auth=auth,
        json={
            "spaceID": "Library-101",
            "date": "2024-12-15",
            "userID": 999,  # Different from auth user
            "occupants": 2,
            "startTime": "2024-12-15T14:00:00Z",
            "endTime": "2024-12-15T16:00:00Z"
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 4: No authentication
    print("4. No authentication:")
    resp = requests.post(f"{ALB_URL}/booking",
        json={
            "spaceID": "Library-101",
            "date": "2024-12-15",
            "userID": int(ALICE['user_id']),
            "occupants": 2,
            "startTime": "2024-12-15T14:00:00Z",
            "endTime": "2024-12-15T16:00:00Z"
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 5: Invalid space ID
    print("5. Invalid space ID:")
    resp = requests.post(f"{ALB_URL}/booking", 
        auth=auth,
        json={
            "spaceID": "NonExistent-999",
            "date": "2024-12-15",
            "userID": int(ALICE['user_id']),
            "occupants": 2,
            "startTime": "2024-12-15T14:00:00Z",
            "endTime": "2024-12-15T16:00:00Z"
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 6: Exceeds capacity
    print("6. Exceeds space capacity:")
    resp = requests.post(f"{ALB_URL}/booking", 
        auth=auth,
        json={
            "spaceID": "Library-101",
            "date": "2024-12-15",
            "userID": int(ALICE['user_id']),
            "occupants": 200,  # Too many
            "startTime": "2024-12-15T14:00:00Z",
            "endTime": "2024-12-15T16:00:00Z"
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")

if __name__ == "__main__":
    test_booking_errors()