import boto3
import json
import os
import time
import logging
import base64
from abc import ABC, abstractmethod
from .sports_classifier import SportsImageClassifier
from .config import AWS_REGION, S3_BUCKET, POLL_INTERVAL, DEFAULT_VIDEO_CONFIG, DEFAULT_IMAGE_CONFIG

# Configure logging
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
        except Exception as e:
            logger.error(f"Error creating presigned URL: {e}")
            return None

class AIModelProcessor(ABC):
    """Abstract base class for AI model processing"""
    
    @abstractmethod
    def process(self, *args, **kwargs):
        """Process the input and return the result"""
        pass


class NovaCanvasProcessor(AIModelProcessor):
    """Processor for Nova Canvas operations with sports marketing focus"""
    
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", AWS_REGION)
        )
        self.accept = "application/json"
        self.content_type = "application/json"
        self.sports_classifier = SportsImageClassifier()
    
    def process(self, image_bytes, negative_prompt, main_prompt, mask_prompt, operation_type, config=None):
        """Process image using Amazon Nova Canvas for inpainting or outpainting with sports focus"""
        try:
            # Check if the image is sports-related
            is_sports, labels = self.sports_classifier.is_sports_image(image_bytes)
            
            if not is_sports:
                return "NOT_SPORTS_IMAGE"
                
            # Convert image bytes to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Use default config if none provided
            if config is None:
                config = DEFAULT_IMAGE_CONFIG
                
            body = {
                "taskType": operation_type,
                "imageGenerationConfig": config
            }
            
            # Add the appropriate parameters based on operation type
            if operation_type == "INPAINTING":
                body["inPaintingParams"] = {
                    "text": main_prompt,
                    "maskPrompt": mask_prompt,
                    "negativeText": negative_prompt,
                    "image": image_base64,
                }
            elif operation_type == "OUTPAINTING":
                body["outPaintingParams"] = {
                    "text": main_prompt,
                    "maskPrompt": mask_prompt,
                    "negativeText": negative_prompt,
                    "image": image_base64,
                }

            response = self.bedrock_runtime.invoke_model(
                modelId="amazon.nova-canvas-v1:0",
                body=json.dumps(body),
                accept=self.accept, contentType=self.content_type
            )
            response_body = json.loads(response.get("body").read())
            base64_image = response_body.get("images")[0]
            base64_bytes = base64_image.encode('ascii')
            image_bytes = base64.b64decode(base64_bytes)

            return image_bytes

        except Exception as e:
            logger.error(f"Error in Nova Canvas processing: {str(e)}")
            return None


class NovaReelProcessor(AIModelProcessor):
    """Processor for Nova Reel operations with sports marketing focus"""
    
    def __init__(self, s3_bucket=S3_BUCKET, poll_interval=POLL_INTERVAL):
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", AWS_REGION)
        )
        self.s3_bucket = s3_bucket
        self.poll_interval = poll_interval
        self.s3_service = S3Service()
        self.sports_classifier = SportsImageClassifier()
        
        # System prompt for sports marketing
        self.system_prompt = "You are SportVision AI, a premier sports marketing agency specializing in creating dynamic sports content."
    
    def process(self, image_bytes, prompt, status_callback=None, video_config=None):
        """Generate sports marketing video using Amazon Nova Reel"""
        try:
            # Check if the image is sports-related
            is_sports, labels = self.sports_classifier.is_sports_image(image_bytes)
            
            if not is_sports:
                if status_callback:
                    status_callback("error", "The uploaded image is not sports-related. Please upload an image related to sports for creating a sports marketing video.")
                return "NOT_SPORTS_IMAGE"
                
            # Convert image bytes to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Enhance the prompt with sports marketing context
            enhanced_prompt = f"{self.system_prompt} {prompt}"
            
            # Use default config if none provided
            if video_config is None:
                video_config = DEFAULT_VIDEO_CONFIG

            model_input = {
                "taskType": "TEXT_VIDEO",
                "textToVideoParams": {
                    "text": enhanced_prompt,
                    "images": [
                        {
                            "format": "png",
                            "source": {
                                "bytes": image_base64
                            }
                        }
                    ]
                },
                "videoGenerationConfig": video_config,
            }

            # Start the asynchronous video generation job
            invocation = self.bedrock_runtime.start_async_invoke(
                modelId="amazon.nova-reel-v1:1",
                modelInput=model_input,
                outputDataConfig={
                    "s3OutputDataConfig": {
                        "s3Uri": f"s3://{self.s3_bucket}"
                    }
                },
            )
            invocation_arn = invocation["invocationArn"]
            
            # Update status
            if status_callback:
                status_callback("start", "Sports marketing video generation started. Checking status...")
            
            # Check status until completed or failed
            status = "InProgress"
            while status == "InProgress":
                invocation = self.bedrock_runtime.get_async_invoke(
                    invocationArn=invocation_arn
                )
                status = invocation["status"]
                
                if status == "Completed":
                    # Extract S3 bucket information
                    bucket_uri = invocation["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]
                    bucket_name = bucket_uri.replace("s3://", "").split("/")[0]
                    object_key = "output.mp4"  # Default output filename
                    
                    # Generate a presigned URL for the video
                    presigned_url = self.s3_service.create_presigned_url(bucket_name, object_key)
                    
                    if status_callback:
                        if presigned_url:
                            status_callback("complete", presigned_url)
                        else:
                            status_callback("warning", f"Sports marketing video is available at: {bucket_uri}/output.mp4, but couldn't generate a presigned URL.")
                    
                    return presigned_url
                    
                elif status == "Failed":
                    failure_message = invocation["failureMessage"]
                    if status_callback:
                        status_callback("error", f"Job failed. Failure message: {failure_message}")
                    return None
                    
                else:  # Still in progress
                    start_time = invocation["submitTime"]
                    if status_callback:
                        status_callback("progress", f"Video generation in progress. Started at: {start_time}. Checking again in {self.poll_interval} seconds...")
                    time.sleep(self.poll_interval)

        except Exception as e:
            logger.error(f"Error in Nova Reel processing: {str(e)}")
            if status_callback:
                status_callback("error", f"Error in sports marketing video generation: {str(e)}")
            return None