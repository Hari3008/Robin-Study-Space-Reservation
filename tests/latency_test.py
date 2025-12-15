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

# Multiple booking 
def new_booking(url, admin_id, room_ids):
    response_latency = {}
    username = "ADMIN"
    userId = f"{admin_id}"
    credentials = f"{username}:{userId}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    for id in room_ids:
        payload = json.dumps({
            "SpaceID": id,
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

        print(response.json())

        response_time = (end_request - start_request) * 1000

        if response.status_code in response_latency.keys():
            response_latency[response.status_code].append((start_request, end_request, response_time))
        else:
             response_latency[response.status_code] = [(start_request, end_request, response_time)]

    return response_latency







# Replace with your EC2 public IP
ALB_DNS = "http://CS6650L2-alb-1619864770.us-east-1.elb.amazonaws.com:80"
USERS_URL = f"{ALB_DNS}/user"
SPACES_URL = f"{ALB_DNS}/space"
BOOKING_URL = f"{ALB_DNS}/booking"
N_ITERATIONS = 100
ADMIN_ID = 21930910619

# # Run the test
# print(f"Starting load test...")
# print(f"----------------------------- \n\n\n STEP 1: CREATE NEW USERS\n\n")
# output = new_user(USERS_URL, N_ITERATIONS, False) # Other Users 
# output_admin = new_user(USERS_URL, 1, True)             # CAN ONLY BE 1 - ADMIN
# plot_latency_dict(output, "(User Creation)")

# # SAMPLE OUTPUT
# #output = {201: [(1765373402.6919, 1765373407.7304618, 5038.561820983887), (1765373407.730531, 1765373412.339881, 4609.349966049194), (1765373412.3399591, 1765373417.049943, 4709.983825683594), (1765373417.050019, 1765373421.676874, 4626.85489654541), (1765373421.67695, 1765373426.299867, 4622.91693687439), (1765373426.299901, 1765373430.8709, 4570.998907089233), (1765373430.870985, 1765373435.496673, 4625.688076019287), (1765373435.496702, 1765373440.0895638, 4592.861890792847), (1765373440.089597, 1765373444.802749, 4713.151931762695), (1765373444.802907, 1765373449.399004, 4596.096992492676), (1765373449.3990881, 1765373453.992734, 4593.645811080933), (1765373453.9928188, 1765373458.62382, 4631.001234054565), (1765373458.6238751, 1765373463.439965, 4816.089868545532), (1765373463.440015, 1765373468.044446, 4604.430913925171), (1765373468.0444732, 1765373472.680672, 4636.1987590789795), (1765373472.680875, 1765373477.3649669, 4684.091806411743), (1765373477.365047, 1765373481.9639838, 4598.9367961883545), (1765373481.964011, 1765373486.616674, 4652.662992477417), (1765373486.616715, 1765373491.173694, 4556.978940963745), (1765373491.173771, 1765373495.7870588, 4613.287925720215), (1765373495.787085, 1765373500.391419, 4604.333877563477), (1765373500.391505, 1765373505.061454, 4669.949054718018), (1765373505.0615392, 1765373509.726497, 4664.957761764526), (1765373509.726548, 1765373514.305717, 4579.169034957886), (1765373514.3057961, 1765373519.041893, 4736.0968589782715), (1765373519.041929, 1765373523.7019331, 4660.004138946533), (1765373523.7020092, 1765373528.3616629, 4659.653663635254), (1765373528.361741, 1765373533.0716329, 4709.891796112061), (1765373533.071712, 1765373537.782393, 4710.680961608887), (1765373537.782433, 1765373542.4913821, 4708.949089050293), (1765373542.4914088, 1765373547.206503, 4715.094089508057), (1765373547.20658, 1765373551.796698, 4590.118169784546), (1765373551.796774, 1765373556.398327, 4601.553201675415), (1765373556.398426, 1765373561.032736, 4634.310007095337), (1765373561.03279, 1765373565.6371148, 4604.324817657471), (1765373565.6371698, 1765373570.266124, 4628.954172134399), (1765373570.266176, 1765373574.954616, 4688.4400844573975), (1765373574.9546921, 1765373579.603908, 4649.215936660767), (1765373579.603965, 1765373584.3756459, 4771.68083190918), (1765373584.3757231, 1765373588.9691782, 4593.455076217651), (1765373588.969236, 1765373593.692658, 4723.422050476074), (1765373593.692687, 1765373598.318797, 4626.110076904297), (1765373598.318877, 1765373602.910924, 4592.0469760894775), (1765373602.911005, 1765373607.556736, 4645.730972290039), (1765373607.55679, 1765373612.1924028, 4635.612726211548), (1765373612.1924548, 1765373616.767026, 4574.571132659912), (1765373616.767061, 1765373621.445364, 4678.303003311157), (1765373621.44543, 1765373626.154428, 4708.997964859009), (1765373626.154506, 1765373630.78651, 4632.004022598267), (1765373630.786571, 1765373635.4738, 4687.2289180755615), (1765373635.473999, 1765373640.069376, 4595.376968383789), (1765373640.0694542, 1765373644.802422, 4732.967853546143), (1765373644.8025, 1765373649.40225, 4599.75004196167), (1765373649.4023309, 1765373654.0102139, 4607.882976531982), (1765373654.010274, 1765373658.719975, 4709.701061248779), (1765373658.720052, 1765373663.3261828, 4606.130838394165), (1765373663.32621, 1765373667.986656, 4660.445928573608), (1765373667.986748, 1765373672.645549, 4658.801078796387), (1765373672.645586, 1765373677.263701, 4618.114948272705), (1765373677.263911, 1765373681.89249, 4628.578901290894), (1765373681.892544, 1765373686.574145, 4681.601047515869), (1765373686.574199, 1765373691.1706991, 4596.5001583099365), (1765373691.1707451, 1765373695.892311, 4721.565961837769), (1765373695.8923898, 1765373700.530995, 4638.605117797852), (1765373700.531038, 1765373705.5179698, 4986.931800842285), (1765373705.518047, 1765373710.093855, 4575.807809829712), (1765373710.093899, 1765373714.677131, 4583.2319259643555), (1765373714.677212, 1765373719.341034, 4663.8219356536865), (1765373719.3410618, 1765373723.9498649, 4608.803033828735), (1765373723.949897, 1765373728.573395, 4623.49796295166), (1765373728.573471, 1765373733.194619, 4621.147871017456), (1765373733.1946619, 1765373737.876342, 4681.680202484131), (1765373737.876373, 1765373742.587858, 4711.484909057617), (1765373742.5878909, 1765373747.200325, 4612.434148788452), (1765373747.200403, 1765373751.771017, 4570.6140995025635), (1765373751.771093, 1765373756.423003, 4651.910066604614), (1765373756.42308, 1765373761.0953972, 4672.317266464233), (1765373761.095476, 1765373766.0371468, 4941.670894622803), (1765373766.037179, 1765373770.595406, 4558.227062225342), (1765373770.595506, 1765373775.2262552, 4630.749225616455), (1765373775.226333, 1765373779.901071, 4674.738168716431), (1765373779.901101, 1765373784.569654, 4668.552875518799), (1765373784.569731, 1765373789.182135, 4612.404108047485), (1765373789.182212, 1765373793.812651, 4630.438804626465), (1765373793.8127282, 1765373798.3962162, 4583.487987518311), (1765373798.3962429, 1765373803.005047, 4608.804225921631), (1765373803.005121, 1765373807.645816, 4640.695095062256), (1765373807.645878, 1765373812.323879, 4678.000926971436), (1765373812.323957, 1765373816.9596422, 4635.685205459595), (1765373816.959719, 1765373821.6879091, 4728.190183639526), (1765373821.687964, 1765373826.365352, 4677.387952804565), (1765373826.365429, 1765373830.989043, 4623.614072799683), (1765373830.989119, 1765373835.6015801, 4612.461090087891), (1765373835.601658, 1765373840.2833521, 4681.694030761719), (1765373840.28349, 1765373844.900647, 4617.156982421875), (1765373844.900707, 1765373849.493896, 4593.189001083374), (1765373849.49396, 1765373854.1030242, 4609.064340591431), (1765373854.10306, 1765373858.815938, 4712.877988815308), (1765373858.816035, 1765373863.401664, 4585.628986358643), (1765373863.401721, 1765373868.029525, 4627.8040409088135)]}

print(f"----------------------------- \n\n\n STEP 2: CREATE NEW SPACE\n\n")
spaces_output, room_ids = new_space(SPACES_URL,ADMIN_ID, N_ITERATIONS)
print(room_ids)
# plot_latency_dict(spaces_output, "(Space Creation)")

# SAMPLE OUTPUT
#room_ids = ['SNELL-8717', 'SNELL-3301', 'SNELL-4303', 'SNELL-6220', 'SNELL-3102', 'SNELL-5105', 'SNELL-5262', 'SNELL-9497', 'SNELL-3930', 'SNELL-2656', 'SNELL-1477', 'SNELL-3151', 'SNELL-1696', 'SNELL-7724', 'SNELL-2047', 'SNELL-6482', 'SNELL-8262', 'SNELL-5290', 'SNELL-1806', 'SNELL-8596', 'SNELL-1419', 'SNELL-3182', 'SNELL-2188', 'SNELL-7774', 'SNELL-3559', 'SNELL-516', 'SNELL-6946', 'SNELL-5410', 'SNELL-7926', 'SNELL-23', 'SNELL-6698', 'SNELL-1905', 'SNELL-7697', 'SNELL-862', 'SNELL-573', 'SNELL-22', 'SNELL-9968', 'SNELL-6763', 'SNELL-3626', 'SNELL-9489', 'SNELL-9227', 'SNELL-7504', 'SNELL-4188', 'SNELL-8780', 'SNELL-138', 'SNELL-5860', 'SNELL-1424', 'SNELL-3526', 'SNELL-9660', 'SNELL-1642', 'SNELL-4363', 'SNELL-7775', 'SNELL-4427', 'SNELL-8838', 'SNELL-4913', 'SNELL-9370', 'SNELL-4262', 'SNELL-6992', 'SNELL-7256', 'SNELL-9373', 'SNELL-8854', 'SNELL-3484', 'SNELL-3852', 'SNELL-7068', 'SNELL-9515', 'SNELL-4430', 'SNELL-630', 'SNELL-8361', 'SNELL-9524', 'SNELL-2103', 'SNELL-1289', 'SNELL-9970', 'SNELL-874', 'SNELL-6303', 'SNELL-1504', 'SNELL-3220', 'SNELL-3900', 'SNELL-7369', 'SNELL-8784', 'SNELL-1276', 'SNELL-584', 'SNELL-6617', 'SNELL-4145', 'SNELL-7784', 'SNELL-5958', 'SNELL-4816', 'SNELL-9273', 'SNELL-7276', 'SNELL-264', 'SNELL-6161', 'SNELL-7602', 'SNELL-8168', 'SNELL-8145', 'SNELL-6238', 'SNELL-5479', 'SNELL-1206', 'SNELL-2690', 'SNELL-1088', 'SNELL-9973']

print(f"----------------------------- \n\n\n STEP 3: CREATE NEW BOOKING\n\n")
booking_output = new_booking(BOOKING_URL, ADMIN_ID, room_ids)
# print(booking_output)
plot_latency_dict(booking_output, "(Booking Creation)")

