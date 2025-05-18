"""Authentication module for the Sports Marketing Video Generator"""
import streamlit as st
from .config import COGNITO_ENABLED, COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID, COGNITO_DOMAIN

def check_authentication():
    """Check if user is authenticated or if authentication is disabled"""
    if not COGNITO_ENABLED:
        # Demo mode - no authentication required
        st.sidebar.warning("⚠️ Running in demo mode (no authentication)")
        return True
    
    try:
        # Import here to avoid errors if package is not installed
        from streamlit_cognito_auth import CognitoAuthenticator
        
        # Initialize Cognito authenticator
        authenticator = CognitoAuthenticator(
            cognito_user_pool_id=COGNITO_USER_POOL_ID,
            cognito_app_client_id=COGNITO_APP_CLIENT_ID,
            cognito_domain=COGNITO_DOMAIN
        )
        
        # Check if user is authenticated
        is_logged_in = authenticator.login()
        if is_logged_in:
            st.sidebar.success(f"Logged in as: {authenticator.get_username()}")
            return True
        return False
    
    except Exception as e:
        # Fall back to demo mode if there's an error with authentication
        st.sidebar.error(f"Authentication error: {str(e)}")
        st.sidebar.warning("⚠️ Falling back to demo mode")
        return True