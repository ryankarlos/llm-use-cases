import streamlit as st
import requests
import base64

# Constants for Cognito authentication
COGNITO_DOMAIN = "https://nova-app-pool.auth.us-east-1.amazoncognito.com"
CLIENT_ID = ""
CLIENT_SECRET = ""
APP_URI = "https://nova-video.ryannaz-mlops.com"

def initialise_st_state_vars():
    """Initialize Streamlit state variables for authentication"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

def get_auth_code():
    """Get authorization code from query parameters"""
    try:
        return st.query_params.get("code")
    except:
        return None

def get_user_tokens(auth_code):
    """Exchange authorization code for access and ID tokens"""
    token_url = f"{COGNITO_DOMAIN}/oauth2/token"
    client_secret_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_secret_encoded = str(
        base64.b64encode(client_secret_string.encode("utf-8")), "utf-8"
    )
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {client_secret_encoded}",
    }
    body = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": auth_code,
    }

    token_response = requests.post(token_url, headers=headers, data=body)
    try:
        return token_response.json()["access_token"], token_response.json()["id_token"]
    except:
        return "", ""

def auth_flow():
    """
    Handle authentication flow and redirect to login if needed
    
    Returns:
        bool: True if authenticated, False otherwise
    """
    # Initialize state variables
    initialise_st_state_vars()
    
    # Generate login link
    login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=aws.cognito.signin.user.admin+email+openid&redirect_uri={APP_URI}"
    
    # Check for auth code in URL (after redirect from Cognito)
    auth_code = get_auth_code()
    
    # If we have an auth code but haven't processed it yet
    if auth_code and not st.session_state["authenticated"]:
        # Process the authentication
        access_token, id_token = get_user_tokens(auth_code)
        if access_token:
            st.session_state["authenticated"] = True
            st.session_state["access_token"] = access_token
            # Clear query parameters
            st.query_params.clear()
            # Force a rerun to update the UI
            st.rerun()
    
    # If not authenticated, redirect to login
    if not st.session_state["authenticated"]:
        st.markdown(f"""
            <meta http-equiv="refresh" content="0;url={login_link}">
            <p>If you are not redirected automatically, click <a href="{login_link}">here</a> to log in.</p>
            """, unsafe_allow_html=True)
        return False
    
    # User is authenticated
    return True
