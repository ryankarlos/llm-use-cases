"""Configuration settings for the Sports Marketing Video Generator"""
import os

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# S3 bucket for video storage
S3_BUCKET = os.getenv("S3_BUCKET", "nova-reel-videos-demo")

# Video polling interval in seconds
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

# Default video configuration
DEFAULT_VIDEO_CONFIG = {
    "durationSeconds": 6,
    "fps": 24,
    "dimension": "1280x720",
    "seed": 0
}

# Default image configuration
DEFAULT_IMAGE_CONFIG = {
    "numberOfImages": 1,
    "quality": "standard",
    "height": 1280,
    "width": 720,
    "cfgScale": 8
}

# Sports marketing prompt templates
SPORTS_PROMPT_TEMPLATES = {
    "brand_awareness": "Create a sports marketing video that builds brand awareness with dynamic action and clear brand visibility",
    "product_launch": "Create a sports marketing video showcasing a new product launch with athletes demonstrating its features",
    "event_promotion": "Create a sports marketing video promoting an upcoming sports event with excitement and anticipation",
    "athlete_endorsement": "Create a sports marketing video featuring an athlete endorsement with authentic connection to the brand",
    "team_sponsorship": "Create a sports marketing video highlighting team sponsorship with brand integration and team spirit",
    "inspirational": "Create an inspirational sports marketing video that motivates viewers with powerful athletic achievements"
}