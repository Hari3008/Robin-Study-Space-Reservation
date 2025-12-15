# locust_file.py
import random
import json
from datetime import datetime, timedelta
from locust import HttpUser, task, between
import base64
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize with default space IDs - these should match your DynamoDB
KNOWN_SPACE_IDS = ['TEST-100', 'TEST-101', 'TEST-102', 'TEST-103', 'TEST-104']
CREATED_USER_IDS = []

class BookingUser(HttpUser):
    """Simulates a user making bookings"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Create and login a user when starting"""
        # Create a unique user
        self.user_index = random.randint(10000, 99999)
        self.username = f'locust{self.user_index}'
        self.password = 'testpass123'
        self.user_id = None
        
        # Create the user
        self.create_user()
        
        # Login if user was created
        if self.user_id:
            self.login()
    
    def create_user(self):
        """Create a new user"""
        with self.client.post('/user',
            json={
                'username': self.username,
                'userPassword': self.password
            },
            catch_response=True,
            name='/user - create'
        ) as response:
            if response.status_code == 201:
                self.user_id = response.json()
                CREATED_USER_IDS.append(self.user_id)
                response.success()
                logger.info(f"Created user {self.username} with ID {self.user_id}")
            else:
                # Failed to create, try to use existing user
                response.failure(f"Failed to create user: {response.status_code}")
                # Use a fake ID to continue testing
                self.user_id = self.user_index
    
    def login(self):
        """Login to establish session"""
        if not self.user_id:
            return
            
        with self.client.post(f'/user/{self.user_id}',
            json={
                'username': self.username,
                'userPassword': self.password
            },
            catch_response=True,
            name='/user - login'
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(20)  # High weight - main task
    def create_booking(self):
        """Main task - attempt to create a booking"""
        if not self.user_id:
            self.create_user()  # Try to create user again
            
        if not self.user_id:
            return
        
        # Pick a random space from our known IDs
        space_id = random.choice(KNOWN_SPACE_IDS)
        
        # Generate booking for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        start_hour = random.randint(9, 17)
        duration = random.choice([1, 2])
        
        booking_data = {
            'spaceID': space_id,
            'date': tomorrow,
            'userID': self.user_id,
            'occupants': random.randint(2, 10),
            'startTime': f'2000-01-01T{start_hour:02d}:00:00Z',
            'endTime': f'2000-01-01T{start_hour+duration:02d}:00:00Z'
        }
        
        # Create auth header
        auth_string = base64.b64encode(f'{self.username}:{self.user_id}'.encode()).decode()
        
        with self.client.post('/booking',
            json=booking_data,
            headers={'Authorization': f'Basic {auth_string}'},
            catch_response=True,
            name='/booking - create'
        ) as response:
            if response.status_code == 201:
                response.success()
                booking_id = response.json()
                logger.info(f"✓ Booking {booking_id} created")
            elif response.status_code == 400:
                try:
                    error = response.json()
                    err_code = error.get('ErrCode', '')
                    
                    if err_code == 'CONFLICT':
                        # Conflicts are expected with concurrent bookings
                        response.success()
                    elif err_code in ['SESSION EXPIRED', 'SESSION ERROR']:
                        response.failure("Session expired")
                        self.login()  # Re-login and retry
                    elif err_code == 'INVALID SPACE':
                        response.failure(f"Invalid space: {space_id}")
                    else:
                        response.failure(f"{err_code}: {error.get('Message', '')}")
                except:
                    response.failure(f"Bad request: {response.text[:100]}")
            else:
                response.failure(f"Unexpected status {response.status_code}")
    
    @task(20)
    def get_booking(self):
        """Try to retrieve a random booking"""
        # Generate random booking ID to check
        booking_id = random.randint(10000, 99999)
        date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        with self.client.get(f'/booking/{date}/{booking_id}',
            catch_response=True,
            name='/booking - get'
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Not found is expected for random IDs
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")
    
    @task(1)
    def validate_session(self):
        """Check if session is still valid"""
        if not self.user_id:
            return
        
        with self.client.get(f'/user/{self.user_id}',
            catch_response=True,
            name='/user - validate'
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 400:
                # Session expired - this is normal
                response.success()
                self.login()  # Re-login
            elif response.status_code == 404:
                # User not found
                response.failure("User not found")
                self.create_user()  # Try to recreate
            else:
                response.failure(f"Unexpected status {response.status_code}")

# Optional: Admin user to create spaces
class SetupUser(HttpUser):
    """One-time setup user that creates spaces"""
    wait_time = between(60, 120)  # Run occasionally
    
    def on_start(self):
        """Create admin and spaces on start"""
        self.setup_spaces()
    
    def setup_spaces(self):
        """Create the test spaces if they don't exist"""
        # Create admin
        with self.client.post('/user',
            json={'username': 'admin', 'userPassword': 'adminpass123'},
            catch_response=True
        ) as response:
            if response.status_code == 201:
                admin_id = response.json()
                response.success()
                
                # Login admin
                with self.client.post(f'/user/{admin_id}',
                    json={'username': 'admin', 'userPassword': 'adminpass123'},
                    catch_response=True
                ) as login_resp:
                    login_resp.success()
                
                # Create spaces
                for i in range(5):
                    room_code = 100 + i
                    auth = base64.b64encode(f'admin:{admin_id}'.encode()).decode()
                    
                    with self.client.post('/space',
                        json={
                            'roomCode': room_code,
                            'buildingCode': 'TEST',
                            'capacity': 20,
                            'openTime': '2000-01-01T08:00:00Z',
                            'closeTime': '2000-01-01T22:00:00Z'
                        },
                        headers={'Authorization': f'Basic {auth}'},
                        catch_response=True
                    ) as space_resp:
                        if space_resp.status_code in [201, 400]:
                            space_resp.success()  # 400 means it already exists
    
    @task
    def idle(self):
        """Just wait - setup is done in on_start"""
        pass