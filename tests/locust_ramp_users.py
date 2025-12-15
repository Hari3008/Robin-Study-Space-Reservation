import random
import datetime
import threading

from locust import FastHttpUser, task, between, LoadTestShape


booking_lock = threading.Lock()
known_bookings = {}


user_init_lock = threading.Lock()
initialized_user = {"user_id": None}
space_init_lock = threading.Lock()
initialized_space = {"space_ids": []}


def today_date_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def iso_time(hour, minute):
    now = datetime.datetime.utcnow()
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat() + "Z"


class BookingUser(FastHttpUser):
    wait_time = between(0.1, 1.0)

    def on_start(self):
        self.date = today_date_str()
        self.user_id = None
        self.auth = None
        self.space_ids = None

        # Ensure there is a valid user in the user-service and an active session.
        # We do this once and share the same user ID across all Locust users to
        # avoid overwhelming the user-service with user creation.
        with user_init_lock:
            if initialized_user["user_id"] is None:
                # Create user once
                create_payload = {
                    "username": "admin",
                    "userPassword": "password",
                }

                with self.client.post(
                    "/user",
                    json=create_payload,
                    name="POST /user (create)",
                    catch_response=True,
                ) as resp:
                    if 200 <= resp.status_code < 300:
                        try:
                            created_user_id = int(resp.text)
                        except ValueError:
                            resp.failure("Unexpected user ID format: %s" % resp.text)
                            return
                    else:
                        resp.failure(
                            "Failed to create user: status=%s body=%s" % (resp.status_code, resp.text)
                        )
                        return
                initialized_user["user_id"] = created_user_id

            # Create multiple spaces once via the availability service.
            # This helps distribute bookings across different rooms and reduce conflicts.
            if not initialized_space["space_ids"] and initialized_user["user_id"] is not None:
                for room in range(101, 301):  # create 200 rooms: 101-300
                    space_payload = {
                        "roomCode": room,
                        "buildingCode": f"KRIK-{self.date}-{room}-{random.randint(1, 1000000)}",
                        "capacity": 10,
                        "openTime": iso_time(8, 0),
                        "closeTime": iso_time(22, 0),
                    }

                    with self.client.post(
                        "/space",
                        json=space_payload,
                        auth=("admin", str(initialized_user["user_id"])),
                        name="POST /space (create)",
                        catch_response=True,
                    ) as resp:
                        if 200 <= resp.status_code < 300:
                            space_id = resp.text.strip().strip('"')
                            initialized_space["space_ids"].append(space_id)
                        else:
                            resp.failure(
                                "Failed to create space: status=%s body=%s" % (resp.status_code, resp.text)
                            )
                            return

        # Each Locust user reuses the same logical application user.
        self.user_id = initialized_user["user_id"]
        # BasicAuth: username is arbitrary here, password is interpreted as userId
        self.auth = ("admin", str(self.user_id))
        # Share the same list of spaces across all Locust users
        self.space_ids = list(initialized_space["space_ids"])

    def _add_booking(self, booking_id):
        with booking_lock:
            bookings_for_date = known_bookings.setdefault(self.date, set())
            bookings_for_date.add(booking_id)

    def _get_random_booking(self):
        with booking_lock:
            bookings_for_date = known_bookings.get(self.date)
            if not bookings_for_date:
                return None
            return random.choice(list(bookings_for_date))

    def _remove_booking(self, booking_id):
        with booking_lock:
            bookings_for_date = known_bookings.get(self.date)
            if not bookings_for_date:
                return
            bookings_for_date.discard(booking_id)

    @task(4)
    def create_booking(self):
        if self.user_id is None or self.auth is None:
            return
        if not self.space_ids:
            return

        # Randomize time slots to further reduce the chance of conflicts.
        # Choose a random 1- or 2-hour window between 8:00 and 21:00 UTC.
        start_hour = random.randint(8, 20)
        duration_hours = random.choice([1, 2])
        end_hour = min(start_hour + duration_hours, 22)

        start_time = iso_time(start_hour, 0)
        end_time = iso_time(end_hour, 0)

        payload = {
            "spaceID": random.choice(self.space_ids),
            "date": self.date,
            "userID": self.user_id,
            "occupants": random.randint(1, 4),
            "startTime": start_time,
            "endTime": end_time,
        }

        with self.client.post(
            "/booking",
            json=payload,
            auth=self.auth,
            name="POST /booking",
            catch_response=True,
        ) as response:
            if 200 <= response.status_code < 300:
                try:
                    booking_id = int(response.text)
                    self._add_booking(booking_id)
                except ValueError:
                    response.failure("Unexpected booking ID format: %s" % response.text)
            else:
                response.failure(
                    "Status code %s body=%s" % (response.status_code, response.text)
                )

    @task(3)
    def get_booking(self):
        if self.user_id is None or self.auth is None:
            return
        booking_id = self._get_random_booking()
        if booking_id is None:
            return

        path = f"/booking/{self.date}/{booking_id}"

        with self.client.get(
            path,
            name="GET /booking/{date}/{id}",
            auth=self.auth,
            catch_response=True,
        ) as response:
            if 200 <= response.status_code < 300:
                try:
                    _ = response.json()
                except Exception as e:
                    response.failure("Invalid JSON: %s" % e)
            else:
                response.failure("Status code %s" % response.status_code)

    @task(1)
    def delete_booking(self):
        if self.user_id is None or self.auth is None:
            return
        booking_id = self._get_random_booking()
        if booking_id is None:
            return

        path = f"/booking/{self.date}/{booking_id}"

        with self.client.delete(
            path,
            name="DELETE /booking/{date}/{id}",
            auth=self.auth,
            catch_response=True,
        ) as response:
            if 200 <= response.status_code < 300:
                self._remove_booking(booking_id)
            else:
                response.failure("Status code %s" % response.status_code)


class RampUsersShape(LoadTestShape):
    stages = [
        {"duration": 120, "users": 100, "spawn_rate": 100},
      #  {"duration": 120, "users": 1000, "spawn_rate": 15},
      #  {"duration": 180, "users": 10000, "spawn_rate": 150},
      #  {"duration": 780, "users": 10000, "spawn_rate": 1},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None
