import logging
import os
import streamlit as st
from ui import StreamlitUI
import boto3
import streamlit as st
import requests
import jwt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Constants for Cognito authentication
COGNITO_DOMAIN = "https://nova-app-pool.auth.us-east-1.amazoncognito.com"
CLIENT_ID = os.environ.get("APP_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("APP_CLIENT_SECRET", "")
APP_URI = "https://nova-video.ryannaz-mlops.com"


def main():
    """Main entry point for the Sports Marketing Video Generator application"""
    
    # Set page config
    st.set_page_config(
        page_title="Sports Marketing Video Generator",
        page_icon="🏆",
        layout="wide"
    )
    # Get ALB-injected headers
    h = st.context.headers
    oidc_data = h["x-amzn-oidc-data"]
    user_info  = jwt.decode(oidc_data, options={"verify_signature": False})

    # User is authenticated, show user info and logout button in sidebar
    with st.sidebar:
        username = user_info['username']   # if entraid user user_info["name"]
        st.success(f"Logged in as {username}")
        

    # Show the main application UI
    ui = StreamlitUI()
    ui.run()

if __name__ == "__main__":
    main()
