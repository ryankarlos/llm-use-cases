import boto3
import logging
import base64
from botocore.exceptions import ClientError
from PIL import Image
import io

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

def resize_image(image_bytes, width=1280, height=720, quality=90, format='JPEG', maintain_aspect=False):
    """
    Resize an image to the specified dimensions.
    
    Args:
        image_bytes: The image as bytes
        width: Target width of the resized image (default: 1280)
        height: Target height of the resized image (default: 720)
        quality: JPEG quality (1-100)
        format: Output format ('JPEG', 'PNG', etc.)
        maintain_aspect: If True, maintain aspect ratio; if False, force exact dimensions
        
    Returns:
        Bytes of the resized image
    """
    try:
        # Open the image from bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # Get original dimensions
        orig_width, orig_height = img.size
        
        if maintain_aspect:
            # Calculate new dimensions while maintaining aspect ratio
            if orig_width / orig_height > width / height:  # Original is wider
                new_width = width
                new_height = int(orig_height * (width / orig_width))
            else:  # Original is taller
                new_height = height
                new_width = int(orig_width * (height / orig_height))
        else:
            # Force exact dimensions
            new_width = width
            new_height = height
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # If not maintaining aspect ratio and dimensions don't match target,
        # create a new image with the exact dimensions and paste the resized image
        if not maintain_aspect and (new_width != width or new_height != height):
            exact_img = Image.new('RGB', (width, height), (0, 0, 0))
            paste_x = (width - new_width) // 2
            paste_y = (height - new_height) // 2
            exact_img.paste(resized_img, (paste_x, paste_y))
            resized_img = exact_img
        
        # Save to bytes
        output = io.BytesIO()
        resized_img.save(output, format=format, quality=quality)
        resized_bytes = output.getvalue()
        
        logger.info(f"Image resized from {orig_width}x{orig_height} to {width}x{height}")
        return resized_bytes
        
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        # Return original image if resizing fails
        return image_bytes