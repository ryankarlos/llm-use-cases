import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the app directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from canvas import CanvasImageGenerator


class TestCanvasImageGenerator(unittest.TestCase):
    """Test cases for the CanvasImageGenerator class"""
    
    @patch('boto3.client')
    def setUp(self, mock_boto3_client):
        """Set up test fixtures"""
        self.mock_bedrock_client = MagicMock()
        self.mock_s3_client = MagicMock()
        
        # Configure the mock boto3.client to return our mock clients
        mock_boto3_client.side_effect = lambda service, region_name=None: {
            'bedrock-runtime': self.mock_bedrock_client,
            's3': self.mock_s3_client
        }[service]
        
        # Create an instance of CanvasImageGenerator with the mocked clients
        self.canvas_generator = CanvasImageGenerator(region_name='us-east-1')
    
    @patch('PIL.Image.open')
    @patch('PIL.Image.save')
    @patch('os.makedirs')
    def test_generate_images(self, mock_makedirs, mock_save, mock_open):
        """Test the generate_images method"""
        # Mock the response from Bedrock
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = '{"images": ["base64_encoded_image"]}'
        self.mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Mock the PIL Image
        mock_image = MagicMock()
        mock_open.return_value = mock_image
        
        # Call the method
        result = self.canvas_generator.generate_images(
            prompt="Test prompt",
            style="photorealistic",
            aspect_ratio="16:9",
            num_images=1
        )
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].startswith('temp/canvas_image_'))
        self.assertTrue(result[0].endswith('.png'))
        
        # Verify that the Bedrock client was called with the correct parameters
        self.mock_bedrock_client.invoke_model.assert_called_once()
        call_args = self.mock_bedrock_client.invoke_model.call_args[1]
        self.assertEqual(call_args['modelId'], 'amazon.titan-image-generator-v1')
        
        # Verify that the request body contains the expected parameters
        request_body = call_args['body']
        self.assertIn('Create a photorealistic image with high detail and natural lighting. Test prompt', request_body)
        self.assertIn('"width": 1920', request_body)
        self.assertIn('"height": 1080', request_body)


if __name__ == '__main__':
    unittest.main()