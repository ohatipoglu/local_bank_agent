"""
Load Testing Suite for Local Bank AI Agent.

Uses Locust for load testing.

Installation:
    pip install locust

Usage:
    # Start Locust web UI
    locust -f tests/load/test_load_audio_processing.py --host=http://localhost:8000

    # Run headless (no UI)
    locust -f tests/load/test_load_audio_processing.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s

    # Parameters:
    #   -u: Number of concurrent users
    #   -r: Spawn rate (users per second)
    #   -t: Test duration
"""

import random
import time
from io import BytesIO
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner


class AudioProcessingUser(HttpUser):
    """
    Simulated user that processes audio through the banking agent.
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task(3)
    def process_audio(self):
        """
        Simulate audio processing request.

        This task sends a mock audio file to the /process_audio endpoint.
        """
        # Generate mock audio data (1 second of silence in WAV format)
        # In real tests, use actual audio files
        audio_data = self._generate_mock_wav()

        files = {
            "audio": ("test_audio.wav", audio_data, "audio/wav"),
        }

        data = {
            "strictness": random.choice([2, 3, 4]),
            "session_id": f"load_test_session_{random.randint(1, 100)}",
        }

        with self.client.post(
            "/process_audio",
            files=files,
            data=data,
            catch_response=True,
            timeout=120.0,
        ) as response:
            if response.status_code == 200:
                json_resp = response.json()
                if json_resp.get("status") == "success":
                    response.success()
                else:
                    response.failure(f"API error: {json_resp.get('message')}")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def health_check(self):
        """
        Simulate health check requests.
        """
        self.client.get("/api/health")

    @task(1)
    def get_models(self):
        """
        Simulate getting available models.
        """
        self.client.get("/api/models")

    @task(1)
    def authenticate(self):
        """
        Simulate customer authentication.
        """
        # Use valid test TC Kimlik numbers
        test_customers = ["10000000146", "20000000114"]
        customer_id = random.choice(test_customers)

        data = {
            "customer_id": customer_id,
        }

        self.client.post("/api/auth", data=data)

    def _generate_mock_wav(self) -> bytes:
        """
        Generate a minimal valid WAV file for testing.

        This creates a very short silent WAV file.
        """
        import wave
        import struct

        # Create WAV in memory
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            # Set parameters: mono, 16-bit, 16kHz
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)

            # Generate 1 second of silence
            for _ in range(16000):
                wav_file.writeframes(struct.pack("h", 0))

        buffer.seek(0)
        return buffer.read()


class APIv1User(HttpUser):
    """
    Simulated user for API v1 endpoints.
    """

    wait_time = between(0.5, 2)

    @task(3)
    def v1_health(self):
        """Test v1 health endpoint."""
        self.client.get("/api/v1/health")

    @task(2)
    def v1_models(self):
        """Test v1 models endpoint."""
        self.client.get("/api/v1/models")

    @task(1)
    def v1_auth(self):
        """Test v1 authentication endpoint."""
        test_customers = ["10000000146", "20000000114"]
        customer_id = random.choice(test_customers)

        data = {"customer_id": customer_id}
        self.client.post("/api/v1/auth/auth", data=data)


# Event hooks for test statistics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """
    Log request statistics.
    """
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called when load test starts.
    """
    print("=" * 60)
    print("Load Test Starting")
    print("=" * 60)
    print(f"Target Host: {environment.host}")
    print(f"Available users: {[u.__name__ for u in environment.user_classes]}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Called when load test stops.
    """
    print("=" * 60)
    print("Load Test Completed")
    print("=" * 60)

    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Success Rate: {(1 - stats.total.fail_ratio) * 100:.2f}%")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")
    print("=" * 60)


# Configuration for distributed load testing
if __name__ == "__main__":
    import os

    # Check if running in distributed mode
    is_master = os.getenv("LOCUST_MODE") == "master"
    is_worker = os.getenv("LOCUST_MODE") == "worker"

    if is_master:
        print("Starting Locust in MASTER mode")
        os.system(
            "locust -f tests/load/test_load_audio_processing.py "
            "--master --expect-workers 2"
        )
    elif is_worker:
        print("Starting Locust in WORKER mode")
        os.system(
            "locust -f tests/load/test_load_audio_processing.py "
            "--worker --master-host=localhost"
        )
    else:
        print("Starting Locust in standalone mode")
        print("\nOpen http://localhost:8089 in your browser")
        print("Or run with --headless for CLI mode\n")
