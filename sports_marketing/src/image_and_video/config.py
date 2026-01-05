"""Configuration settings for the Sports Marketing Video Generator"""
import os

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# S3 bucket for video storage
S3_BUCKET = os.getenv("S3_BUCKET", "nova-reel-videos-demo")

# Video polling interval in seconds
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

# Cognito Authentication Settings
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
COGNITO_APP_CLIENT_SECRET = os.getenv("COGNITO_APP_CLIENT_SECRET")
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN")
COGNITO_REDIRECT_URI = os.getenv("COGNITO_REDIRECT_URI", "http://localhost:8501/")

# Default video configuration
DEFAULT_VIDEO_CONFIG = {
    "durationSeconds": 30,
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

# Sports marketing video templates
SPORTS_MARKETING_VIDEOS = {
    "dynamic_action": "Create a dynamic sports marketing video with fast-paced action shots, energetic transitions, and powerful moments",
    "athlete_showcase": "Create a sports marketing video highlighting an athlete's skill, form, and determination with close-up shots",
    "team_spirit": "Create a sports marketing video showcasing team unity, celebration, and collective achievement",
    "fan_experience": "Create a sports marketing video focusing on fan excitement, crowd reactions, and the emotional connection to the sport",
    "product_in_action": "Create a sports marketing video demonstrating sports equipment or apparel being used in authentic athletic scenarios",
    "inspirational": "Create an inspirational sports marketing video with motivational moments, overcoming challenges, and triumphant achievements"
}

# Base prompt for Amazon Nova Reel AI Sports marketing
NOVA_REEL_BASE_PROMPT = """
You are SportVision AI, a premier sports marketing agency specializing in creating dynamic sports content.Use dynamic camera angles, smooth transitions, and high-energy motion.
"""