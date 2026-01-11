import os
import uuid
from locust import HttpUser, task, between, events

# Custom metric to track LiteLLM overhead duration
overhead_durations = []

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    if response and hasattr(response, 'headers'):
        overhead_duration = response.headers.get('x-litellm-overhead-duration-ms')
        if overhead_duration:
            try:
                duration_ms = float(overhead_duration)
                overhead_durations.append(duration_ms)
                # Report as custom metric
                events.request.fire(
                    request_type="Custom",
                    name="LiteLLM Overhead Duration (ms)",
                    response_time=duration_ms,
                    response_length=0,
                )
            except (ValueError, TypeError):
                pass

class MyUser(HttpUser):
    wait_time = between(0.5, 1)  # Random wait time between requests

    def on_start(self):
        self.api_key = os.getenv('API_KEY', 'sk-L5jvenh9qObvYcmc9L74Cw')
        self.client.headers.update({'Authorization': f'Bearer {self.api_key}'})

    @task(5)
    def litellm_completion(self):
        # no cache hits with this
        payload = {
            "model": "nova-pro",
            "messages": [{"role": "user", "content": "Say hello world" }],
            "user": "my-new-end-user-1"
        }
        response = self.client.post("chat/completions", json=payload)


    @task(5)
    def litellm_completion(self):
        # no cache hits with this
        payload = {
            "model": "nova-micro",
            "messages": [{"role": "user", "content": "Say hello world"}],
            "user": "my-new-end-user-1"
        }
        response = self.client.post("chat/completions", json=payload)
