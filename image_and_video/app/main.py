import streamlit as st
import boto3
import base64
import json
import os
import time
from PIL import Image
import io
import requests
import logging
import numpy as np
from botocore.exceptions import ClientError
from abc import ABC, abstractmethod

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


class AIModelProcessor(ABC):
    """Abstract base class for AI model processing"""
    
    @abstractmethod
    def process(self, *args, **kwargs):
        """Process the input and return the result"""
        pass


class SportsImageClassifier:
    """Classifier to determine if an image is sports-related"""
    
    def __init__(self):
        # Sports-related keywords for image analysis
        self.sports_keywords = [
            "sports", "athlete", "game", "match", "competition", "team", 
            "stadium", "field", "court", "ball", "player", "race", "tournament",
            "basketball", "football", "soccer", "baseball", "tennis", "golf",
            "hockey", "rugby", "volleyball", "swimming", "track", "fitness",
            "running", "cycling", "boxing", "martial arts", "olympics"
        ]
        
    def is_sports_image(self, image_bytes):
        """Determine if the image is sports-related using Amazon Rekognition"""
        try:
            rekognition = boto3.client('rekognition')
            response = rekognition.detect_labels(Image={'Bytes': image_bytes})
            
            # Extract labels from the response
            labels = [label['Name'].lower() for label in response['Labels']]
            
            # Check if any sports keywords are in the labels
            for keyword in self.sports_keywords:
                if keyword.lower() in labels:
                    return True, labels
                    
            # Check for confidence scores on sports-related activities
            for label in response['Labels']:
                if any(keyword.lower() in label['Name'].lower() for keyword in self.sports_keywords):
                    if label['Confidence'] > 70:
                        return True, labels
            
            return False, labels
            
        except Exception as e:
            logger.error(f"Error in sports image classification: {str(e)}")
            return False, []


class NovaCanvasProcessor(AIModelProcessor):
    """Processor for Nova Canvas operations with sports marketing focus"""
    
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1")
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
            
            # Enhance the prompt with sports marketing context
            enhanced_prompt = self.enhance_prompt_with_sports_context(main_prompt, labels)
            
            # Use default config if none provided
            if config is None:
                config = {
                    "numberOfImages": 1,
                    "quality": "standard",
                    "height": 1280,
                    "width": 720,
                    "cfgScale": 8
                }
                
            body = {
                "taskType": operation_type,
                "imageGenerationConfig": config
            }
            
            # Add the appropriate parameters based on operation type
            if operation_type == "INPAINTING":
                body["inPaintingParams"] = {
                    "text": enhanced_prompt,
                    "maskPrompt": mask_prompt,
                    "negativeText": negative_prompt,
                    "image": image_base64,
                }
            elif operation_type == "OUTPAINTING":
                body["outPaintingParams"] = {
                    "text": enhanced_prompt,
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
    
    def __init__(self, s3_bucket="nova-reel-videos-demo", poll_interval=30):
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        self.s3_bucket = s3_bucket
        self.poll_interval = poll_interval
        self.s3_service = S3Service()
        self.sports_classifier = SportsImageClassifier()
    
    
    def enhance_prompt_with_sports_context(self, prompt, labels):
        """Enhance the prompt with sports-specific marketing video context"""
        # Determine which sport context to use based on detected labels
        sport_template = "You are SportVision AI, a premier sports marketing agency specializing in creating dynamic sports content. " \
        "As an expert in sports advertising, your role is to generate compelling, authentic sports marketing materials that resonate with fans and athletes. " \
        "Focus on capturing the energy, emotion, and competitive spirit of sports while maintaining brand visibility and marketing objectives. " \
        "Incorporate sports-specific terminology, athlete movements, and fan experiences in your content. Always prioritize action, motion, and emotional connection in sports contexts"

        # Enhance the prompt with sports marketing context
        enhanced_prompt = f"{sport_template}. {prompt}. Include dynamic camera movements, brand visibility, and emotional connection. Show the excitement and passion of sports. Create a compelling advertisement that inspires viewers to engage with the brand."
        return enhanced_prompt
    
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
            enhanced_prompt = self.enhance_prompt_with_sports_context(prompt, labels)
            
            # Use default config if none provided
            if video_config is None:
                video_config = {
                    "durationSeconds": 6,
                    "fps": 24,
                    "dimension": "1280x720",
                    "seed": 0
                }

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
                        status_callback("progress", f"Sports marketing video generation in progress. Started at: {start_time}. Checking again in {self.poll_interval} seconds...")
                    time.sleep(self.poll_interval)

        except Exception as e:
            logger.error(f"Error in Nova Reel processing: {str(e)}")
            if status_callback:
                status_callback("error", f"Error in sports marketing video generation: {str(e)}")
            return None


class StreamlitUI:
    """UI handler for Streamlit for Sports Marketing Video Generator"""
    
    def __init__(self):
        self.nova_canvas = NovaCanvasProcessor()
        self.nova_reel = NovaReelProcessor()
        
    def status_callback(self, status_type, message):
        """Handle status updates"""
        if not hasattr(self, 'status_placeholder'):
            self.status_placeholder = st.empty()
            
        if status_type == "start" or status_type == "progress":
            self.status_placeholder.info(message)
        elif status_type == "complete":
            self.status_placeholder.success("Sports marketing video generated successfully!")
            st.video(message)  # message contains the presigned URL
            st.markdown(f"[Download Sports Marketing Video]({message})")
        elif status_type == "warning":
            self.status_placeholder.warning(message)
        elif status_type == "error":
            self.status_placeholder.error(message)
    
    def run(self):
        """Run the Sports Marketing Video Generator Streamlit UI"""
        # Set page config for a wider layout
        st.set_page_config(page_title="Sports Marketing Video Generator", layout="wide")        
        # Header with sports theme
        st.title("🏆 Sports Marketing Video Generator 🏆")
        st.markdown("""
        Transform sports images into compelling marketing videos for your brand.
        Upload a sports-related image, choose your marketing goal, and let AI create a dynamic sports advertisement!
        """)
        
        # Sidebar for options
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Marketing goal selection
            st.subheader("Marketing Goal")
            marketing_goal = st.selectbox(
                "Select your marketing objective:",
                list(self.sports_prompt_templates.keys()),
                format_func=lambda x: x.replace('_', ' ').title()
            )
            
            # Video duration
            st.subheader("Video Settings")
            duration = st.slider("Video Duration (seconds)", min_value=3, max_value=10, value=6, step=1)
            
            # Video quality
            quality_options = {
                "Standard (720p)": "1280x720",
                "High (1080p)": "1920x1080"
            }
            quality = st.selectbox("Video Quality", options=list(quality_options.keys()))
            
            # Advanced options
            with st.expander("Advanced Options"):
                fps = st.slider("Frames Per Second", min_value=24, max_value=30, value=24)
                seed = st.number_input("Random Seed (0 for random)", min_value=0, value=0)
                
            # Create video config
            video_config = {
                "durationSeconds": duration,
                "fps": fps,
                "dimension": quality_options[quality],
                "seed": seed
            }
        
        # Main content area
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.header("1️⃣ Upload Sports Image")
            uploaded_file = st.file_uploader("Choose a sports-related image...", type=["jpg", "jpeg", "png"])
            
            if uploaded_file is not None:
                # Display the uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_column_width=True)
                
                # Convert to bytes for processing
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format=image.format if image.format else 'PNG')
                image_bytes = img_byte_arr.getvalue()
                
                # Check if image is sports-related
                sports_classifier = SportsImageClassifier()
                is_sports, labels = sports_classifier.is_sports_image(image_bytes)
                
                if not is_sports:
                    st.error("⚠️ The uploaded image does not appear to be sports-related. Please upload an image related to sports for creating a sports marketing video.")
                else:
                    st.success("✅ Sports image detected! Ready to generate marketing video.")
                    # Show detected sports elements
                    with st.expander("View detected sports elements"):
                        st.write(", ".join([label for label in labels if label in " ".join(sports_classifier.sports_keywords)]))
        
        with col2:
            st.header("2️⃣ Customize Your Marketing Video")
            
            # Use template as starting point
            base_prompt = self.sports_prompt_templates[marketing_goal]
            
            # Allow customization
            custom_prompt = st.text_area(
                "Customize your marketing message:",
                value=base_prompt,
                height=100
            )
            
            # Brand information
            brand_name = st.text_input("Brand Name (optional)")
            if brand_name:
                custom_prompt += f" for {brand_name}"
                
            # Target audience
            target_audience = st.selectbox(
                "Target Audience",
                ["General Sports Fans", "Young Athletes", "Professional Athletes", "Fitness Enthusiasts", "Team Supporters"]
            )
            custom_prompt += f" targeting {target_audience.lower()}"
            
            # Call to action
            cta_options = {
                "Shop Now": "with a clear 'Shop Now' call to action",
                "Learn More": "with an inviting 'Learn More' call to action",
                "Join Today": "with an engaging 'Join Today' call to action",
                "Sign Up": "with a compelling 'Sign Up' call to action",
                "Visit Website": "with a direct 'Visit Website' call to action"
            }
            cta = st.selectbox("Call to Action", list(cta_options.keys()))
            custom_prompt += f" {cta_options[cta]}"
            
            # Generate button
            generate_button = st.button("🎬 Generate Sports Marketing Video")
            
            if generate_button and uploaded_file is not None:
                if not is_sports:
                    st.error("Cannot generate video. Please upload a sports-related image.")
                else:
                    # Process with Nova Reel
                    result = self.nova_reel.process(
                        image_bytes=image_bytes,
                        prompt=custom_prompt,
                        status_callback=self.status_callback,
                        video_config=video_config
                    )
                    
                    if result == "NOT_SPORTS_IMAGE":
                        st.error("The image was not recognized as sports-related. Please upload a different image.")
        
        # Footer
        st.markdown("---")
        st.markdown("Powered by AWS Bedrock Nova Reel and Nova Canvas")t_page_config(
            page_title="AI Image to Video Generator",
            page_icon="🎬",
            layout="wide"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #FF9900;
            text-align: center;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #232F3E;
            margin-bottom: 1rem;
        }
        .stButton>button {
            background-color: #FF9900;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #FF8000;
        }
        .section-divider {
            margin-top: 2rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid #ddd;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("<h1 class='main-header'>AI Image to Video Generator</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Transform your images into stunning videos with AWS Bedrock AI</p>", unsafe_allow_html=True)
        
        # Create tabs for better organization
        tab1, tab2 = st.tabs(["Generate", "About"])
        
        with tab1:
            # File uploader
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("<h3 class='sub-header'>Upload Image</h3>", unsafe_allow_html=True)
                uploaded_file = st.file_uploader("", type=['png', 'jpg', 'jpeg'])
            
            if uploaded_file:
                # Display uploaded image
                with col2:
                    image = Image.open(uploaded_file)
                    
                    # Check if image needs resizing
                    if image.size != (1280, 720):
                        st.info(f"Resizing image from {image.size} to 1280x720 for compatibility")
                        image = image.resize((1280, 720), Image.LANCZOS)
                    
                    st.image(image, caption="Uploaded Image", use_column_width=True)
                
                st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
                
                # Pre-processing options
                st.markdown("<h3 class='sub-header'>Image Processing Options</h3>", unsafe_allow_html=True)
                
                preprocessing = st.selectbox(
                    "Select pre-processing (optional)",
                    ["NONE", "INPAINTING", "OUTPAINTING"]
                )
                
                if preprocessing != "NONE":
                    # Create columns for prompts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        main_prompt = st.text_area(
                            f"Enter {preprocessing.lower()} prompt:",
                            help=f"Describe what you want to {preprocessing.lower()} in the image",
                            placeholder="E.g., a beautiful sunset over mountains"
                        )
                        
                        negative_prompt = st.text_area(
                            "Enter negative prompt:",
                            help="Describe what you want to avoid in the generated image",
                            placeholder="E.g., blur, distortion, bad quality"
                        )
                    
                    with col2:
                        mask_prompt = st.text_area(
                            f"Enter mask prompt:",
                            help=f"Describe what you want to mask in the image",
                            placeholder="E.g., the sky"
                        )
                    
                    # Nova Canvas advanced parameters
                    with st.expander("Advanced Canvas Parameters"):
                        canvas_quality = st.selectbox(
                            "Quality",
                            ["standard", "premium"]
                        )
                        
                        canvas_cfg_scale = st.slider(
                            "CFG Scale",
                            min_value=1,
                            max_value=15,
                            value=8,
                            help="Controls how closely the image follows the prompt"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            canvas_width = st.select_slider(
                                "Width",
                                options=[512, 640, 720, 1024, 1280, 1536],
                                value=1280
                            )
                        with col2:
                            canvas_height = st.select_slider(
                                "Height",
                                options=[512, 640, 720, 1024, 1280, 1536],
                                value=720
                            )
                
                st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
                
                # Video generation options
                st.markdown("<h3 class='sub-header'>Video Generation Options</h3>", unsafe_allow_html=True)
                
                video_prompt = st.text_area(
                    "Enter video generation prompt:",
                    help="Describe what you want to generate in the video",
                    placeholder="E.g., a camera flying through a beautiful mountain landscape with clouds moving"
                )
                
                # Nova Reel advanced parameters
                with st.expander("Advanced Video Parameters"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        video_duration = st.slider(
                            "Duration (seconds)",
                            min_value=2,
                            max_value=10,
                            value=6,
                            step=1
                        )
                        
                        video_fps = st.slider(
                            "Frames Per Second",
                            min_value=15,
                            max_value=30,
                            value=24,
                            step=1
                        )
                    
                    with col2:
                        video_dimension = st.selectbox(
                            "Video Dimension",
                            ["1280x720", "1920x1080"],
                            index=0
                        )
                        
                        video_seed = st.number_input(
                            "Random Seed",
                            min_value=0,
                            max_value=10000,
                            value=0,
                            help="Set to 0 for random results, or specify a value for reproducible results"
                        )
                
                # Generate button
                if st.button("🚀 Generate Video", use_container_width=True):
                    with st.spinner("Processing..."):
                        try:
                            # Convert image to bytes (image is already resized at this point)
                            img_byte_arr = io.BytesIO()
                            image.save(img_byte_arr, format='PNG')
                            image_bytes = img_byte_arr.getvalue()
                            
                            # Apply pre-processing if selected
                            if preprocessing != "NONE":
                                st.info(f"Applying {preprocessing.lower()}...")
                                
                                # Prepare canvas config
                                canvas_config = {
                                    "numberOfImages": 1,
                                    "quality": canvas_quality if 'canvas_quality' in locals() else "standard",
                                    "height": canvas_height if 'canvas_height' in locals() else 720,
                                    "width": canvas_width if 'canvas_width' in locals() else 1280,
                                    "cfgScale": canvas_cfg_scale if 'canvas_cfg_scale' in locals() else 8
                                }
                                
                                image_bytes = self.nova_canvas.process(
                                    image_bytes,
                                    negative_prompt,
                                    main_prompt,
                                    mask_prompt,
                                    preprocessing.upper(),
                                    canvas_config
                                )
                                
                                if image_bytes:
                                    st.image(image_bytes, caption=f"After {preprocessing.lower()}")
                                else:
                                    st.error(f"Failed to {preprocessing.lower()} the image")
                                    return
                            
                            # Generate video
                            if video_prompt:
                                st.info("Generating video...")
                                
                                # Prepare video config
                                video_config = {
                                    "durationSeconds": video_duration if 'video_duration' in locals() else 6,
                                    "fps": video_fps if 'video_fps' in locals() else 24,
                                    "dimension": video_dimension if 'video_dimension' in locals() else "1280x720",
                                    "seed": video_seed if 'video_seed' in locals() else 0
                                }
                                
                                self.nova_reel.process(
                                    image_bytes,
                                    video_prompt,
                                    self.status_callback,
                                    video_config
                                )
                            else:
                                st.error("Please enter a video generation prompt")
                        
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")
            else:
                # Show placeholder when no image is uploaded
                st.info("👆 Upload an image to get started")
        
        with tab2:
            st.markdown("<h3 class='sub-header'>About this Application</h3>", unsafe_allow_html=True)
            st.write("""
            This application uses AWS Bedrock AI models to transform static images into dynamic videos:
            
            - **Nova Canvas**: Allows for inpainting (filling in parts of an image) and outpainting (extending an image beyond its borders)
            - **Nova Reel**: Transforms static images into fluid videos based on text prompts
            
            The application is built with Streamlit and uses AWS SDK for Python (Boto3) to interact with AWS services.
            """)
            
            st.markdown("<h3 class='sub-header'>How to Use</h3>", unsafe_allow_html=True)
            st.write("""
            1. Upload an image using the file uploader
            2. Optionally select inpainting or outpainting to modify your image
            3. Enter a video generation prompt describing the motion you want
            4. Adjust advanced parameters if needed
            5. Click "Generate Video" to start the process
            """)


if __name__ == "__main__":
    ui = StreamlitUI()
    ui.run()