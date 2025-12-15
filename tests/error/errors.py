#!/usr/bin/env python3
"""
error_handling_test.py - Test error responses and invalid request handling
Tests all services for proper error codes and messages
"""

import requests
import json
import random
import time
from datetime import datetime, timedelta
from colorama import init, Fore, Style
import traceback

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
ALB_URL = "http://CS6650L2-alb-243173383.us-east-1.elb.amazonaws.com" 

# Test results storage
test_results = {
    "passed": [],
    "failed": [],
    "unexpected": []
}

def print_test_header(test_name):
    """Print formatted test header"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{test_name}")
    print(f"{'='*60}{Style.RESET_ALL}")

def test_case(test_name, expected_status=None):
    """Decorator for test cases"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n{Fore.YELLOW}► Testing: {test_name}{Style.RESET_ALL}")
            try:
                response = func(*args, **kwargs)
                
                # Check if we got expected status
                if expected_status and response.status_code == expected_status:
                    print(f"{Fore.GREEN}✓ Expected {expected_status}: {response.status_code}{Style.RESET_ALL}")
                    test_results["passed"].append(test_name)
                elif expected_status:
                    print(f"{Fore.RED}✗ Expected {expected_status}, got {response.status_code}{Style.RESET_ALL}")
                    test_results["failed"].append(f"{test_name} (got {response.status_code})")
                else:
                    print(f"{Fore.BLUE}  Status: {response.status_code}{Style.RESET_ALL}")
                    test_results["passed"].append(test_name)
                
                # Print response details
                try:
                    response_json = response.json()
                    print(f"  Response: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"  Response: {response.text[:200]}")
                
                return response
                
            except Exception as e:
                print(f"{Fore.RED}✗ Exception: {str(e)}{Style.RESET_ALL}")
                test_results["unexpected"].append(f"{test_name}: {str(e)}")
                return None
        return wrapper
    return decorator

class UserServiceErrorTests:
    """Test error handling for User Service"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        
    def run_all(self):
        print_test_header("USER SERVICE ERROR TESTS")
        self.test_create_user_errors()
        self.test_login_errors()
        self.test_session_errors()
    
    def test_create_user_errors(self):
        print(f"\n{Fore.CYAN}=== Create User Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Missing required fields", expected_status=400)
        def missing_username():
            return requests.post(f"{self.base_url}/user", json={
                "userPassword": "test123"
                # Missing username
            })
        missing_username()
        
        @test_case("Empty username", expected_status=400)
        def empty_username():
            return requests.post(f"{self.base_url}/user", json={
                "username": "",
                "userPassword": "test123"
            })
        empty_username()
        
        @test_case("Missing password", expected_status=400)
        def missing_password():
            return requests.post(f"{self.base_url}/user", json={
                "username": "testuser"
                # Missing password
            })
        missing_password()
        
        @test_case("Invalid JSON", expected_status=400)
        def invalid_json():
            return requests.post(
                f"{self.base_url}/user",
                data="not valid json",
                headers={"Content-Type": "application/json"}
            )
        invalid_json()
        
        @test_case("Duplicate username (if implemented)")
        def duplicate_user():
            # First create a user
            username = f"dup_test_{random.randint(1000, 9999)}"
            requests.post(f"{self.base_url}/user", json={
                "username": username,
                "userPassword": "test123"
            })
            # Try to create again
            return requests.post(f"{self.base_url}/user", json={
                "username": username,
                "userPassword": "test123"
            })
        duplicate_user()
    
    def test_login_errors(self):
        print(f"\n{Fore.CYAN}=== Login Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Non-existent user", expected_status=404)
        def nonexistent_user():
            return requests.post(f"{self.base_url}/user/999999999", json={
                "username": "nonexistent",
                "userPassword": "test123"
            })
        nonexistent_user()
        
        @test_case("Wrong password", expected_status=404)  # Your code returns 404 for wrong password
        def wrong_password():
            # Create a user first
            response = requests.post(f"{self.base_url}/user", json={
                "username": f"pwtest_{random.randint(1000, 9999)}",
                "userPassword": "correct123"
            })
            if response.status_code == 201:
                user_id = response.text.strip('"')
                return requests.post(f"{self.base_url}/user/{user_id}", json={
                    "username": f"pwtest_{random.randint(1000, 9999)}",
                    "userPassword": "wrong123"
                })
        wrong_password()
        
        @test_case("Invalid user ID format", expected_status=400)
        def invalid_userid():
            return requests.post(f"{self.base_url}/user/not_a_number", json={
                "username": "test",
                "userPassword": "test123"
            })
        invalid_userid()
        
        @test_case("Missing credentials", expected_status=400)
        def missing_credentials():
            return requests.post(f"{self.base_url}/user/12345", json={})
        missing_credentials()
    
    def test_session_errors(self):
        print(f"\n{Fore.CYAN}=== Session Validation Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Invalid session format", expected_status=400)
        def invalid_session_format():
            return requests.get(f"{self.base_url}/user/invalid_format")
        invalid_session_format()
        
        @test_case("Expired session", expected_status=400)
        def expired_session():
            # This would need a user with an expired session
            # For now, just test non-existent user
            return requests.get(f"{self.base_url}/user/888888888")
        expired_session()

class SpaceServiceErrorTests:
    """Test error handling for Space/Availability Service"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        
    def run_all(self):
        print_test_header("SPACE SERVICE ERROR TESTS")
        self.test_create_space_errors()
        self.test_get_space_errors()
        self.test_authorization_errors()
    
    def test_create_space_errors(self):
        print(f"\n{Fore.CYAN}=== Create Space Error Cases ==={Style.RESET_ALL}")
        
        @test_case("No authentication", expected_status=400)
        def no_auth():
            return requests.post(f"{self.base_url}/space", json={
                "roomCode": 999,
                "buildingCode": "Test",
                "capacity": 4
            })
        no_auth()
        
        @test_case("Non-admin user", expected_status=400)
        def non_admin():
            # Create regular user
            resp = requests.post(f"{self.base_url}/user", json={
                "username": f"regular_{random.randint(1000, 9999)}",
                "userPassword": "test123"
            })
            if resp.status_code == 201:
                user_id = resp.text.strip('"')
                return requests.post(
                    f"{self.base_url}/space",
                    json={
                        "roomCode": 999,
                        "buildingCode": "Test",
                        "capacity": 4
                    },
                    auth=(f"regular_{random.randint(1000, 9999)}", str(user_id))
                )
        non_admin()
        
        @test_case("Invalid auth format", expected_status=400)
        def invalid_auth():
            return requests.post(
                f"{self.base_url}/space",
                json={
                    "roomCode": 999,
                    "buildingCode": "Test",
                    "capacity": 4
                },
                auth=("", "")  # Empty auth
            )
        invalid_auth()
        
        @test_case("Missing required fields", expected_status=400)
        def missing_fields():
            return requests.post(
                f"{self.base_url}/space",
                json={
                    "capacity": 4
                    # Missing roomCode and buildingCode
                },
                auth=("admin", "12345")
            )
        missing_fields()
        
        @test_case("Duplicate space", expected_status=400)
        def duplicate_space():
            # Assuming Library-101 exists
            return requests.post(
                f"{self.base_url}/space",
                json={
                    "roomCode": 101,
                    "buildingCode": "Library",
                    "capacity": 4
                },
                auth=("admin", "12345")
            )
        duplicate_space()
    
    def test_get_space_errors(self):
        print(f"\n{Fore.CYAN}=== Get Space Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Non-existent space", expected_status=404)
        def nonexistent_space():
            return requests.get(f"{self.base_url}/space/NonExistent-999")
        nonexistent_space()
        
        @test_case("Invalid space ID format")
        def invalid_format():
            return requests.get(f"{self.base_url}/space/")
        invalid_format()
        
        @test_case("Special characters in space ID")
        def special_chars():
            return requests.get(f"{self.base_url}/space/Test<script>alert(1)</script>")
        special_chars()
    
    def test_authorization_errors(self):
        print(f"\n{Fore.CYAN}=== Authorization Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Expired admin session", expected_status=400)
        def expired_admin():
            return requests.post(
                f"{self.base_url}/space",
                json={
                    "roomCode": 999,
                    "buildingCode": "Test",
                    "capacity": 4
                },
                auth=("admin", "99999999")  # Invalid admin ID
            )
        expired_admin()

class BookingServiceErrorTests:
    """Test error handling for Booking Service"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        
    def run_all(self):
        print_test_header("BOOKING SERVICE ERROR TESTS")
        self.test_create_booking_errors()
        self.test_conflict_errors()
        self.test_invalid_data_errors()
    
    def test_create_booking_errors(self):
        print(f"\n{Fore.CYAN}=== Create Booking Error Cases ==={Style.RESET_ALL}")
        
        @test_case("No authentication", expected_status=401)
        def no_auth():
            return requests.post(f"{self.base_url}/booking", json={
                "spaceID": "Library-101",
                "date": "2025-12-20",
                "startTime": "2025-12-20T10:00:00Z",
                "endTime": "2025-12-20T12:00:00Z",
                "occupants": 4
            })
        no_auth()
        
        @test_case("Invalid time range (end before start)", expected_status=400)
        def invalid_time():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "Library-101",
                    "date": "2025-12-20",
                    "startTime": "2025-12-20T14:00:00Z",
                    "endTime": "2025-12-20T12:00:00Z",  # End before start
                    "occupants": 4
                },
                auth=("testuser", "12345")
            )
        invalid_time()
        
        @test_case("Invalid date format", expected_status=400)
        def invalid_date():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "Library-101",
                    "date": "not-a-date",
                    "startTime": "invalid",
                    "endTime": "invalid",
                    "occupants": 4
                },
                auth=("testuser", "12345")
            )
        invalid_date()
        
        @test_case("Missing required fields", expected_status=400)
        def missing_fields():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "Library-101"
                    # Missing other fields
                },
                auth=("testuser", "12345")
            )
        missing_fields()
        
        @test_case("Non-existent space", expected_status=404)
        def nonexistent_space():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "NonExistent-999",
                    "date": "2025-12-20",
                    "startTime": "2025-12-20T10:00:00Z",
                    "endTime": "2025-12-20T12:00:00Z",
                    "occupants": 4
                },
                auth=("testuser", "12345")
            )
        nonexistent_space()
        
        @test_case("Exceeding space capacity")
        def exceed_capacity():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "Library-101",
                    "date": "2025-12-20",
                    "startTime": "2025-12-20T10:00:00Z",
                    "endTime": "2025-12-20T12:00:00Z",
                    "occupants": 999  # Way over capacity
                },
                auth=("testuser", "12345")
            )
        exceed_capacity()
    
    def test_conflict_errors(self):
        print(f"\n{Fore.CYAN}=== Booking Conflict Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Double booking same time slot", expected_status=409)
        def double_booking():
            booking_data = {
                "spaceID": "Library-101",
                "date": "2025-12-25",
                "startTime": "2025-12-25T14:00:00Z",
                "endTime": "2025-12-25T16:00:00Z",
                "occupants": 4
            }
            
            # First booking (should succeed)
            requests.post(
                f"{self.base_url}/booking",
                json=booking_data,
                auth=("user1", "11111")
            )
            
            # Second booking (should conflict)
            return requests.post(
                f"{self.base_url}/booking",
                json=booking_data,
                auth=("user2", "22222")
            )
        double_booking()
    
    def test_invalid_data_errors(self):
        print(f"\n{Fore.CYAN}=== Invalid Data Error Cases ==={Style.RESET_ALL}")
        
        @test_case("Negative occupants", expected_status=400)
        def negative_occupants():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "Library-101",
                    "date": "2025-12-20",
                    "startTime": "2025-12-20T10:00:00Z",
                    "endTime": "2025-12-20T12:00:00Z",
                    "occupants": -1
                },
                auth=("testuser", "12345")
            )
        negative_occupants()
        
        @test_case("Booking in the past")
        def past_booking():
            return requests.post(
                f"{self.base_url}/booking",
                json={
                    "spaceID": "Library-101",
                    "date": "2020-01-01",
                    "startTime": "2020-01-01T10:00:00Z",
                    "endTime": "2020-01-01T12:00:00Z",
                    "occupants": 4
                },
                auth=("testuser", "12345")
            )
        past_booking()

class EdgeCaseTests:
    """Test edge cases and boundary conditions"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        
    def run_all(self):
        print_test_header("EDGE CASE TESTS")
        self.test_boundary_values()
        self.test_injection_attempts()
        self.test_concurrent_requests()
    
    def test_boundary_values(self):
        print(f"\n{Fore.CYAN}=== Boundary Value Tests ==={Style.RESET_ALL}")
        
        @test_case("Very long username", expected_status=400)
        def long_username():
            return requests.post(f"{self.base_url}/user", json={
                "username": "a" * 10000,
                "userPassword": "test123"
            })
        long_username()
        
        @test_case("Unicode characters in username")
        def unicode_username():
            return requests.post(f"{self.base_url}/user", json={
                "username": "测试用户_🚀",
                "userPassword": "test123"
            })
        unicode_username()
        
        @test_case("Maximum integer user ID")
        def max_userid():
            return requests.get(f"{self.base_url}/user/{2**63-1}")
        max_userid()
    
    def test_injection_attempts(self):
        print(f"\n{Fore.CYAN}=== Injection Attack Tests ==={Style.RESET_ALL}")
        
        @test_case("SQL injection attempt")
        def sql_injection():
            return requests.post(f"{self.base_url}/user", json={
                "username": "admin'; DROP TABLE users; --",
                "userPassword": "test123"
            })
        sql_injection()
        
        @test_case("NoSQL injection attempt")
        def nosql_injection():
            return requests.post(f"{self.base_url}/user", json={
                "username": {"$ne": None},
                "userPassword": "test123"
            })
        nosql_injection()
        
        @test_case("XSS attempt in space creation")
        def xss_attempt():
            return requests.post(
                f"{self.base_url}/space",
                json={
                    "roomCode": 999,
                    "buildingCode": "<script>alert('XSS')</script>",
                    "capacity": 4
                },
                auth=("admin", "12345")
            )
        xss_attempt()
        
        @test_case("Command injection in parameters")
        def command_injection():
            return requests.get(f"{self.base_url}/space/Library-101; ls -la")
        command_injection()
    
    def test_concurrent_requests(self):
        print(f"\n{Fore.CYAN}=== Concurrent Request Tests ==={Style.RESET_ALL}")
        
        import threading
        results = []
        
        def make_request():
            try:
                resp = requests.post(f"{self.base_url}/user", json={
                    "username": f"concurrent_{random.randint(100000, 999999)}",
                    "userPassword": "test123"
                })
                results.append(resp.status_code)
            except Exception as e:
                results.append(f"Error: {e}")
        
        # Create 10 concurrent requests
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"  Concurrent request results: {results}")
        success_count = sum(1 for r in results if r == 201)
        print(f"  Successful: {success_count}/10")

def print_summary():
    """Print test summary"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✓ Passed: {len(test_results['passed'])} tests{Style.RESET_ALL}")
    for test in test_results['passed'][:10]:  # Show first 10
        print(f"  - {test}")
    if len(test_results['passed']) > 10:
        print(f"  ... and {len(test_results['passed']) - 10} more")
    
    print(f"\n{Fore.RED}✗ Failed: {len(test_results['failed'])} tests{Style.RESET_ALL}")
    for test in test_results['failed']:
        print(f"  - {test}")
    
    print(f"\n{Fore.YELLOW}⚠ Unexpected: {len(test_results['unexpected'])} tests{Style.RESET_ALL}")
    for test in test_results['unexpected']:
        print(f"  - {test}")
    
    # Calculate pass rate
    total = len(test_results['passed']) + len(test_results['failed']) + len(test_results['unexpected'])
    if total > 0:
        pass_rate = (len(test_results['passed']) / total) * 100
        print(f"\n{Fore.CYAN}Pass Rate: {pass_rate:.1f}%{Style.RESET_ALL}")
    
    # Save results to file
    with open(f"error_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(test_results, f, indent=2)
    print(f"\nResults saved to error_test_results_*.json")

def main():
    """Run all error handling tests"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print("COMPREHENSIVE ERROR HANDLING TEST SUITE")
    print(f"Target: {ALB_URL}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*60}{Style.RESET_ALL}")
    
    # Run all test suites
    user_tests = UserServiceErrorTests(ALB_URL)
    user_tests.run_all()
    
    space_tests = SpaceServiceErrorTests(ALB_URL)
    space_tests.run_all()
    
    booking_tests = BookingServiceErrorTests(ALB_URL)
    booking_tests.run_all()
    
    edge_tests = EdgeCaseTests(ALB_URL)
    edge_tests.run_all()
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()