"""
Pytest configuration file for the Sports Marketing Video Generator tests.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock

# Add the app directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def mock_boto3_client(mocker):
    """Fixture to mock boto3.client"""
    mock_client = mocker.patch('boto3.client')
    return mock_client

@pytest.fixture
def mock_bedrock_client():
    """Fixture to create a mock Bedrock client"""
    mock_client = MagicMock()
    return mock_client

@pytest.fixture
def mock_s3_client():
    """Fixture to create a mock S3 client"""
    mock_client = MagicMock()
    return mock_client

@pytest.fixture
def mock_rekognition_client():
    """Fixture to create a mock Rekognition client"""
    mock_client = MagicMock()
    return mock_client