import random
import datetime

from locust import FastHttpUser, task, between


def today_date_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def iso_time(hour, minute):
    now = datetime.datetime.utcnow()
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat() + "Z"


class BookingConcurrencyUser(FastHttpUser):
    # Very small wait to approximate continuous requests from each user
    wait_time = between(0.0, 0.1)

    def on_start(self):
        self.date = today_date_str()

    @task
    def create_booking(self):
        start_time = iso_time(9, 0)
        end_time = iso_time(11, 0)

        payload = {
            "spaceID": "SPACE-101",
            "date": self.date,
            "userID": 1,
            "occupants": random.randint(1, 4),
            "startTime": start_time,
            "endTime": end_time,
        }

        # This measures end-to-end booking completion time as seen by the client
        with self.client.post(
            "/booking",
            json=payload,
            auth=("admin", "1"),
            name="POST /booking (concurrency)",
            catch_response=True,
        ) as response:
            if 200 <= response.status_code < 300:
                # Treat as success; Locust records latency for completion time
                pass
            else:
                response.failure(f"Status code {response.status_code}")
