"""Simple Bedrock Agent client for NHS Patient Booking demo.

Uses Bedrock Agent with web search for NHS.uk information.
"""

import json
import os
import uuid
from typing import Generator

import boto3


class BedrockAgentClient:
    """Client for invoking Bedrock Agents with streaming."""
    
    def __init__(self):
        self.client = boto3.client(
            "bedrock-agent-runtime",
            region_name=os.environ.get("AWS_REGION", "eu-west-2")
        )
        self.agent_id = os.environ.get("BEDROCK_AGENT_ID")
        self.agent_alias_id = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
    
    def invoke_agent(
        self,
        message: str,
        session_id: str = None,
        enable_trace: bool = True
    ) -> Generator[dict, None, None]:
        """Invoke the agent and stream responses.
        
        Args:
            message: User message
            session_id: Session ID for conversation continuity
            enable_trace: Whether to include agent trace events
            
        Yields:
            Dict with 'type' (text/trace/status) and 'content'
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if not self.agent_id:
            yield {"type": "text", "content": "Agent not configured. Set BEDROCK_AGENT_ID."}
            return
        
        try:
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=message,
                enableTrace=enable_trace
            )
        except Exception as e:
            yield {"type": "text", "content": f"Error connecting to agent: {str(e)}"}
            return
        
        # Stream the response
        for event in response.get("completion", []):
            # Text chunk from agent
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    text = chunk["bytes"].decode("utf-8")
                    yield {"type": "text", "content": text}
            
            # Trace events (agent thinking/actions)
            if "trace" in event and enable_trace:
                trace = event["trace"].get("trace", {})
                
                # Orchestration trace
                if "orchestrationTrace" in trace:
                    orch = trace["orchestrationTrace"]
                    
                    if "modelInvocationInput" in orch:
                        yield {"type": "status", "content": "🤔 Processing..."}
                    
                    if "rationale" in orch:
                        rationale = orch["rationale"].get("text", "")
                        if rationale:
                            yield {"type": "trace", "content": f"💭 {rationale[:150]}..."}
                    
                    if "invocationInput" in orch:
                        inv = orch["invocationInput"]
                        if "actionGroupInvocationInput" in inv:
                            action = inv["actionGroupInvocationInput"]
                            action_name = action.get("actionGroupName", "")
                            api_path = action.get("apiPath", "")
                            yield {"type": "status", "content": f"⚙️ {_format_action(action_name, api_path)}"}
                    
                    if "observation" in orch:
                        yield {"type": "status", "content": "✅ Step completed"}
    
    def invoke_agent_simple(self, message: str, session_id: str = None) -> str:
        """Invoke agent and return complete response (non-streaming).
        
        Args:
            message: User message
            session_id: Session ID
            
        Returns:
            Complete response text
        """
        full_response = []
        for event in self.invoke_agent(message, session_id, enable_trace=False):
            if event["type"] == "text":
                full_response.append(event["content"])
        return "".join(full_response)


def _format_action(action_name: str, api_path: str = "") -> str:
    """Format action name for display."""
    
    # Map API paths to friendly messages
    path_messages = {
        "/check-availability": "Checking available appointments...",
        "/create-booking": "Creating your booking...",
        "/approve-booking": "Confirming your appointment...",
        "/send-confirmation": "Sending confirmation...",
    }
    
    if api_path and api_path in path_messages:
        return path_messages[api_path]
    
    # Fallback for action group names
    if "WebSearch" in action_name:
        return "🔍 Searching NHS.uk..."
    
    return f"Processing: {action_name}"
