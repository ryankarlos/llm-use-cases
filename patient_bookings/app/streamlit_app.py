"""NHS Patient Booking Demo - Streamlit App.

A simple demo showing multi-agent booking with real-time status updates.
Run with: streamlit run streamlit_app.py
"""

import os
import sys
import uuid
import base64
import tempfile
from datetime import datetime

import streamlit as st

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bedrock_client import BedrockAgentClient, KnowledgeBaseClient
from audio_utils import AudioProcessor
from notifications import NotificationService

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
if "processing" not in st.session_state:
    st.session_state.processing = False

# Initialize clients
@st.cache_resource
def get_clients():
    return {
        "agent": BedrockAgentClient(),
        "kb": KnowledgeBaseClient(),
        "audio": AudioProcessor(),
        "notify": NotificationService()
    }

clients = get_clients()

# Header
st.title("🏥 NHS Patient Booking")
st.caption("Book GP or specialist appointments with AI assistance")

# Sidebar - Patient Info (demo)
with st.sidebar:
    st.header("Patient Details")
    patient_name = st.text_input("Name", value="John Smith")
    patient_email = st.text_input("Email", value="patient@example.com")
    patient_phone = st.text_input("Phone", value="+447700900000")
    preferred_lang = st.selectbox("Language", ["English", "Spanish", "French"])
    
    st.divider()
    st.caption(f"Session: {st.session_state.session_id[:8]}...")
    
    if st.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Show status updates for assistant messages
        if msg["role"] == "assistant" and "statuses" in msg:
            with st.expander("🔍 Processing Steps", expanded=False):
                for status in msg["statuses"]:
                    st.caption(status)

# Chat input
col1, col2 = st.columns([5, 1])

with col1:
    user_input = st.chat_input("Type your message or describe your symptoms...")

with col2:
    # Voice input button (simplified - in production use streamlit-webrtc)
    voice_mode = st.button("🎤", help="Voice input (demo)")

# Handle voice input (demo placeholder)
if voice_mode:
    st.info("🎤 Voice input demo: In production, this would record audio and transcribe it.")
    # In production, use streamlit-webrtc or audio_recorder_streamlit
    demo_voice_text = "I need to book an appointment with my GP for persistent headaches"
    user_input = demo_voice_text
    st.toast(f"Transcribed: {demo_voice_text}")

# Process user input
if user_input:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Display user message
    with st.chat_message("user"):
        st.write(user_input)
    
    # Process with agent
    with st.chat_message("assistant"):
        status_container = st.empty()
        response_container = st.empty()
        
        statuses = []
        full_response = []
        
        # Stream agent response
        try:
            status_container.info("🤔 Connecting to NHS booking system...")
            
            for event in clients["agent"].invoke_agent(
                message=user_input,
                session_id=st.session_state.session_id,
                enable_trace=True
            ):
                if event["type"] == "status":
                    statuses.append(event["content"])
                    status_container.info(event["content"])
                
                elif event["type"] == "trace":
                    statuses.append(event["content"])
                
                elif event["type"] == "text":
                    full_response.append(event["content"])
                    response_container.write("".join(full_response))
            
            # Clear status and show final response
            status_container.empty()
            final_response = "".join(full_response)
            
            if not final_response:
                final_response = "I apologize, I couldn't process your request. Please try again."
            
            response_container.write(final_response)
            
            # Check if booking was made (simple keyword check for demo)
            if "confirmed" in final_response.lower() and "appointment" in final_response.lower():
                # Send notifications (demo)
                st.success("📧 Confirmation sent to your email and phone!")
            
        except Exception as e:
            status_container.empty()
            error_msg = f"Sorry, there was an error: {str(e)}"
            response_container.error(error_msg)
            final_response = error_msg
            statuses = []
        
        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_response,
            "statuses": statuses
        })

# Quick action buttons
st.divider()
st.caption("Quick Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📅 Book GP"):
        st.session_state.messages.append({
            "role": "user",
            "content": "I'd like to book a GP appointment"
        })
        st.rerun()

with col2:
    if st.button("👨‍⚕️ See Specialist"):
        st.session_state.messages.append({
            "role": "user",
            "content": "I need to see a specialist"
        })
        st.rerun()

with col3:
    if st.button("❓ NHS Info"):
        st.session_state.messages.append({
            "role": "user",
            "content": "What information do you have about NHS services?"
        })
        st.rerun()

# Footer
st.divider()
st.caption("""
⚠️ **Demo Only** - This is for educational purposes. 
This system does not provide medical advice - it only helps with booking appointments 
and can reference NHS documentation for general information.
""")
