"""
Test cases for the main module
"""
import pytest
from unittest.mock import patch

from image_and_video.main import main

class TestMain:
    """Test cases for the main module"""
    
    @patch('image_and_video.main.StreamlitUI')
    def test_main_function(self, mock_streamlit_ui):
        """Test the main function"""
        # Create a mock instance
        mock_ui_instance = mock_streamlit_ui.return_value
        
        # Call the main function
        main()
        
        # Assertions
        mock_streamlit_ui.assert_called_once()
        mock_ui_instance.run.assert_called_once()