#!/usr/bin/env python3
"""Test User Service error scenarios"""

import requests
import json

# Configuration
ALB_URL = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com"  # Update this

def test_user_errors():
    print("=== USER SERVICE ERROR TESTS ===\n")
    
    # Test 1: Create user with missing password
    print("1. Missing password:")
    resp = requests.post(f"{ALB_URL}/user", 
        json={"username": "testuser"})
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 2: Login with wrong password
    print("2. Wrong password:")
    resp = requests.post(f"{ALB_URL}/user/6036687152", 
        json={"username": "alice", "userPassword": "wrongpass"})
    print(f"   Status: {resp.status_code}, Expected: 404")
    if resp.status_code == 404:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 3: Validate non-existent user session
    print("3. Non-existent user:")
    resp = requests.get(f"{ALB_URL}/user/99999999")
    print(f"   Status: {resp.status_code}, Expected: 404")
    if resp.status_code == 404:
        print(f"   ✓ Error: {resp.json()}\n")
    
    # Test 4: Invalid user ID format
    print("4. Invalid user ID:")
    resp = requests.get(f"{ALB_URL}/user/notanumber")
    print(f"   Status: {resp.status_code}, Expected: 400")
    if resp.status_code == 400:
        print(f"   ✓ Error: {resp.json()}\n")

if __name__ == "__main__":
    test_user_errors()