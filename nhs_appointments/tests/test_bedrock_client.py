"""Tests for Bedrock client."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestBedrockAgentClient:
    """Tests for BedrockAgentClient."""
    
    @patch.dict(os.environ, {
        "AWS_REGION": "eu-west-2",
        "BEDROCK_AGENT_ID": "test-agent-id",
        "BEDROCK_AGENT_ALIAS_ID": "test-alias-id"
    })
    @patch("boto3.client")
    def test_client_initialization(self, mock_boto_client):
        """Test client initializes correctly."""
        from bedrock_client import BedrockAgentClient
        
        client = BedrockAgentClient()
        
        assert client.agent_id == "test-agent-id"
        assert client.agent_alias_id == "test-alias-id"
    
    @patch.dict(os.environ, {
        "AWS_REGION": "eu-west-2",
        "BEDROCK_AGENT_ID": "test-agent-id"
    })
    @patch("boto3.client")
    def test_invoke_agent_simple(self, mock_boto_client):
        """Test simple agent invocation."""
        from bedrock_client import BedrockAgentClient
        
        mock_client = MagicMock()
        mock_client.invoke_agent.return_value = {
            "completion": [
                {"chunk": {"bytes": b"Hello!"}}
            ]
        }
        mock_boto_client.return_value = mock_client
        
        client = BedrockAgentClient()
        result = client.invoke_agent_simple("Book appointment")
        
        assert result == "Hello!"
    
    @patch.dict(os.environ, {"AWS_REGION": "eu-west-2", "BEDROCK_AGENT_ID": ""})
    @patch("boto3.client")
    def test_invoke_agent_not_configured(self, mock_boto_client):
        """Test error when agent not configured."""
        from bedrock_client import BedrockAgentClient
        
        client = BedrockAgentClient()
        result = client.invoke_agent_simple("Test")
        
        assert "not configured" in result.lower()


class TestFormatAction:
    """Tests for action formatting."""
    
    def test_format_booking_action(self):
        """Test formatting booking actions."""
        from bedrock_client import _format_action
        
        assert "checking" in _format_action("", "/check-availability").lower()
        assert "creating" in _format_action("", "/create-booking").lower()
        assert "confirming" in _format_action("", "/approve-booking").lower()
    
    def test_format_web_search(self):
        """Test formatting web search action."""
        from bedrock_client import _format_action
        
        result = _format_action("WebSearch", "")
        assert "nhs" in result.lower() or "search" in result.lower()
