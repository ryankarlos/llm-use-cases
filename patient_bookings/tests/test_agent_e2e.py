"""End-to-end pytest tests for NHS Patient Booking Agents.

These tests invoke the actual Bedrock agents to verify end-to-end functionality.
Requires AWS credentials and deployed infrastructure.

Usage:
    pytest tests/test_agent_e2e.py -v
    pytest tests/test_agent_e2e.py -v -k "routine"
"""

import os
import uuid
import pytest
import boto3

# Skip all tests if not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPERVISOR_AGENT_ID"),
    reason="Agent IDs not configured - set SUPERVISOR_AGENT_ID env var"
)

# Agent configurations
SUPERVISOR_AGENT_ID = os.environ.get("SUPERVISOR_AGENT_ID", "R5CKKTHOFB")
SUPERVISOR_ALIAS_ID = os.environ.get("SUPERVISOR_ALIAS_ID", "CWU2HM8ITH")
SINGLE_AGENT_ID = os.environ.get("BEDROCK_AGENT_ID", "P7QFL8LKUN")
SINGLE_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "QGFY7425NI")
REGION = os.environ.get("AWS_REGION", "us-east-1")


@pytest.fixture(scope="module")
def bedrock_client():
    """Create Bedrock Agent Runtime client."""
    return boto3.client('bedrock-agent-runtime', region_name=REGION)


@pytest.fixture
def session_id():
    """Generate unique session ID for each test."""
    return f"pytest-{uuid.uuid4().hex[:8]}"


def invoke_agent(client, agent_id: str, alias_id: str, message: str, session_id: str) -> str:
    """Invoke agent and return response text."""
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=session_id,
        inputText=message,
        enableTrace=False
    )
    
    text_parts = []
    try:
        for event in response['completion']:
            if 'chunk' in event:
                text_parts.append(event['chunk']['bytes'].decode('utf-8'))
    except Exception as e:
        if "accessDenied" in str(e).lower():
            raise PermissionError(f"Access denied to agent {agent_id}")
        raise
    
    return ''.join(text_parts)


class TestSupervisorAgent:
    """Tests for the multi-agent supervisor."""
    
    def test_routine_booking_request(self, bedrock_client, session_id):
        """Test routine GP appointment booking flow."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "I need to book a routine GP appointment. My name is Test Patient.",
            session_id
        )
        
        response_lower = response.lower()
        assert any(word in response_lower for word in ["appointment", "available", "slot", "book"])
        assert "999" not in response_lower  # Should not suggest emergency
    
    def test_urgent_booking_request(self, bedrock_client, session_id):
        """Test urgent appointment booking flow."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "I have a high fever and severe headache. I need to see a doctor urgently. My name is Urgent Patient.",
            session_id
        )
        
        response_lower = response.lower()
        # Should recognize urgency
        assert any(word in response_lower for word in ["urgent", "soon", "today", "tomorrow", "appointment"])
    
    def test_emergency_detection(self, bedrock_client, session_id):
        """Test that emergency symptoms trigger 999 advice."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "I'm having severe chest pain and difficulty breathing right now.",
            session_id
        )
        
        response_lower = response.lower()
        # Should advise calling 999 for emergency
        assert any(word in response_lower for word in ["999", "emergency", "ambulance", "immediately"])
    
    def test_information_query(self, bedrock_client, session_id):
        """Test NHS information queries."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "What should I bring to my GP appointment?",
            session_id
        )
        
        response_lower = response.lower()
        # Should provide helpful information - broader keyword check
        assert any(word in response_lower for word in [
            "bring", "nhs", "appointment", "medication", "number",
            "id", "list", "prepare", "documents", "records", "information"
        ])
    
    def test_appointment_types_query(self, bedrock_client, session_id):
        """Test query about appointment types."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "What types of appointments are available?",
            session_id
        )
        
        response_lower = response.lower()
        assert any(word in response_lower for word in ["gp", "routine", "urgent", "specialist", "appointment"])
    
    def test_no_medical_advice(self, bedrock_client, session_id):
        """Test that agent doesn't provide medical advice."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "What medicine should I take for my headache?",
            session_id
        )
        
        response_lower = response.lower()
        # Should not prescribe medication, should redirect
        assert any(word in response_lower for word in ["cannot", "medical advice", "doctor", "pharmacist", "nhs 111"])


class TestSingleAgent:
    """Tests for the single agent (non-supervisor).
    
    Note: These tests may be skipped if the single agent alias is not accessible.
    """
    
    def test_single_agent_booking(self, bedrock_client, session_id):
        """Test single agent can handle booking requests."""
        try:
            response = invoke_agent(
                bedrock_client,
                SINGLE_AGENT_ID,
                SINGLE_ALIAS_ID,
                "I need to book a GP appointment for next week. My name is Single Test.",
                session_id
            )
            
            response_lower = response.lower()
            assert any(word in response_lower for word in ["appointment", "available", "book"])
        except (PermissionError, Exception) as e:
            if "accessdenied" in str(e).lower() or "permission" in str(e).lower():
                pytest.skip("Single agent not accessible - may need alias update")
            raise
    
    def test_single_agent_emergency(self, bedrock_client, session_id):
        """Test single agent handles emergencies correctly."""
        try:
            response = invoke_agent(
                bedrock_client,
                SINGLE_AGENT_ID,
                SINGLE_ALIAS_ID,
                "I'm having chest pain and can't breathe properly.",
                session_id
            )
            
            response_lower = response.lower()
            assert any(word in response_lower for word in ["999", "emergency", "ambulance"])
        except (PermissionError, Exception) as e:
            if "accessdenied" in str(e).lower() or "permission" in str(e).lower():
                pytest.skip("Single agent not accessible - may need alias update")
            raise


class TestMultiTurnConversation:
    """Tests for multi-turn conversation flows."""
    
    def test_booking_conversation_flow(self, bedrock_client):
        """Test a complete booking conversation with multiple turns."""
        session_id = f"pytest-multi-{uuid.uuid4().hex[:8]}"
        
        # Turn 1: Initial request
        response1 = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "Hi, I'd like to book a GP appointment.",
            session_id
        )
        assert len(response1) > 0
        
        # Turn 2: Provide details
        response2 = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "My name is Multi Turn Test and I need a routine checkup.",
            session_id
        )
        
        response2_lower = response2.lower()
        assert any(word in response2_lower for word in ["available", "slot", "appointment", "book"])


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_message(self, bedrock_client, session_id):
        """Test handling of minimal input."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "Hello",
            session_id
        )
        
        # Should respond with greeting or ask how to help
        assert len(response) > 0
    
    def test_unrelated_query(self, bedrock_client, session_id):
        """Test handling of unrelated queries."""
        response = invoke_agent(
            bedrock_client,
            SUPERVISOR_AGENT_ID,
            SUPERVISOR_ALIAS_ID,
            "What's the weather like today?",
            session_id
        )
        
        # Should respond in some way - agent may redirect or explain its purpose
        assert len(response) > 0  # Just verify we get a response
