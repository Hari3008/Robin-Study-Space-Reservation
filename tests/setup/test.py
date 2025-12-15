#!/usr/bin/env python3
"""
quick_test.py - Quick tests using populated data
"""

import requests
import json
from datetime import datetime, timedelta
from colorama import init, Fore, Style

init(autoreset=True)

# Load credentials
with open('test_credentials.json', 'r') as f:
    creds = json.load(f)

ALB_URL = "http://CS6650L2-alb-1577896554.us-east-1.elb.amazonaws.com"

def test_space_availability():
    """Test space availability"""
    print(f"{Fore.CYAN}Testing Space Availability{Style.RESET_ALL}")
    
    for space_id in creds['test_spaces']:
        response = requests.get(f"{ALB_URL}/space/{space_id}")
        if response.status_code == 200:
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} Space {space_id} is available")
        else:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Space {space_id} not found")

def test_user_sessions():
    """Test user sessions"""
    print(f"\n{Fore.CYAN}Testing User Sessions{Style.RESET_ALL}")
    
    for user in creds['test_users'][:3]:
        # Login first
        login_response = requests.post(
            f"{ALB_URL}/user/{user['user_id']}",
            json={
                "username": user['username'],
                "userPassword": user['password']
            }
        )
        
        if login_response.status_code == 200:
            # Check session
            session_response = requests.get(f"{ALB_URL}/user/{user['user_id']}")
            if session_response.status_code == 200:
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} User {user['username']} session valid")
            else:
                print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} User {user['username']} session invalid")
        else:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Failed to login {user['username']}")

if __name__ == "__main__":
    print(f"\n{Fore.CYAN}Quick System Test{Style.RESET_ALL}")
    print("=" * 40)
    test_space_availability()
    test_user_sessions()
    print(f"\n{Fore.GREEN}Quick test completed!{Style.RESET_ALL}")