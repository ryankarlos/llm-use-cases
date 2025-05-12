import boto3
import os
import json
import uuid
import time
import base64
from io import BytesIO
from PIL import Image


class CanvasImageGenerator:
    """
    Class to handle image generation using Amazon Canvas through AWS Bedrock
    """
    
    def __init__(self, region_name="us-east-1"):
        """
        Initialize the Canvas image generator
        
        Args:
            region_name (str): AWS region name
        """
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=region_name
        )
        self.s3_client = boto3.client(
            "s3",
            region_name=region_name
        )
        
        # Get S3 bucket name from environment variable or use default
        self.bucket_name = os.environ.get("CANVAS_S3_BUCKET", "canvas-video-images")
        
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
    
    def generate_images(self, prompt, style="photorealistic", aspect_ratio="16:9", num_images=1):
        """
        Generate images using Amazon Canvas
        
        Args:
            prompt (str): Text description of the image to generate
            style (str): Style of the image (photorealistic, artistic, cartoon, etc.)
            aspect_ratio (str): Aspect ratio of the image (16:9, 9:16, 1:1, etc.)
            num_images (int): Number of images to generate
            
        Returns:
            list: List of paths to generated images
        """
        # Map aspect ratios to actual dimensions
        aspect_ratio_map = {
            "16:9": (1920, 1080),
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
            "4:5": (1080, 1350),
            "2:1": (2048, 1024)
        }
        
        # Get dimensions based on aspect ratio
        width, height = aspect_ratio_map.get(aspect_ratio, (1920, 1080))
        
        # Map styles to appropriate prompts
        style_prompts = {
            "photorealistic": "Create a photorealistic image with high detail and natural lighting. ",
            "artistic": "Create an artistic image with creative expression and vibrant colors. ",
            "cartoon": "Create a cartoon-style image with bold outlines and simplified forms. ",
            "abstract": "Create an abstract image with non-representational forms and patterns. ",
            "corporate": "Create a professional corporate image with clean lines and business aesthetic. ",
            "minimalist": "Create a minimalist image with simple elements and plenty of negative space. "
        }
        
        # Add style prompt to user prompt
        enhanced_prompt = style_prompts.get(style, "") + prompt
        
        # List to store paths to generated images
        image_paths = []
        
        # Generate specified number of images
        for i in range(num_images):
            try:
                # Prepare request body for Titan Image Generator
                request_body = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": enhanced_prompt,
                        "negativeText": "blurry, distorted, low quality, poor lighting, bad proportions",
                        "width": width,
                        "height": height
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "quality": "standard",
                        "cfgScale": 8.0,
                        "seed": int(time.time()) + i  # Use different seed for each image
                    }
                }
                
                # Call Bedrock to generate image
                response = self.bedrock_client.invoke_model(
                    modelId="amazon.titan-image-generator-v1",
                    body=json.dumps(request_body)
                )
                
                # Parse response
                response_body = json.loads(response["body"].read())
                
                # Extract base64 image
                base64_image = response_body["images"][0]
                
                # Convert base64 to image
                image_data = base64.b64decode(base64_image)
                image = Image.open(BytesIO(image_data))
                
                # Generate unique filename
                filename = f"canvas_image_{uuid.uuid4().hex[:8]}_{i+1}.png"
                local_path = os.path.join("temp", filename)
                
                # Save image locally
                image.save(local_path)
                
                # Upload to S3 (in production)
                # s3_key = f"images/{filename}"
                # self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
                # s3_path = f"s3://{self.bucket_name}/{s3_key}"
                
                # Add local path to list
                image_paths.append(local_path)
                
            except Exception as e:
                print(f"Error generating image {i+1}: {e}")
                # Continue with next image if one fails
                continue
        
        return image_paths
    
    def customize_image(self, image_path, text=None, text_position="bottom", text_color="#FFFFFF", 
                       logo_path=None, logo_position="bottom-right"):
        """
        Customize an image with text overlay and logo
        
        Args:
            image_path (str): Path to the image to customize
            text (str): Text to overlay on the image
            text_position (str): Position of the text (top, center, bottom)
            text_color (str): Color of the text
            logo_path (str): Path to the logo image
            logo_position (str): Position of the logo (top-left, top-right, bottom-left, bottom-right)
            
        Returns:
            str: Path to the customized image
        """
        try:
            # Open the image
            image = Image.open(image_path)
            
            # Generate unique filename for customized image
            filename = f"customized_{os.path.basename(image_path)}"
            output_path = os.path.join("temp", filename)
            
            # TODO: Implement text overlay and logo placement using PIL
            # This would involve:
            # 1. Creating a draw object
            # 2. Loading a font
            # 3. Calculating text position based on text_position
            # 4. Drawing text on the image
            # 5. If logo_path is provided, opening the logo and pasting it at the specified position
            
            # For now, just save the original image
            image.save(output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Error customizing image: {e}")
            return image_path  # Return original image path if customization fails