"""NHS Patient Booking Demo - Streamlit App.

A demo showing multi-agent booking with real-time status updates.

Usage:
    cd patient_bookings
    streamlit run scripts/streamlit_app.py
"""

import os
import sys
import uuid

import boto3
import streamlit as st

# Agent configurations - update after terraform apply
AGENTS = {
    "Single Agent": {
        "agent_id": os.environ.get("BEDROCK_AGENT_ID", "P7QFL8LKUN"),
        "alias_id": os.environ.get("BEDROCK_AGENT_ALIAS_ID", "QGFY7425NI"),
        "description": "Single agent with all capabilities"
    },
    "Multi-Agent Supervisor": {
        "agent_id": os.environ.get("SUPERVISOR_AGENT_ID", "R5CKKTHOFB"),
        "alias_id": os.environ.get("SUPERVISOR_ALIAS_ID", "CWU2HM8ITH"),
        "description": "Supervisor orchestrating Triage, Scheduling, and Information agents"
    }
}

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Page config
st.set_page_config(
    page_title="NHS Patient Booking",
    page_icon="🏥",
    layout="centered"
)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_agent" not in st.session_state:
    st.session_state.selected_agent = "Multi-Agent Supervisor"


@st.cache_resource
def get_bedrock_client():
    """Get Bedrock Agent Runtime client."""
    return boto3.client('bedrock-agent-runtime', region_name=REGION)


def invoke_agent(client, agent_id: str, alias_id: str, message: str, session_id: str):
    """Invoke a Bedrock agent and yield events."""
    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=message,
            enableTrace=True
        )
        
        for event in response['completion']:
            if 'chunk' in event:
                yield {
                    "type": "text",
                    "content": event['chunk']['bytes'].decode('utf-8')
                }
            elif 'trace' in event:
                trace = event.get('trace', {}).get('trace', {})
                if 'orchestrationTrace' in trace:
                    orch = trace['orchestrationTrace']
                    
                    # Check for collaborator routing
                    if 'invocationInput' in orch:
                        inv = orch['invocationInput']
                        if 'agentCollaboratorInvocationInput' in inv:
                            collab = inv['agentCollaboratorInvocationInput']
                            yield {
                                "type": "status",
                                "content": f"🔄 Routing to {collab.get('collaboratorName', 'specialist')}..."
                            }
                        elif 'actionGroupInvocationInput' in inv:
                            action = inv['actionGroupInvocationInput']
                            api_path = action.get('apiPath', '')
                            action_name = api_path.replace('/', '').replace('-', ' ').title()
                            yield {
                                "type": "status", 
                                "content": f"⚡ {action_name}..."
                            }
                        elif 'knowledgeBaseLookupInput' in inv:
                            yield {
                                "type": "status",
                                "content": "📚 Searching NHS knowledge base..."
                            }
                    
                    # Check for observations
                    if 'observation' in orch:
                        obs = orch['observation']
                        if 'actionGroupInvocationOutput' in obs:
                            yield {
                                "type": "trace",
                                "content": "✅ Action completed"
                            }
                        elif 'knowledgeBaseLookupOutput' in obs:
                            yield {
                                "type": "trace",
                                "content": "✅ Found relevant information"
                            }
                            
    except Exception as e:
        yield {"type": "error", "content": str(e)}


# Header
st.title("🏥 NHS Patient Booking")
st.caption("Book GP or specialist appointments with AI assistance")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # Agent selection
    selected = st.selectbox(
        "Agent Mode",
        options=list(AGENTS.keys()),
        index=list(AGENTS.keys()).index(st.session_state.selected_agent),
        help="Choose between single agent or multi-agent supervisor"
    )
    st.session_state.selected_agent = selected
    
    agent_config = AGENTS[selected]
    st.caption(agent_config["description"])
    
    st.divider()
    
    st.header("Patient Details")
    patient_name = st.text_input("Name", value="John Smith")
    patient_email = st.text_input("Email", value="patient@example.com")
    
    st.divider()
    st.caption(f"Session: {st.session_state.session_id[:8]}...")
    st.caption(f"Agent: {agent_config['agent_id']}")
    
    if st.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and "statuses" in msg and msg["statuses"]:
            with st.expander("🔍 Processing Steps", expanded=False):
                for status in msg["statuses"]:
                    st.caption(status)

# Chat input
user_input = st.chat_input("Type your message...")

# Process user input
if user_input:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # Process with agent
    with st.chat_message("assistant"):
        status_container = st.empty()
        response_container = st.empty()
        
        statuses = []
        full_response = []
        
        client = get_bedrock_client()
        agent_config = AGENTS[st.session_state.selected_agent]
        
        status_container.info("🤔 Connecting to NHS booking system...")
        
        for event in invoke_agent(
            client,
            agent_config["agent_id"],
            agent_config["alias_id"],
            user_input,
            st.session_state.session_id
        ):
            if event["type"] == "status":
                statuses.append(event["content"])
                status_container.info(event["content"])
            elif event["type"] == "trace":
                statuses.append(event["content"])
            elif event["type"] == "text":
                full_response.append(event["content"])
                response_container.write("".join(full_response))
            elif event["type"] == "error":
                status_container.error(f"Error: {event['content']}")
        
        status_container.empty()
        final_response = "".join(full_response)
        
        if not final_response:
            final_response = "I apologize, I couldn't process your request. Please try again."
        
        response_container.write(final_response)
        
        # Check for booking confirmation
        if "confirmed" in final_response.lower() or "approved" in final_response.lower():
            st.success("📧 Confirmation sent to your email!")
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_response,
            "statuses": statuses
        })

# Quick action buttons
st.divider()
st.caption("Quick Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📅 Book GP"):
        st.session_state.messages.append({
            "role": "user",
            "content": f"I'd like to book a GP appointment. My name is {patient_name}."
        })
        st.rerun()

with col2:
    if st.button("🔍 Check Slots"):
        st.session_state.messages.append({
            "role": "user",
            "content": "What appointment slots are available next week?"
        })
        st.rerun()

with col3:
    if st.button("👨‍⚕️ Specialist"):
        st.session_state.messages.append({
            "role": "user",
            "content": "I need to see a specialist for ongoing back pain."
        })
        st.rerun()

with col4:
    if st.button("❓ NHS Info"):
        st.session_state.messages.append({
            "role": "user",
            "content": "What types of appointments does the NHS offer?"
        })
        st.rerun()

# Footer
st.divider()
st.caption("""
⚠️ **Demo Only** - This is for educational purposes. 
This system does not provide medical advice. For emergencies, call 999.
""")
