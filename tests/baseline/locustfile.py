# #!/usr/bin/env python3
# """
# availability_actual_test.py - Test only endpoints that actually exist
# """

# from locust import HttpUser, task, between, events
# import random
# import time
# from datetime import datetime, timedelta
# import json

# # Spaces created by your baseline script
# EXISTING_SPACES = [
#     "Library-101", "Library-102", "Library-103",
#     "Engineering-101", "Engineering-102", "Engineering-103", 
#     "Science-101", "Science-102", "Science-103",
#     "Business-101", "Business-102", "Business-103",
#     "Arts-101", "Arts-102", "Arts-103"
# ]

# # Load admin credentials if available
# try:
#     with open('test_credentials.json', 'r') as f:
#         CREDENTIALS = json.load(f)
#         ADMIN_CREDS = CREDENTIALS.get('admin', {})
# except:
#     ADMIN_CREDS = {'username': 'admin', 'user_id': '12345', 'password': 'admin123'}

# class AvailabilityReadUser(HttpUser):
#     """Test ONLY the endpoints that actually exist"""
    
#     wait_time = between(1, 3)
    
#     def on_start(self):
#         self.viewed_spaces = []  # Track for cache simulation
#         self.popular_spaces = random.sample(EXISTING_SPACES, 5)  # Some spaces are more popular
    
#     @task(70)
#     def get_space_details(self):
#         """Primary endpoint that EXISTS: GET /space/:spaceId"""
#         space_id = random.choice(EXISTING_SPACES)
        
#         with self.client.get(
#             f"/space/{space_id}",
#             catch_response=True,
#             name="/space"  # Groups all space requests together
#         ) as response:
#             if response.status_code == 200:
#                 response.success()
#                 # Track cache behavior
#                 if space_id not in self.viewed_spaces:
#                     self.viewed_spaces.append(space_id)
#                     if len(self.viewed_spaces) > 20:
#                         self.viewed_spaces.pop(0)
#             elif response.status_code == 404:
#                 print{f"Space {space_id} not found"}
#                 response.failure(f"Space {space_id} not found")
#             else:
#                 response.failure(f"Unexpected status: {response.status_code}")
    
#     @task(20)
#     def get_popular_space(self):
#         """Simulate cache-friendly behavior - repeatedly access popular spaces"""
#         space_id = random.choice(self.popular_spaces)
        
#         with self.client.get(
#             f"/space/{space_id}",
#             catch_response=True,
#             name="/space"
#         ) as response:
#             if response.status_code == 200:
#                 response.success()
    
#     @task(10)
#     def health_check(self):
#         """Health check endpoint that EXISTS"""
#         with self.client.get(
#             "/space/health",
#             catch_response=True,
#             name="/space/health"
#         ) as response:
#             if response.status_code == 200:
#                 response.success()

# class AvailabilityBurstUser(HttpUser):
#     """Simulate burst traffic patterns"""
    
#     wait_time = between(0.1, 0.5)
#     weight = 2  # Less common
    
#     @task
#     def rapid_space_lookup(self):
#         """User quickly checking multiple spaces"""
#         spaces = random.sample(EXISTING_SPACES, 3)
        
#         for space_id in spaces:
#             with self.client.get(
#                 f"/space/{space_id}",
#                 catch_response=True,
#                 name="/space"
#             ) as response:
#                 if response.status_code == 200:
#                     response.success()



from locust import HttpUser, task, between
import random

# Space IDs populated in DynamoDB
EXISTING_SPACES = [
    "Library-101", "Library-102", "Library-103",
    "Engineering-101", "Engineering-102", "Engineering-103",
    "Science-101", "Science-102", "Science-103",
    "Business-101", "Business-102", "Business-103",
    "Arts-101", "Arts-102", "Arts-103"
]

class SpaceReadUser(HttpUser):
    # User wait time between requests (adjust for load)
    wait_time = between(1, 2)

    @task
    def get_space_by_id(self):
        space_id = random.choice(EXISTING_SPACES)
        self.client.get(f"/space/{space_id}", name="/space/:id")
