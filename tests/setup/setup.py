#!/usr/bin/env python3
"""
baseline_populate.py - Populate Study Reservation System with test data
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass
from colorama import init, Fore, Style
import sys

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
ALB_URL = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com"  # Update this
ADMIN_PASSWORD = "admin123"
RATE_LIMIT_DELAY = 0.5  # Seconds between requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'baseline_population_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data class"""
    username: str
    user_id: int
    password: str
    email: str
    user_type: str

@dataclass
class Space:
    """Space data class"""
    space_id: str
    building: str
    room_code: int
    capacity: int

class StudyReservationPopulator:
    """Class to populate the Study Reservation System with baseline data"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.created_users: List[User] = []
        self.created_spaces: List[Space] = []
        self.failed_operations: List[str] = []
        self.admin_user: Optional[User] = None
        
    def create_user(self, username: str, password: str, email: str = "", user_type: str = "student") -> Optional[User]:
        """Create a new user"""
        url = f"{self.base_url}/user"
        payload = {
            "username": username,
            "userPassword": password,
            "userEmail": email or f"{username}@university.edu"
        }
        
        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 201:
                user_id = int(response.text.strip('"'))
                user = User(username, user_id, password, payload["userEmail"], user_type)
                self.created_users.append(user)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Created user: {username} (ID: {user_id})")
                logger.info(f"Created user: {username} with ID: {user_id}")
                return user
            else:
                print(f"{Fore.RED}✗{Style.RESET_ALL} Failed to create user: {username} (HTTP {response.status_code})")
                logger.error(f"Failed to create user {username}: {response.text}")
                self.failed_operations.append(f"User: {username}")
                return None
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error creating user {username}: {str(e)}")
            logger.error(f"Exception creating user {username}: {str(e)}")
            self.failed_operations.append(f"User: {username} (Exception)")
            return None
    
    def login_user(self, user: User) -> bool:
        """Login a user to activate their session"""
        url = f"{self.base_url}/user/{user.user_id}"
        payload = {
            "username": user.username,
            "userPassword": user.password
        }
        
        try:
            response = self.session.post(url, json=payload)
            if response.status_code == 200:
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Logged in user: {user.username}")
                logger.info(f"Successfully logged in user: {user.username}")
                return True
            else:
                print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} Failed to login user: {user.username}")
                logger.warning(f"Failed to login user {user.username}: {response.text}")
                return False
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error logging in user {user.username}: {str(e)}")
            logger.error(f"Exception logging in user {user.username}: {str(e)}")
            return False
    
    def create_space(self, room_code: int, building: str, capacity: int) -> Optional[Space]:
        """Create a new space (requires admin authentication)"""
        if not self.admin_user:
            print(f"{Fore.RED}✗{Style.RESET_ALL} No admin user available for space creation")
            return None
            
        url = f"{self.base_url}/space"
        payload = {
            "roomCode": room_code,
            "buildingCode": building,
            "capacity": capacity
        }
        
        # Use Basic Auth with admin credentials
        auth = (self.admin_user.username, str(self.admin_user.user_id))
        
        try:
            response = self.session.post(url, json=payload, auth=auth)
            if response.status_code == 201:
                space_id = response.text.strip('"')
                space = Space(space_id, building, room_code, capacity)
                self.created_spaces.append(space)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Created space: {space_id} (Capacity: {capacity})")
                logger.info(f"Created space: {space_id}")
                return space
            elif response.status_code == 400 and "already exists" in response.text:
                print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} Space already exists: {building}-{room_code}")
                logger.warning(f"Space already exists: {building}-{room_code}")
                return None
            else:
                print(f"{Fore.RED}✗{Style.RESET_ALL} Failed to create space: {building}-{room_code} (HTTP {response.status_code})")
                logger.error(f"Failed to create space {building}-{room_code}: {response.text}")
                self.failed_operations.append(f"Space: {building}-{room_code}")
                return None
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error creating space {building}-{room_code}: {str(e)}")
            logger.error(f"Exception creating space {building}-{room_code}: {str(e)}")
            self.failed_operations.append(f"Space: {building}-{room_code} (Exception)")
            return None
    
    def verify_space(self, space_id: str) -> bool:
        """Verify a space can be retrieved"""
        url = f"{self.base_url}/space/{space_id}"
        
        try:
            response = self.session.get(url)
            return response.status_code == 200
        except:
            return False
    
    def verify_user_session(self, user: User) -> bool:
        """Verify a user's session is valid"""
        url = f"{self.base_url}/user/{user.user_id}"
        
        try:
            response = self.session.get(url)
            return response.status_code == 200
        except:
            return False
    
    def populate_users(self):
        """Create all test users"""
        print(f"\n{Fore.CYAN}Step 1: Creating Admin User{Style.RESET_ALL}")
        print("-" * 50)
        
        # Create admin
        self.admin_user = self.create_user("admin", ADMIN_PASSWORD, "admin@studyreservation.com", "admin")
        if self.admin_user:
            time.sleep(RATE_LIMIT_DELAY)
            self.login_user(self.admin_user)
        else:
            print(f"{Fore.RED}Failed to create admin user. Some operations may fail.{Style.RESET_ALL}")
            logger.error("Failed to create admin user")
        
        print(f"\n{Fore.CYAN}Step 2: Creating Regular Users{Style.RESET_ALL}")
        print("-" * 50)
        
        # User configurations
        user_configs = [
            # Students
            ("alice", "password123", "alice@university.edu", "student"),
            ("bob", "password123", "bob@university.edu", "student"),
            ("charlie", "password123", "charlie@university.edu", "student"),
            ("diana", "password123", "diana@university.edu", "student"),
            ("ethan", "password123", "ethan@university.edu", "student"),
            ("fiona", "password123", "fiona@university.edu", "student"),
            ("george", "password123", "george@university.edu", "student"),
            ("hannah", "password123", "hannah@university.edu", "student"),
            ("ivan", "password123", "ivan@university.edu", "student"),
            ("julia", "password123", "julia@university.edu", "student"),
            
            # Faculty
            ("prof_smith", "faculty456", "prof.smith@university.edu", "faculty"),
            ("prof_jones", "faculty456", "prof.jones@university.edu", "faculty"),
            ("prof_chen", "faculty456", "prof.chen@university.edu", "faculty"),
            ("prof_garcia", "faculty456", "prof.garcia@university.edu", "faculty"),
            ("prof_kim", "faculty456", "prof.kim@university.edu", "faculty"),
            
            # Staff
            ("staff_mary", "staff789", "mary@university.edu", "staff"),
            ("staff_john", "staff789", "john@university.edu", "staff"),
            ("staff_sarah", "staff789", "sarah@university.edu", "staff"),
            ("staff_mike", "staff789", "mike@university.edu", "staff"),
            ("staff_lisa", "staff789", "lisa@university.edu", "staff"),
        ]
        
        print(f"\n{Fore.YELLOW}Creating Student Users...{Style.RESET_ALL}")
        students = [config for config in user_configs if config[3] == "student"]
        for username, password, email, user_type in students:
            user = self.create_user(username, password, email, user_type)
            if user:
                time.sleep(RATE_LIMIT_DELAY)
                self.login_user(user)
        
        print(f"\n{Fore.YELLOW}Creating Faculty Users...{Style.RESET_ALL}")
        faculty = [config for config in user_configs if config[3] == "faculty"]
        for username, password, email, user_type in faculty:
            user = self.create_user(username, password, email, user_type)
            if user:
                time.sleep(RATE_LIMIT_DELAY)
                self.login_user(user)
        
        print(f"\n{Fore.YELLOW}Creating Staff Users...{Style.RESET_ALL}")
        staff = [config for config in user_configs if config[3] == "staff"]
        for username, password, email, user_type in staff:
            user = self.create_user(username, password, email, user_type)
            if user:
                time.sleep(RATE_LIMIT_DELAY)
                self.login_user(user)
    
    def populate_spaces(self):
        """Create all test spaces"""
        print(f"\n{Fore.CYAN}Step 3: Creating Spaces{Style.RESET_ALL}")
        print("-" * 50)
        
        if not self.admin_user:
            print(f"{Fore.RED}Cannot create spaces without admin user{Style.RESET_ALL}")
            return
        
        # Space configurations
        buildings = ["Library", "Engineering", "Science", "Business", "Arts"]
        room_configs = [
            (101, 4, "Study Room"),
            (102, 6, "Group Room"),
            (103, 8, "Conference Room"),
            (201, 2, "Phone Booth"),
            (202, 10, "Classroom"),
            (301, 1, "Individual Desk"),
        ]
        
        for building in buildings:
            print(f"\n{Fore.YELLOW}Creating spaces in {building}...{Style.RESET_ALL}")
            for room_code, capacity, room_type in room_configs:
                self.create_space(room_code, building, capacity)
                time.sleep(RATE_LIMIT_DELAY)
        
        # Special spaces
        print(f"\n{Fore.YELLOW}Creating special spaces...{Style.RESET_ALL}")
        special_spaces = [
            (500, "Library", 20, "Large Study Hall"),
            (600, "Library", 30, "Event Space"),
            (999, "Virtual", 100, "Virtual Meeting Room"),
            (401, "Engineering", 15, "Computer Lab"),
            (501, "Science", 12, "Research Room"),
        ]
        
        for room_code, building, capacity, description in special_spaces:
            print(f"  Creating {description}...")
            self.create_space(room_code, building, capacity)
            time.sleep(RATE_LIMIT_DELAY)
    
    def verify_system(self):
        """Verify the system is working"""
        print(f"\n{Fore.CYAN}Step 4: System Verification{Style.RESET_ALL}")
        print("-" * 50)
        
        # Test space retrieval
        if self.created_spaces:
            test_space = self.created_spaces[0]
            if self.verify_space(test_space.space_id):
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Space retrieval working")
            else:
                print(f"{Fore.RED}✗{Style.RESET_ALL} Space retrieval failed")
        
        # Test user session
        if self.admin_user:
            if self.verify_user_session(self.admin_user):
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} User session validation working")
            else:
                print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} User session might have expired")
    
    def save_results(self):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = f"baseline_results_{timestamp}.json"
        results = {
            "timestamp": timestamp,
            "alb_url": self.base_url,
            "users": [
                {
                    "username": u.username,
                    "user_id": u.user_id,
                    "email": u.email,
                    "type": u.user_type
                } for u in self.created_users
            ],
            "spaces": [
                {
                    "space_id": s.space_id,
                    "building": s.building,
                    "room_code": s.room_code,
                    "capacity": s.capacity
                } for s in self.created_spaces
            ],
            "failed_operations": self.failed_operations
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{Fore.GREEN}Results saved to: {results_file}{Style.RESET_ALL}")
        
        # Save test credentials for easy use
        creds_file = "test_credentials.json"
        credentials = {
            "admin": {
                "username": self.admin_user.username if self.admin_user else None,
                "user_id": self.admin_user.user_id if self.admin_user else None,
                "password": self.admin_user.password if self.admin_user else None
            },
            "test_users": [
                {
                    "username": u.username,
                    "user_id": u.user_id,
                    "password": u.password,
                    "type": u.user_type
                } for u in self.created_users[:5]  # Save first 5 users for testing
            ],
            "test_spaces": [
                s.space_id for s in self.created_spaces[:5]  # Save first 5 spaces
            ]
        }
        
        with open(creds_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print(f"{Fore.GREEN}Test credentials saved to: {creds_file}{Style.RESET_ALL}")
    
    def print_summary(self):
        """Print population summary"""
        print(f"\n{'='*60}")
        print(f"{Fore.CYAN}Population Summary{Style.RESET_ALL}")
        print(f"{'='*60}")
        
        # Count by type
        students = len([u for u in self.created_users if u.user_type == "student"])
        faculty = len([u for u in self.created_users if u.user_type == "faculty"])
        staff = len([u for u in self.created_users if u.user_type == "staff"])
        
        print(f"{Fore.GREEN}Created Users:{Style.RESET_ALL} {len(self.created_users)}")
        print(f"  - Students: {students}")
        print(f"  - Faculty: {faculty}")
        print(f"  - Staff: {staff}")
        print(f"  - Admin: {1 if self.admin_user else 0}")
        
        print(f"\n{Fore.GREEN}Created Spaces:{Style.RESET_ALL} {len(self.created_spaces)}")
        
        # Count by building
        building_counts = {}
        for space in self.created_spaces:
            building_counts[space.building] = building_counts.get(space.building, 0) + 1
        
        for building, count in building_counts.items():
            print(f"  - {building}: {count}")
        
        if self.failed_operations:
            print(f"\n{Fore.RED}Failed Operations:{Style.RESET_ALL} {len(self.failed_operations)}")
            for op in self.failed_operations[:5]:  # Show first 5
                print(f"  - {op}")
            if len(self.failed_operations) > 5:
                print(f"  ... and {len(self.failed_operations) - 5} more")
    
    def run(self):
        """Run the complete population process"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Study Reservation System - Baseline Data Population{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ALB URL: {self.base_url}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        try:
            self.populate_users()
            self.populate_spaces()
            self.verify_system()
            self.save_results()
            self.print_summary()
            
            print(f"\n{Fore.GREEN}Population completed successfully!{Style.RESET_ALL}")
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Population interrupted by user{Style.RESET_ALL}")
            self.save_results()
            self.print_summary()
        except Exception as e:
            print(f"\n{Fore.RED}Population failed with error: {str(e)}{Style.RESET_ALL}")
            logger.error(f"Population failed: {str(e)}", exc_info=True)
            self.save_results()
            self.print_summary()

class TestRunner:
    """Run tests with populated data"""
    
    def __init__(self, base_url: str, credentials_file: str = "test_credentials.json"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Load credentials
        with open(credentials_file, 'r') as f:
            self.credentials = json.load(f)
    
    def test_booking_flow(self):
        """Test complete booking flow"""
        print(f"\n{Fore.CYAN}Testing Booking Flow{Style.RESET_ALL}")
        print("-" * 50)
        
        # Use first test user
        if not self.credentials['test_users']:
            print(f"{Fore.RED}No test users available{Style.RESET_ALL}")
            return
        
        test_user = self.credentials['test_users'][0]
        test_space = self.credentials['test_spaces'][0] if self.credentials['test_spaces'] else "Library-101"
        
        # Create booking
        booking_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        start_time = f"{booking_date}T14:00:00Z"
        end_time = f"{booking_date}T16:00:00Z"
        
        url = f"{self.base_url}/booking"
        payload = {
            "spaceID": test_space,
            "date": booking_date,
            "startTime": start_time,
            "endTime": end_time,
            "occupants": 3,
            "userID": test_user['user_id']
        }
        
        auth = (test_user['username'], str(test_user['user_id']))
        
        try:
            response = self.session.post(url, json=payload, auth=auth)
            if response.status_code in [200, 201]:
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Successfully created booking")
                booking_id = response.json() if response.text else None
                
                # Verify booking
                if booking_id:
                    verify_url = f"{self.base_url}/booking/user/{test_user['user_id']}"
                    verify_response = self.session.get(verify_url, auth=auth)
                    if verify_response.status_code == 200:
                        print(f"{Fore.GREEN}✓{Style.RESET_ALL} Successfully retrieved user bookings")
                    else:
                        print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} Could not retrieve bookings")
            else:
                print(f"{Fore.RED}✗{Style.RESET_ALL} Failed to create booking: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error testing booking: {str(e)}")
    
    def test_concurrent_bookings(self):
        """Test concurrent booking attempts"""
        print(f"\n{Fore.CYAN}Testing Concurrent Bookings{Style.RESET_ALL}")
        print("-" * 50)
        
        if len(self.credentials['test_users']) < 2:
            print(f"{Fore.YELLOW}Need at least 2 users for concurrent test{Style.RESET_ALL}")
            return
        
        import threading
        
        results = []
        
        def attempt_booking(user, space_id, results):
            booking_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            start_time = f"{booking_date}T10:00:00Z"
            end_time = f"{booking_date}T12:00:00Z"
            
            url = f"{self.base_url}/booking"
            payload = {
                "spaceID": space_id,
                "date": booking_date,
                "startTime": start_time,
                "endTime": end_time,
                "occupants": 2,
                "userID": user['user_id']
            }
            
            auth = (user['username'], str(user['user_id']))
            
            try:
                response = requests.post(url, json=payload, auth=auth)
                results.append({
                    "user": user['username'],
                    "status": response.status_code,
                    "success": response.status_code in [200, 201]
                })
            except Exception as e:
                results.append({
                    "user": user['username'],
                    "status": 0,
                    "success": False,
                    "error": str(e)
                })
        
        # Create threads for concurrent requests
        threads = []
        test_space = self.credentials['test_spaces'][0] if self.credentials['test_spaces'] else "Library-101"
        
        for user in self.credentials['test_users'][:2]:
            thread = threading.Thread(target=attempt_booking, args=(user, test_space, results))
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        successful = sum(1 for r in results if r['success'])
        
        if successful == 1:
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} Correctly prevented double booking (1 success, 1 failure)")
        elif successful == 0:
            print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} Both bookings failed")
        else:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Both bookings succeeded - double booking occurred!")
        
        for result in results:
            status_icon = "✓" if result['success'] else "✗"
            status_color = Fore.GREEN if result['success'] else Fore.RED
            print(f"  {status_color}{status_icon}{Style.RESET_ALL} {result['user']}: Status {result['status']}")
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Running Tests with Populated Data{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        self.test_booking_flow()
        self.test_concurrent_bookings()
        
        print(f"\n{Fore.GREEN}Testing completed!{Style.RESET_ALL}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Study Reservation System - Baseline Population')
    parser.add_argument('--url', default=ALB_URL, help='ALB URL for the system')
    parser.add_argument('--test', action='store_true', help='Run tests after population')
    parser.add_argument('--test-only', action='store_true', help='Only run tests (skip population)')
    
    args = parser.parse_args()
    
    if not args.test_only:
        # Run population
        populator = StudyReservationPopulator(args.url)
        populator.run()
    
    if args.test or args.test_only:
        # Run tests
        try:
            tester = TestRunner(args.url)
            tester.run_all_tests()
        except FileNotFoundError:
            print(f"{Fore.RED}No test credentials found. Run population first.{Style.RESET_ALL}")
            sys.exit(1)

if __name__ == "__main__":
    main()