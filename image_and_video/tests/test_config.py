"""
Test cases for the config module
"""
import pytest
import os
from unittest.mock import patch

from image_and_video.config import (
    AWS_REGION, S3_BUCKET, POLL_INTERVAL, DEFAULT_VIDEO_CONFIG, 
    DEFAULT_IMAGE_CONFIG, SPORTS_MARKETING_VIDEOS, NOVA_REEL_BASE_PROMPT
)

class TestConfig:
    """Test cases for the config module"""
    
    def test_default_config_values(self):
        """Test that default configuration values are set correctly"""
        # Test default values when environment variables are not set
        assert AWS_REGION == "us-east-1"
        assert S3_BUCKET == "nova-reel-videos-demo"
        assert POLL_INTERVAL == 30
        
        # Test default video configuration
        assert DEFAULT_VIDEO_CONFIG["durationSeconds"] == 6
        assert DEFAULT_VIDEO_CONFIG["fps"] == 24
        assert DEFAULT_VIDEO_CONFIG["dimension"] == "1280x720"
        assert DEFAULT_VIDEO_CONFIG["seed"] == 0
        
        # Test default image configuration
        assert DEFAULT_IMAGE_CONFIG["numberOfImages"] == 1
        assert DEFAULT_IMAGE_CONFIG["quality"] == "standard"
        assert DEFAULT_IMAGE_CONFIG["height"] == 1280
        assert DEFAULT_IMAGE_CONFIG["width"] == 720
        assert DEFAULT_IMAGE_CONFIG["cfgScale"] == 8
    
    @patch.dict(os.environ, {"AWS_REGION": "eu-west-1"})
    def test_aws_region_from_env(self):
        """Test that AWS_REGION is read from environment variable"""
        # We need to reload the module to pick up the environment variable
        import importlib
        import image_and_video.config
        importlib.reload(image_and_video.config)
        
        # Now test the reloaded value
        assert image_and_video.config.AWS_REGION == "eu-west-1"
    
    @patch.dict(os.environ, {"S3_BUCKET": "custom-bucket"})
    def test_s3_bucket_from_env(self):
        """Test that S3_BUCKET is read from environment variable"""
        # We need to reload the module to pick up the environment variable
        import importlib
        import image_and_video.config
        importlib.reload(image_and_video.config)
        
        # Now test the reloaded value
        assert image_and_video.config.S3_BUCKET == "custom-bucket"
    
    @patch.dict(os.environ, {"POLL_INTERVAL": "60"})
    def test_poll_interval_from_env(self):
        """Test that POLL_INTERVAL is read from environment variable"""
        # We need to reload the module to pick up the environment variable
        import importlib
        import image_and_video.config
        importlib.reload(image_and_video.config)
        
        # Now test the reloaded value
        assert image_and_video.config.POLL_INTERVAL == 60
    
    def test_sports_marketing_videos_templates(self):
        """Test that sports marketing video templates are defined"""
        # Test that the templates dictionary has the expected keys
        expected_keys = [
            "dynamic_action", "athlete_showcase", "team_spirit", 
            "fan_experience", "product_in_action", "inspirational"
        ]
        
        for key in expected_keys:
            assert key in SPORTS_MARKETING_VIDEOS
            assert isinstance(SPORTS_MARKETING_VIDEOS[key], str)
            assert len(SPORTS_MARKETING_VIDEOS[key]) > 0
    
    def test_nova_reel_base_prompt(self):
        """Test that the Nova Reel base prompt is defined"""
        assert isinstance(NOVA_REEL_BASE_PROMPT, str)
        assert "SportVision AI" in NOVA_REEL_BASE_PROMPT
        assert len(NOVA_REEL_BASE_PROMPT) > 0