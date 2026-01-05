"""Locust load test for NHS Patient Booking Demo.

IMPORTANT: Keep requests minimal to save on Bedrock costs!

Usage:
    # Headless mode (recommended for cost control)
    locust -f locustfile.py --headless -u 2 -r 1 -t 30s
    
    # Web UI mode
    locust -f locustfile.py
    # Then open http://localhost:8089
"""

import os
import sys
import time
from locust import HttpUser, task, between

# Add src to path for direct testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class NHSBookingUser(HttpUser):
    """Simulated patient user for load testing."""
    
    # Wait 5-10 seconds between requests to minimize costs
    wait_time = between(5, 10)
    
    # Limit total requests per user
    request_count = 0
    max_requests = 3  # Only 3 requests per user to save costs
    
    def on_start(self):
        """Called when user starts."""
        self.session_id = f"load-test-{int(time.time())}"
        self.request_count = 0
    
    @task(3)
    def book_gp_appointment(self):
        """Test booking a GP appointment."""
        if self.request_count >= self.max_requests:
            return
        
        self.request_count += 1
        
        # This would hit the Streamlit app or API
        # For demo, we just simulate the request
        self.client.post(
            "/api/chat",
            json={
                "message": "I need to book a GP appointment",
                "session_id": self.session_id
            },
            catch_response=True
        )
    
    @task(2)
    def check_availability(self):
        """Test checking availability."""
        if self.request_count >= self.max_requests:
            return
        
        self.request_count += 1
        
        self.client.post(
            "/api/chat",
            json={
                "message": "What appointments are available next week?",
                "session_id": self.session_id
            },
            catch_response=True
        )
    
    @task(1)
    def ask_nhs_info(self):
        """Test asking for NHS information."""
        if self.request_count >= self.max_requests:
            return
        
        self.request_count += 1
        
        self.client.post(
            "/api/chat",
            json={
                "message": "What services does the NHS provide?",
                "session_id": self.session_id
            },
            catch_response=True
        )


class DirectBedrockUser(HttpUser):
    """Direct Bedrock Agent testing (no web server needed).
    
    Use this for testing the agent directly without Streamlit.
    """
    
    wait_time = between(10, 15)  # Longer wait to minimize costs
    
    request_count = 0
    max_requests = 2  # Very limited for cost control
    
    def on_start(self):
        """Initialize Bedrock client."""
        self.request_count = 0
        
        # Only import if testing directly
        try:
            from bedrock_client import BedrockAgentClient
            self.agent = BedrockAgentClient()
            self.has_agent = True
        except Exception as e:
            print(f"Could not initialize Bedrock client: {e}")
            self.has_agent = False
    
    @task
    def invoke_agent(self):
        """Test direct agent invocation."""
        if not self.has_agent or self.request_count >= self.max_requests:
            return
        
        self.request_count += 1
        
        start_time = time.time()
        try:
            response = self.agent.invoke_agent_simple(
                "I need to book a GP appointment for next week"
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Report to Locust
            self.environment.events.request.fire(
                request_type="BEDROCK",
                name="invoke_agent",
                response_time=response_time,
                response_length=len(response),
                exception=None,
                context={}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="BEDROCK",
                name="invoke_agent",
                response_time=response_time,
                response_length=0,
                exception=e,
                context={}
            )


# Simple test script for quick validation
if __name__ == "__main__":
    print("=" * 50)
    print("NHS Patient Booking - Quick Load Test")
    print("=" * 50)
    print()
    print("To run load test:")
    print("  locust -f locustfile.py --headless -u 2 -r 1 -t 30s")
    print()
    print("This will:")
    print("  - Spawn 2 users")
    print("  - Each user makes max 3 requests")
    print("  - Total: ~6 Bedrock invocations")
    print("  - Estimated cost: < $0.10")
    print()
    print("For web UI:")
    print("  locust -f locustfile.py")
    print("  Then open http://localhost:8089")
