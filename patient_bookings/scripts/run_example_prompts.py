#!/usr/bin/env python3
"""Test the multi-agent supervisor for NHS Patient Booking.

This script tests the multi-agent collaboration setup where:
- Supervisor agent orchestrates the workflow
- Triage agent assesses urgency
- Scheduling agent handles bookings via Lambda
- Information agent answers NHS questions via Knowledge Base

Usage:
    python scripts/test_multi_agent.py
    python scripts/test_multi_agent.py --agent single  # Test single agent
    python scripts/test_multi_agent.py --agent supervisor  # Test multi-agent
"""

import argparse
import os
import sys
import uuid

import boto3

# Agent configurations - update these after terraform apply
AGENTS = {
    "single": {
        "agent_id": os.environ.get("BEDROCK_AGENT_ID", "P7QFL8LKUN"),
        "alias_id": os.environ.get("BEDROCK_AGENT_ALIAS_ID", "QGFY7425NI"),
        "name": "Single Agent"
    },
    "supervisor": {
        "agent_id": os.environ.get("SUPERVISOR_AGENT_ID", "R5CKKTHOFB"),
        "alias_id": os.environ.get("SUPERVISOR_ALIAS_ID", "CWU2HM8ITH"),
        "name": "Multi-Agent Supervisor"
    }
}

REGION = os.environ.get("AWS_REGION", "us-east-1")


def test_agent(agent_type: str, message: str, show_trace: bool = True):
    """Test an agent with a message."""
    config = AGENTS.get(agent_type)
    if not config:
        print(f"Unknown agent type: {agent_type}")
        return
    
    client = boto3.client('bedrock-agent-runtime', region_name=REGION)
    session_id = f"test-{agent_type}-{uuid.uuid4().hex[:8]}"
    
    print(f"\nTesting {config['name']} ({config['agent_id']})...")
    print("=" * 60)
    print(f"Input: {message}")
    print("-" * 60)
    
    try:
        response = client.invoke_agent(
            agentId=config['agent_id'],
            agentAliasId=config['alias_id'],
            sessionId=session_id,
            inputText=message,
            enableTrace=show_trace
        )
        
        print("Response:")
        for event in response['completion']:
            if 'chunk' in event:
                print(event['chunk']['bytes'].decode('utf-8'), end='')
            elif 'trace' in event and show_trace:
                trace = event.get('trace', {}).get('trace', {})
                if 'orchestrationTrace' in trace:
                    orch = trace['orchestrationTrace']
                    if 'invocationInput' in orch:
                        inv = orch['invocationInput']
                        if 'agentCollaboratorInvocationInput' in inv:
                            collab = inv['agentCollaboratorInvocationInput']
                            print(f"\n  [ROUTING TO] {collab.get('collaboratorName', 'unknown')}")
                        elif 'actionGroupInvocationInput' in inv:
                            action = inv['actionGroupInvocationInput']
                            print(f"\n  [ACTION] {action.get('actionGroupName', '')}{action.get('apiPath', '')}")
                    if 'observation' in orch:
                        obs = orch['observation']
                        if 'agentCollaboratorInvocationOutput' in obs:
                            out = obs['agentCollaboratorInvocationOutput']
                            output_text = out.get('agentCollaboratorOutput', {}).get('output', {}).get('text', '')
                            if output_text:
                                print(f"\n  [COLLABORATOR] {output_text[:200]}...")
                        elif 'actionGroupInvocationOutput' in obs:
                            out = obs['actionGroupInvocationOutput']
                            text = out.get('text', '')[:200]
                            if text:
                                print(f"\n  [LAMBDA] {text}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test NHS Patient Booking Agents")
    parser.add_argument("--agent", choices=["single", "supervisor", "both"], 
                       default="supervisor", help="Which agent to test")
    parser.add_argument("--message", type=str, 
                       default="I need to book a routine GP appointment. My name is Jane Doe.",
                       help="Message to send to the agent")
    parser.add_argument("--no-trace", action="store_true", help="Disable trace output")
    args = parser.parse_args()
    
    show_trace = not args.no_trace
    
    if args.agent == "both":
        test_agent("single", args.message, show_trace)
        test_agent("supervisor", args.message, show_trace)
    else:
        test_agent(args.agent, args.message, show_trace)


if __name__ == "__main__":
    main()
