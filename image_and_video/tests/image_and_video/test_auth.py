from image_and_video.auth import check_authentication
from streamlit_cognito_auth import CognitoAuthenticator
from unittest.mock import patch
from unittest.mock import patch, MagicMock
import os
import streamlit as st
import sys
import unittest

class TestAuth(unittest.TestCase):

    def test_check_authentication_exception_handling(self):
        """
        Test that check_authentication handles exceptions and falls back to demo mode
        when there's an error with authentication.
        """
        with patch('streamlit_cognito_auth.CognitoAuthenticator') as mock_authenticator:
            mock_authenticator.side_effect = Exception("Test exception")

            with patch('streamlit.sidebar.error') as mock_error, \
                 patch('streamlit.sidebar.warning') as mock_warning:

                result = check_authentication()

                mock_error.assert_called_once_with("Authentication error: Test exception")
                mock_warning.assert_called_once_with("⚠️ Falling back to demo mode")
                assert result == True

    def test_check_authentication_returns_false_when_not_logged_in(self):
        """
        Test that check_authentication() returns False when the user is not logged in.

        This test verifies that when the CognitoAuthenticator.login() method returns False,
        indicating the user is not authenticated, the check_authentication() function
        correctly returns False.
        """
        # Mock the CognitoAuthenticator
        class MockAuthenticator:
            def login(self):
                return False

            def get_username(self):
                return "test_user"

        # Patch the CognitoAuthenticator import
        sys.modules['streamlit_cognito_auth'] = type('MockModule', (), {'CognitoAuthenticator': MockAuthenticator})

        # Set required environment variables
        os.environ["COGNITO_USER_POOL_ID"] = "test_pool_id"
        os.environ["COGNITO_APP_CLIENT_ID"] = "test_client_id"
        os.environ["COGNITO_DOMAIN"] = "test_domain"

        # Import the function under test

        # Call the function and assert the result
        result = check_authentication()
        assert result == False

        # Clean up
        del sys.modules['streamlit_cognito_auth']
        del os.environ["COGNITO_USER_POOL_ID"]
        del os.environ["COGNITO_APP_CLIENT_ID"]
        del os.environ["COGNITO_DOMAIN"]

    def test_check_authentication_successful_login(self):
        """
        Test case for successful authentication.

        This test verifies that the check_authentication function returns True
        when the user is successfully logged in via Cognito authentication.
        It mocks the CognitoAuthenticator to simulate a successful login
        and checks if the function returns True and displays the correct
        success message in the Streamlit sidebar.
        """
        with patch('image_and_video.auth.CognitoAuthenticator') as MockAuthenticator:
            mock_authenticator = MockAuthenticator.return_value
            mock_authenticator.login.return_value = True
            mock_authenticator.get_username.return_value = "test_user"

            with patch.object(st.sidebar, 'success') as mock_success:
                result = check_authentication()

                self.assertTrue(result)
                mock_success.assert_called_once_with("Logged in as: test_user")
