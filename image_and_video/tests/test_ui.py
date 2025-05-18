"""
Test cases for the UI module
"""
import pytest
from unittest.mock import patch, MagicMock
import io
from PIL import Image

from image_and_video.ui import StreamlitUI

class TestStreamlitUI:
    """Test cases for the StreamlitUI class"""
    
    @pytest.fixture
    def ui(self):
        """Set up test fixtures"""
        # Mock the NovaCanvasProcessor and NovaReelProcessor
        with patch('image_and_video.ui.NovaCanvasProcessor') as mock_canvas, \
             patch('image_and_video.ui.NovaReelProcessor') as mock_reel:
            # Create mock instances
            mock_canvas_instance = mock_canvas.return_value
            mock_reel_instance = mock_reel.return_value
            
            # Create an instance of StreamlitUI
            ui = StreamlitUI()
            
            # Return the UI instance and mocks for testing
            return {
                'ui': ui,
                'mock_canvas': mock_canvas_instance,
                'mock_reel': mock_reel_instance
            }
    
    def test_init(self, ui):
        """Test initialization of StreamlitUI"""
        # Assertions
        assert ui['ui'].nova_canvas == ui['mock_canvas']
        assert ui['ui'].nova_reel == ui['mock_reel']
        assert ui['ui'].processed_image is None
        assert ui['ui'].original_image is None
        assert ui['ui'].current_image is None
        assert ui['ui'].sports_marketing_videos is not None
        assert ui['ui'].sports_prompt_templates is not None
    
    @patch('streamlit.empty')
    def test_status_callback_start(self, mock_empty):
        """Test status callback with start status"""
        # Create a mock placeholder
        mock_placeholder = mock_empty.return_value
        
        # Create UI instance
        ui = StreamlitUI()
        
        # Call the method
        ui.status_callback("start", "Test message")
        
        # Assertions
        mock_empty.assert_called_once()
        mock_placeholder.info.assert_called_once_with("Test message")
    
    @patch('streamlit.empty')
    def test_status_callback_progress(self, mock_empty):
        """Test status callback with progress status"""
        # Create a mock placeholder
        mock_placeholder = mock_empty.return_value
        
        # Create UI instance
        ui = StreamlitUI()
        
        # Call the method
        ui.status_callback("progress", "Test progress message")
        
        # Assertions
        mock_empty.assert_called_once()
        mock_placeholder.info.assert_called_once_with("Test progress message")
    
    @patch('streamlit.empty')
    @patch('streamlit.video')
    @patch('streamlit.markdown')
    def test_status_callback_complete(self, mock_markdown, mock_video, mock_empty):
        """Test status callback with complete status"""
        # Create a mock placeholder
        mock_placeholder = mock_empty.return_value
        
        # Create UI instance
        ui = StreamlitUI()
        
        # Call the method
        ui.status_callback("complete", "https://test-url.com/video.mp4")
        
        # Assertions
        mock_empty.assert_called_once()
        mock_placeholder.success.assert_called_once_with("✅ Sports marketing video generated successfully!")
        mock_video.assert_called_once_with("https://test-url.com/video.mp4")
        mock_markdown.assert_called_once_with("[Download Sports Marketing Video](https://test-url.com/video.mp4)")
    
    @patch('streamlit.empty')
    def test_status_callback_warning(self, mock_empty):
        """Test status callback with warning status"""
        # Create a mock placeholder
        mock_placeholder = mock_empty.return_value
        
        # Create UI instance
        ui = StreamlitUI()
        
        # Call the method
        ui.status_callback("warning", "Test warning message")
        
        # Assertions
        mock_empty.assert_called_once()
        mock_placeholder.warning.assert_called_once_with("Test warning message")
    
    @patch('streamlit.empty')
    def test_status_callback_error(self, mock_empty):
        """Test status callback with error status"""
        # Create a mock placeholder
        mock_placeholder = mock_empty.return_value
        
        # Create UI instance
        ui = StreamlitUI()
        
        # Call the method
        ui.status_callback("error", "Test error message")
        
        # Assertions
        mock_empty.assert_called_once()
        mock_placeholder.error.assert_called_once_with("Test error message")
    
    @patch('streamlit.set_page_config')
    @patch('streamlit.markdown')
    @patch('streamlit.title')
    @patch('streamlit.sidebar')
    @patch('streamlit.file_uploader')
    def test_run_no_upload(self, mock_file_uploader, mock_sidebar, mock_title, mock_markdown, mock_set_page_config):
        """Test run method with no file uploaded"""
        # Mock the file uploader to return None (no file uploaded)
        mock_file_uploader.return_value = None
        
        # Create UI instance
        ui = StreamlitUI()
        
        # Call the method
        ui.run()
        
        # Assertions
        mock_set_page_config.assert_called_once()
        mock_title.assert_called_once()
        mock_file_uploader.assert_called_once()
        
    @patch('streamlit.set_page_config')
    @patch('streamlit.markdown')
    @patch('streamlit.title')
    @patch('streamlit.sidebar')
    @patch('streamlit.file_uploader')
    @patch('streamlit.columns')
    @patch('streamlit.image')
    @patch('streamlit.error')
    def test_run_with_non_sports_image(self, mock_error, mock_image, mock_columns, 
                                      mock_file_uploader, mock_sidebar, mock_title, 
                                      mock_markdown, mock_set_page_config):
        """Test run method with a non-sports image uploaded"""
        # Create a mock image
        mock_img = MagicMock(spec=Image.Image)
        mock_img.format = "PNG"
        
        # Mock the file uploader to return a file
        mock_file = MagicMock()
        mock_file_uploader.return_value = mock_file
        
        # Mock Image.open to return our mock image
        with patch('PIL.Image.open', return_value=mock_img):
            # Mock the sports classifier to return False
            with patch('image_and_video.ui.SportsImageClassifier') as mock_classifier_class:
                mock_classifier = mock_classifier_class.return_value
                mock_classifier.is_sports_image.return_value = (False, [])
                
                # Create UI instance
                ui = StreamlitUI()
                
                # Call the method
                ui.run()
                
                # Assertions
                mock_set_page_config.assert_called_once()
                mock_title.assert_called_once()
                mock_file_uploader.assert_called_once()
                mock_classifier.is_sports_image.assert_called_once()
                mock_error.assert_called_once()
                assert "sports image" in mock_error.call_args[0][0]