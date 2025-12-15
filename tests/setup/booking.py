#!/usr/bin/env python3
"""
populate_bookings.py - Simple script to create a few test bookings
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
ALB_URL = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com"  # Update this

# Known working user
ALICE = {
    "user_id": "6036687152",
    "username": "alice", 
    "password": "password123"
}

# Test spaces
SPACES = ["Library-101", "Library-102", "Engineering-101"]

def populate_bookings():
    print("="*60)
    print("POPULATING BOOKING TABLE")
    print("="*60)
    
    # Step 1: Login alice to activate session
    print("\n1. Logging in alice...")
    login_resp = requests.post(
        f"{ALB_URL}/user/{ALICE['user_id']}",
        json={
            "username": ALICE['username'],
            "userPassword": ALICE['password']
        }
    )
    
    if login_resp.status_code == 200:
        print("   ✓ Login successful")
    else:
        print(f"   ✗ Login failed: {login_resp.status_code}")
        return
    
    # Step 2: Create several bookings
    print("\n2. Creating bookings...")
    
    created_bookings = []
    auth = (ALICE['username'], ALICE['user_id'])
    
    # Create 5 bookings over next week
    for i in range(5):
        days_ahead = i + 1
        booking_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        hour = 10 + i  # Different times: 10, 11, 12, 13, 14
        space = SPACES[i % len(SPACES)]
        
        payload = {
            "spaceID": space,
            "date": booking_date,
            "userID": int(ALICE['user_id']),
            "occupants": 2,
            "startTime": f"{booking_date}T{hour:02d}:00:00Z",
            "endTime": f"{booking_date}T{hour+1:02d}:00:00Z"
        }
        
        print(f"\n   Booking {i+1}:")
        print(f"   - Space: {space}")
        print(f"   - Date: {booking_date}")
        print(f"   - Time: {hour}:00-{hour+1}:00")
        
        resp = requests.post(
            f"{ALB_URL}/booking",
            auth=auth,
            json=payload
        )
        
        if resp.status_code == 201:
            booking_id = resp.text.strip('"')
            print(f"   ✓ Created - ID: {booking_id}")
            created_bookings.append({
                "booking_id": booking_id,
                "date": booking_date,
                "space": space
            })
        else:
            print(f"   ✗ Failed: {resp.status_code}")
            if resp.text:
                error = json.loads(resp.text)
                print(f"     Error: {error.get('Message', '')}")
    
    # Step 3: Verify bookings
    print("\n3. Verifying created bookings...")
    
    for booking in created_bookings:
        resp = requests.get(
            f"{ALB_URL}/booking/{booking['date']}/{booking['booking_id']}"
        )
        
        if resp.status_code == 200:
            print(f"   ✓ Verified booking {booking['booking_id']}")
        else:
            print(f"   ✗ Could not verify booking {booking['booking_id']}")
    
    # Step 4: Save results
    print("\n4. Summary")
    print(f"   Created {len(created_bookings)} bookings")
    
    # Save to file for reference
    with open('created_bookings.json', 'w') as f:
        json.dump(created_bookings, f, indent=2)
    print("   Saved booking IDs to created_bookings.json")
    
    print("\n" + "="*60)
    print("POPULATION COMPLETE")
    print("="*60)
    
    return created_bookings

if __name__ == "__main__":
    populate_bookings()