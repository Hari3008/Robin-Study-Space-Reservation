#!/usr/bin/env python3
"""Test Availability Service error scenarios"""

import requests
import json

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

def test_availability_errors():
    print("=== AVAILABILITY SERVICE ERROR TESTS ===\n")
    
    # Login both users
    if login_user(ALICE):
        print("✓ Alice logged in successfully")
    if login_user(ADMIN):
        print("✓ Admin logged in successfully\n")
    
    alice_auth = (ALICE['username'], ALICE['user_id'])
    admin_auth = (ADMIN['username'], ADMIN['user_id'])
    
    # Test 1: Create space without admin auth
    print("1. Create space without admin (alice):")
    resp = requests.post(f"{ALB_URL}/space", 
        auth=alice_auth,
        json={
            "roomCode": 999,
            "buildingCode": "Test",
            "capacity": 10
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 2: Create space with missing auth
    print("2. Missing authentication:")
    resp = requests.post(f"{ALB_URL}/space", 
        json={
            "roomCode": 999,
            "buildingCode": "Test",
            "capacity": 10
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 3: Create duplicate space (with admin)
    print("3. Duplicate space (admin auth):")
    resp = requests.post(f"{ALB_URL}/space", 
        auth=admin_auth,
        json={
            "roomCode": 101,
            "buildingCode": "Library",  # Already exists
            "capacity": 10
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 4: Get non-existent space
    print("4. Get non-existent space:")
    resp = requests.get(f"{ALB_URL}/space/NonExistent-999")
    print(f"   Status: {resp.status_code}, Expected: 404")
    if resp.status_code == 404:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 5: Invalid session for space creation
    print("5. Invalid user ID in auth:")
    invalid_auth = ("admin", "99999999999")  # Wrong user ID
    resp = requests.post(f"{ALB_URL}/space", 
        auth=invalid_auth,
        json={
            "roomCode": 999,
            "buildingCode": "Test",
            "capacity": 10
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 6: Missing required fields
    print("6. Missing required fields (with admin):")
    resp = requests.post(f"{ALB_URL}/space", 
        auth=admin_auth,
        json={
            "buildingCode": "Test"
            # Missing roomCode
        })
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")

if __name__ == "__main__":
    test_availability_errors()