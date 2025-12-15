import random
import json
import requests
import time
import matplotlib.pyplot as plt
import statistics
import numpy as np
import base64

from pathlib import Path


ROOT = Path(__file__).parent
LOCUST_FILE = ROOT / "locust_concurrency.py"
USER_PREFIX = "User"

# Multiple Users 
def new_user(url, n_users, admin=False):
    responses_user_ids = {}
    username_user_id = {}

    for i in range(n_users):
        user_id = random.randint(1,10000)
        username = "ADMIN" if admin else f"{USER_PREFIX}_{user_id}"
        payload = json.dumps({
            "username": username,
            "userPassword": str(user_id)
        })
        headers = {
            'Content-Type': 'application/json'
        }

        start_request = time.time()
        response = requests.request("POST", url, headers=headers, data=payload)
        end_request = time.time()

        #print(response.json())

        response_time = (end_request - start_request) * 1000

        if response.status_code in responses_user_ids.keys():
            responses_user_ids[response.status_code].append((start_request, end_request, response_time))
        else:
             responses_user_ids[response.status_code] = [(start_request, end_request, response_time)]

    return responses_user_ids

def plot_latency_dict(response_users_map, test_name):
    for response_code in response_users_map.keys():
        responses = response_users_map[response_code]

        start_times = [t[0] for t in responses] # all start times of the reponse
        first_start = start_times[0]
        start_times = [t-first_start for t in start_times]

        #end_times = [t[1] for t in responses] # all end times of the reponse
        latency_times = [t[2]/1000 for t in responses]

        print(f"MEAN LATENCY: {statistics.mean(latency_times)}")
        print(f"MEDIAN LATENCY: {statistics.median(latency_times)}")
        print(f"95%: {np.percentile(latency_times, 95)}")
        print(f"STD: {statistics.stdev(latency_times)}")

        #for i in range(len(responses)):

        plt.figure(figsize=(10, 6))
        plt.plot(start_times, latency_times, marker='o', linestyle='-', color='skyblue', markersize=4)
        plt.xlabel("Start Time (s)")
        plt.ylabel("Latency (s)")
        plt.title(f"{response_code}: Latency Over Time {test_name}")
        plt.show()

            
# Multiple spaces 
def new_space(url, admin_id, n_spaces):
    response_latency = {}

    username = "ADMIN"
    password = f"{admin_id}"
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    room_ids = []

    for i in range(n_spaces):
        room_num = random.randint(1,10000)
        payload = json.dumps({
            "buildingCode": "HASTINGS",
            "roomCode": room_num,
            "capacity": 5,
            "openTime": "2025-11-25T09:00:00Z",
            "closeTime": "2025-11-25T17:00:00Z"
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {encoded_credentials}'
        }

        room_ids.append(f"HASTINGS-{room_num}")
        
        start_request = time.time()
        response = requests.request("POST", url, headers=headers, data=payload)
        end_request = time.time()

        response_time = (end_request - start_request) * 1000

        if response.status_code in response_latency.keys():
            response_latency[response.status_code].append((start_request, end_request, response_time))
        else:
             response_latency[response.status_code] = [(start_request, end_request, response_time)]

    return response_latency, list(set(room_ids))

# test booking consistency
def booking_test(url, max_retries, admin_id, room_id):
    # Make booking (branch new)
    code, json, t = new_booking(url, admin_id, room_id)
    time.sleep(5)

    start_request = time.time()

    if code != 201:
        return -1, 0
    
    conflict_detected = False
    total_time = t
    num_tries = 0
    while not conflict_detected and num_tries <= max_retries:
        num_tries += 1

        code, json, t = new_booking(url, admin_id, room_id)
        total_time += t
        
        

        if (code == 400):
            conflict_detected = True
    
    end_request = time.time()
    response_time = (end_request - start_request)

    return num_tries, response_time

# make booking
def new_booking(url, admin_id, room_id):
    response_latency = {}
    username = "ADMIN"
    userId = f"{admin_id}"
    credentials = f"{username}:{userId}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    payload = json.dumps({
        "SpaceID": room_id,
        "Date": "2025-11-20",
        "UserID": admin_id,
        "Occupants": 3,
        "StartTime": "2025-11-25T11:00:00Z",
        "EndTime": "2025-11-25T12:15:00Z"
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_credentials}'
    }
        
    start_request = time.time()
    response = requests.request("POST", url, headers=headers, data=payload)
    end_request = time.time()

    #print(response.json())

    response_time = (end_request - start_request) * 1000

    return response.status_code, response.json(), response_time







# Replace with your EC2 public IP
ALB_DNS = "http://CS6650L2-alb-1619864770.us-east-1.elb.amazonaws.com:80"
USERS_URL = f"{ALB_DNS}/user"
SPACES_URL = f"{ALB_DNS}/space"
BOOKING_URL = f"{ALB_DNS}/booking"
N_ITERATIONS = 100
ADMIN_ID = 49247462423

# Run the test
print(f"Starting consistency test...")

print(f"----------------------------- \n\n\n Make a bunch of new spaces\n\n")
spaces_output, room_ids = new_space(SPACES_URL,ADMIN_ID, N_ITERATIONS)

print(f"----------------------------- \n\n\n Create booking with spaces \n\n")

resp_times = {}
for room in room_ids:
    num_retries, total_time = booking_test(BOOKING_URL, 5, ADMIN_ID, room)
    if num_retries in resp_times.keys():
        resp_times[num_retries].append(total_time)
    else:
        resp_times[num_retries] = [total_time]

y_to_plot = []
for retry_amount in resp_times.keys():
    avg = statistics.mean(resp_times[retry_amount])
    y_to_plot.append(avg)

plt.bar(resp_times.keys(), y_to_plot)
plt.xlabel('# Retries Before Conflict Detected')
plt.ylabel('Average Total Consistency Downtime (s)')
plt.title('Consistency Detection')
plt.show()



print(resp_times)
print("\n\n------------------\n\n")
print(retries)



#print(booking_output)

## print(booking_output)
#plot_latency_dict(booking_output, "(Booking Creation)")

