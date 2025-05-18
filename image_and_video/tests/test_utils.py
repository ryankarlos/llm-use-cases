"""
Test cases for the utils module
"""
import pytest
from unittest.mock import MagicMock
import base64

from image_and_video.utils import S3Service, encode_image, decode_image

class TestS3Service:
    """Test cases for the S3Service class"""
    
    @pytest.fixture
    def s3_service(self, mock_boto3_client, mock_s3_client):
        """Set up test fixtures"""
        # Configure the mock boto3.client to return our mock clients
        mock_boto3_client.side_effect = lambda service, region_name=None: {
            's3': mock_s3_client
        }[service]
        
        return S3Service()
    
    def test_create_presigned_url_success(self, s3_service, mock_s3_client):
        """Test creating a presigned URL successfully"""
        # Mock the response from S3
        mock_s3_client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-object?signature=abc123"
        
        # Test data
        bucket_name = "test-bucket"
        object_name = "test-object"
        expiration = 7200
        
        # Call the method
        result = S3Service.create_presigned_url(bucket_name, object_name, expiration)
        
        # Assertions
        assert result == "https://test-bucket.s3.amazonaws.com/test-object?signature=abc123"
        
        # Verify that S3 client was called with the correct parameters
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration,
        )

class TestImageUtils:
    """Test cases for image utility functions"""
    
    def test_encode_image(self):
        """Test encoding image bytes to base64"""
        # Test data
        test_bytes = b'test image data'
        expected_base64 = base64.b64encode(test_bytes).decode('utf-8')
        
        # Call the function
        result = encode_image(test_bytes)
        
        # Assertions
        assert result == expected_base64
    
    def test_decode_image(self):
        """Test decoding base64 to image bytes"""
        # Test data
        test_bytes = b'test image data'
        base64_str = base64.b64encode(test_bytes).decode('utf-8')
        
        # Call the function
        result = decode_image(base64_str)
        
        # Assertions
        assert result == test_bytes