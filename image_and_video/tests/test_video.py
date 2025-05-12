import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the app directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from video import VideoConverter


class TestVideoConverter(unittest.TestCase):
    """Test cases for the VideoConverter class"""
    
    @patch('boto3.client')
    def setUp(self, mock_boto3_client):
        """Set up test fixtures"""
        self.mock_mediaconvert_client = MagicMock()
        self.mock_s3_client = MagicMock()
        
        # Configure the mock boto3.client to return our mock clients
        mock_boto3_client.side_effect = lambda service, region_name=None: {
            'mediaconvert': self.mock_mediaconvert_client,
            's3': self.mock_s3_client
        }[service]
        
        # Create an instance of VideoConverter with the mocked clients
        self.video_converter = VideoConverter(region_name='us-east-1')
    
    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_create_video_with_ffmpeg(self, mock_makedirs, mock_subprocess_run):
        """Test the _create_video_with_ffmpeg method"""
        # Mock the subprocess.run to return successfully
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Test data
        image_path = 'test_image.png'
        output_path = 'test_output.mp4'
        settings = {
            'duration': 15,
            'resolution': '1080p',
            'format': 'mp4',
            'transition_effects': 'fade',
            'background_music': None
        }
        
        # Call the method
        result = self.video_converter._create_video_with_ffmpeg(image_path, output_path, settings)
        
        # Assertions
        self.assertEqual(result, output_path)
        mock_subprocess_run.assert_called_once()
        
        # Verify that the FFmpeg command contains the expected parameters
        ffmpeg_command = mock_subprocess_run.call_args[0][0]
        self.assertEqual(ffmpeg_command[0], 'ffmpeg')
        self.assertEqual(ffmpeg_command[2], '1')  # Loop the image
        self.assertEqual(ffmpeg_command[4], image_path)  # Input image
        self.assertEqual(ffmpeg_command[6], 'libx264')  # Video codec
        self.assertEqual(ffmpeg_command[8], '15')  # Duration
        self.assertIn('1920:1080', ffmpeg_command[12])  # Resolution
    
    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_create_video(self, mock_makedirs, mock_subprocess_run):
        """Test the create_video method"""
        # Mock the subprocess.run to return successfully
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Test data
        image_path = 'test_image.png'
        settings = {
            'duration': 15,
            'resolution': '1080p',
            'format': 'mp4',
            'transition_effects': 'fade',
            'background_music': None
        }
        
        # Call the method
        result = self.video_converter.create_video(image_path, settings)
        
        # Assertions
        self.assertTrue(result.startswith('temp/videos/canvas_video_'))
        self.assertTrue(result.endswith('.mp4'))
        mock_subprocess_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()