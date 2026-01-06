"""Locust load test for NHS Patient Booking Demo.

IMPORTANT: Keep requests minimal to save on Bedrock costs!

Usage:
    # From patient_bookings directory:
    cd patient_bookings
    
    # Headless mode (recommended for cost control)
    locust -f scripts/locustfile.py --headless -u 2 -r 1 -t 30s
    
    # Web UI mode
    locust -f scripts/locustfile.py
    # Then open http://localhost:8089
"""

import os
import sys
import time
import uuid
from locust import User, task, between

# Add src to path for direct testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Agent configurations
SINGLE_AGENT_ID = os.environ.get("BEDROCK_AGENT_ID", "P7QFL8LKUN")
SINGLE_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "QGFY7425NI")
SUPERVISOR_AGENT_ID = os.environ.get("SUPERVISOR_AGENT_ID", "R5CKKTHOFB")
SUPERVISOR_ALIAS_ID = os.environ.get("SUPERVISOR_ALIAS_ID", "CWU2HM8ITH")
REGION = os.environ.get("AWS_REGION", "us-east-1")


class BedrockAgentUser(User):
    """Direct Bedrock Agent load testing.
    
    Tests the agent directly without going through Streamlit.
    """
    
    wait_time = between(10, 15)  # Longer wait to minimize costs
    
    request_count = 0
    max_requests = 3  # Limited for cost control
    
    # Test messages
    test_messages = [
        "I need to book a GP appointment for next week",
        "What appointments are available on Monday?",
        "Can I see a specialist for back pain?",
        "What should I bring to my appointment?",
        "I need an urgent appointment today",
    ]
    
    def on_start(self):
        """Initialize Bedrock client."""
        import boto3
        self.client = boto3.client('bedrock-agent-runtime', region_name=REGION)
        self.session_id = f"load-test-{uuid.uuid4().hex[:8]}"
        self.request_count = 0
        self.message_index = 0
    
    @task(3)
    def test_single_agent(self):
        """Test the single agent."""
        if self.request_count >= self.max_requests:
            return
        
        self._invoke_agent(
            SINGLE_AGENT_ID, 
            SINGLE_ALIAS_ID, 
            "single_agent"
        )
    
    @task(2)
    def test_supervisor_agent(self):
        """Test the multi-agent supervisor."""
        if self.request_count >= self.max_requests:
            return
        
        self._invoke_agent(
            SUPERVISOR_AGENT_ID, 
            SUPERVISOR_ALIAS_ID, 
            "supervisor_agent"
        )
    
    def _invoke_agent(self, agent_id: str, alias_id: str, name: str):
        """Invoke an agent and report metrics."""
        self.request_count += 1
        message = self.test_messages[self.message_index % len(self.test_messages)]
        self.message_index += 1
        
        start_time = time.time()
        response_text = ""
        
        try:
            response = self.client.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=f"{self.session_id}-{self.request_count}",
                inputText=message,
                enableTrace=False
            )
            
            for event in response['completion']:
                if 'chunk' in event:
                    response_text += event['chunk']['bytes'].decode('utf-8')
            
            response_time = (time.time() - start_time) * 1000
            
            self.environment.events.request.fire(
                request_type="BEDROCK",
                name=name,
                response_time=response_time,
                response_length=len(response_text),
                exception=None,
                context={}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="BEDROCK",
                name=name,
                response_time=response_time,
                response_length=0,
                exception=e,
                context={}
            )


# Quick validation when run directly
if __name__ == "__main__":
    print("=" * 50)
    print("NHS Patient Booking - Load Test")
    print("=" * 50)
    print()
    print("To run load test from patient_bookings directory:")
    print()
    print("  # Headless mode (recommended)")
    print("  locust -f scripts/locustfile.py --headless -u 2 -r 1 -t 30s")
    print()
    print("  # Web UI mode")
    print("  locust -f scripts/locustfile.py")
    print("  # Then open http://localhost:8089")
    print()
    print("This will:")
    print("  - Spawn 2 users")
    print("  - Each user makes max 3 requests")
    print("  - Tests both single and multi-agent")
    print("  - Estimated cost: < $0.20")
