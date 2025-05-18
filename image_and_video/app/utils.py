import boto3
import logging
import base64
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S3Service:
    """Service for S3 operations"""
    
    @staticmethod
    def create_presigned_url(bucket_name, object_name, expiration=3600):
        """Generate a presigned URL to share an S3 object"""
        s3_client = boto3.client('s3')
        try:
            response = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_name},
                ExpiresIn=expiration,
            )
            return response
        except ClientError as e:
            logger.error(f"Error creating presigned URL: {e}")
            return None

def encode_image(image_bytes):
    """Convert image bytes to base64 encoding"""
    return base64.b64encode(image_bytes).decode('utf-8')

def decode_image(base64_image):
    """Convert base64 image to bytes"""
    base64_bytes = base64_image.encode('ascii')
    return base64.b64decode(base64_bytes)