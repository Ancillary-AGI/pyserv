"""
Load and stress tests using Locust
"""
from locust import HttpUser, task, between
import json


class PydanceUser(HttpUser):
    """Load test user for Pydance application"""

    wait_time = between(1, 3)

    @task(3)
    def test_homepage(self):
        """Test homepage - most frequent task"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Homepage failed: {response.status_code}")

    @task(2)
    def test_json_endpoint(self):
        """Test JSON response endpoint"""
        with self.client.get("/json", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "users" in data and len(data["users"]) == 100:
                        response.success()
                    else:
                        response.failure("Invalid JSON response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON")
            else:
                response.failure(f"JSON endpoint failed: {response.status_code}")

    @task(1)
    def test_user_creation(self):
        """Test user creation endpoint"""
        user_data = {
            "name": "Load Test User",
            "email": f"user_{self.user_id}@example.com",
            "age": 25
        }

        with self.client.post("/users",
                            json=user_data,
                            headers={"Content-Type": "application/json"},
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"User creation failed: {response.status_code}")

    @task(1)
    def test_parameterized_route(self):
        """Test parameterized routes"""
        user_id = self.user_id % 100 + 1  # Cycle through 1-100
        with self.client.get(f"/users/{user_id}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Parameterized route failed: {response.status_code}")

    @task(1)
    def test_404_error(self):
        """Test 404 error handling"""
        with self.client.get("/nonexistent", catch_response=True) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(f"Expected 404, got {response.status_code}")

    @task(1)
    def test_websocket_connection(self):
        """Test WebSocket connection (simulated)"""
        # Note: Locust doesn't natively support WebSocket testing
        # This is a placeholder for WebSocket load testing
        with self.client.get("/ws/chat", catch_response=True) as response:
            if response.status_code in [200, 101]:  # 101 = Switching Protocols
                response.success()
            else:
                response.failure(f"WebSocket connection failed: {response.status_code}")


class StressTestUser(PydanceUser):
    """Stress test user with more aggressive load"""

    wait_time = between(0.1, 0.5)  # Much faster requests

    @task(5)
    def aggressive_homepage_test(self):
        """Aggressive homepage testing"""
        for _ in range(10):  # Make multiple requests quickly
            with self.client.get("/", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Stress test failed: {response.status_code}")
                    break
        else:
            response.success()

    @task(2)
    def large_payload_test(self):
        """Test with large payloads"""
        large_data = {"data": "x" * 10000}  # 10KB payload
        with self.client.post("/large-payload",
                            json=large_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Large payload test failed: {response.status_code}")


class SpikeTestUser(PydanceUser):
    """Spike test user for sudden load increases"""

    wait_time = between(0.01, 0.1)  # Very fast requests

    @task
    def spike_test(self):
        """High-frequency requests for spike testing"""
        with self.client.get("/spike-test", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Spike test failed: {response.status_code}")
