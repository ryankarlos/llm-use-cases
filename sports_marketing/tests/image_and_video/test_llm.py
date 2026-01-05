from image_and_video.llm import NovaCanvasProcessor
from image_and_video.llm import NovaCanvasProcessor, DEFAULT_IMAGE_CONFIG
from image_and_video.llm import NovaReelProcessor
from image_and_video.llm import NovaReelProcessor, NOVA_REEL_BASE_PROMPT
from image_and_video.llm import NovaReelProcessor, S3_BUCKET, POLL_INTERVAL
from image_and_video.llm import NovaReelProcessor, S3_BUCKET, POLL_INTERVAL, AWS_REGION
from image_and_video.llm import S3Service
from image_and_video.sports_classifier import SportsImageClassifier
from moto import mock_aws
from unittest.mock import MagicMock, patch
from unittest.mock import Mock, patch
from unittest.mock import patch
from unittest.mock import patch, MagicMock
import base64
import boto3
import json
import os
import pytest
import unittest

class TestLlm:

    def test___init___1(self):
        """
        Test the initialization of NovaCanvasProcessor.

        This test verifies that the NovaCanvasProcessor is correctly initialized
        with the expected attributes: bedrock_runtime client, accept and content_type
        headers, and an instance of SportsImageClassifier.
        """
        with patch('boto3.client') as mock_boto3_client:
            mock_bedrock_runtime = mock_boto3_client.return_value

            nova_canvas_processor = NovaCanvasProcessor()

            # Assert that boto3.client was called with correct parameters
            mock_boto3_client.assert_called_once_with(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )

            # Assert that the attributes are set correctly
            assert nova_canvas_processor.bedrock_runtime == mock_bedrock_runtime
            assert nova_canvas_processor.accept == "application/json"
            assert nova_canvas_processor.content_type == "application/json"
            assert isinstance(nova_canvas_processor.sports_classifier, SportsImageClassifier)

    def test___init___1_2(self):
        """
        Test the initialization of NovaReelProcessor with default parameters.
        Verifies that the object is created with correct attribute values and
        that the boto3 client is initialized properly.
        """
        with patch('boto3.client') as mock_boto3_client:
            processor = NovaReelProcessor()

            # Assert that boto3 client was called with correct parameters
            mock_boto3_client.assert_called_once_with(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_REGION", AWS_REGION)
            )

            # Verify that attributes are set correctly
            assert processor.s3_bucket == S3_BUCKET
            assert processor.poll_interval == POLL_INTERVAL
            assert isinstance(processor.s3_service, S3Service)
            assert isinstance(processor.sports_classifier, SportsImageClassifier)

    def test___init___with_invalid_poll_interval(self):
        """
        Test initializing NovaReelProcessor with an invalid poll interval.
        This test checks if the constructor properly handles a non-numeric poll interval,
        which is explicitly set in the __init__ method.
        """
        with self.assertRaises(TypeError):
            NovaReelProcessor(poll_interval="not_a_number")

    def test___init___with_invalid_s3_bucket(self):
        """
        Test initializing NovaReelProcessor with an invalid S3 bucket name.
        This test verifies that the constructor correctly handles an invalid S3 bucket name,
        which is explicitly set in the __init__ method.
        """
        with patch('boto3.client') as mock_boto3_client:
            # Simulate boto3 client creation failing due to invalid bucket name
            mock_boto3_client.side_effect = boto3.exceptions.Boto3Error("Invalid bucket name")

            with self.assertRaises(boto3.exceptions.Boto3Error):
                NovaReelProcessor(s3_bucket="XXXXXXXXXXXXXXXXXXX")

    def test___init___with_missing_aws_region(self):
        """
        Test initialization of NovaCanvasProcessor when AWS_REGION environment variable is not set.
        This tests the edge case where the environment variable is missing, and the method falls back to the default region.
        """
        with patch.dict('os.environ', clear=True):
            # Remove AWS_REGION from environment variables
            if 'AWS_REGION' in os.environ:
                del os.environ['AWS_REGION']

            processor = NovaCanvasProcessor()

            # Assert that the bedrock_runtime client is created with the default region
            assert processor.bedrock_runtime.meta.region_name == 'us-east-1'  # Assuming 'us-east-1' is the default in AWS_REGION constant

    @mock_aws
    def test_create_presigned_url_1(self):
        """
        Test that create_presigned_url generates a valid presigned URL for an S3 object.
        """
        # Set up mock S3 bucket and object
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'XXXXXXXXXXX'
        object_name = 'test-object'
        s3.create_bucket(Bucket=bucket_name)
        s3.put_object(Bucket=bucket_name, Key=object_name, Body='test content')

        # Call the method under test
        result = S3Service.create_presigned_url(bucket_name, object_name)

        # Assert that a URL is returned
        assert result is not None
        assert isinstance(result, str)
        assert 'https://' in result
        assert bucket_name in result
        assert object_name in result

    def test_create_presigned_url_exception_handling(self):
        """
        Test that the create_presigned_url method handles exceptions and returns None.
        This test simulates an exception occurring during the presigned URL generation.
        """
        with mock_aws():
            s3_client = boto3.client('s3', region_name='us-east-1')
            s3_client.create_bucket(Bucket='XXXXXXXXXXX')

            # Simulate an exception by passing an invalid expiration
            result = S3Service.create_presigned_url('test-bucket', 'test-object', expiration='invalid')

            assert result is None

    def test_enhance_prompt_2(self):
        """
        Test enhance_prompt method with no brand and with sport_type.

        This test verifies that the enhance_prompt method correctly enhances
        the marketing prompt by adding the base Nova Reel prompt and the
        sport type, without including a brand.
        """
        processor = NovaReelProcessor()
        marketing_prompt = "Create an exciting video"
        sport_type = "basketball"

        expected_prompt = f"{NOVA_REEL_BASE_PROMPT.strip()} {marketing_prompt} in the context of {sport_type}"
        result = processor.enhance_prompt(marketing_prompt, sport_type=sport_type)

        assert result == expected_prompt

    def test_enhance_prompt_3(self):
        """
        Test enhance_prompt method with brand parameter but without sport_type.

        This test verifies that the enhance_prompt method correctly enhances
        the marketing prompt by appending the base Nova Reel prompt and the
        brand, but not including any sport type context.
        """
        processor = NovaReelProcessor()
        marketing_prompt = "Create an exciting video"
        brand = "Nike"
        enhanced_prompt = processor.enhance_prompt(marketing_prompt, brand=brand)
        expected_prompt = f"{NOVA_REEL_BASE_PROMPT.strip()} {marketing_prompt} for {brand}"
        assert enhanced_prompt == expected_prompt, f"Expected '{expected_prompt}', but got '{enhanced_prompt}'"

    def test_enhance_prompt_empty_input(self):
        """
        Test enhance_prompt method with an empty marketing_prompt.
        This tests the edge case of providing an empty string as input,
        which is explicitly handled by the method (it will still append
        the base prompt).
        """
        processor = NovaReelProcessor()
        result = processor.enhance_prompt("")
        assert result == NOVA_REEL_BASE_PROMPT.strip()

    def test_enhance_prompt_only_brand(self):
        """
        Test enhance_prompt method with only the brand parameter provided.
        This tests the edge case where sport_type is None but brand is given,
        which is explicitly handled in the method.
        """
        processor = NovaReelProcessor()
        result = processor.enhance_prompt("", brand="Nike")
        expected = NOVA_REEL_BASE_PROMPT.strip() + " for Nike"
        assert result == expected

    def test_enhance_prompt_only_sport_type(self):
        """
        Test enhance_prompt method with only the sport_type parameter provided.
        This tests the edge case where brand is None but sport_type is given,
        which is explicitly handled in the method.
        """
        processor = NovaReelProcessor()
        result = processor.enhance_prompt("", sport_type="basketball")
        expected = NOVA_REEL_BASE_PROMPT.strip() + " in the context of basketball"
        assert result == expected

    def test_enhance_prompt_with_brand_and_sport_type(self):
        """
        Test the enhance_prompt method with both brand and sport_type provided.

        This test verifies that the enhance_prompt method correctly combines
        the base prompt with the marketing prompt and appends both the brand
        and sport type information when provided.
        """
        processor = NovaReelProcessor()
        marketing_prompt = "Create an exciting video"
        brand = "Nike"
        sport_type = "basketball"

        enhanced_prompt = processor.enhance_prompt(marketing_prompt, brand, sport_type)

        expected_prompt = f"{NOVA_REEL_BASE_PROMPT.strip()} {marketing_prompt} for {brand} in the context of {sport_type}"
        assert enhanced_prompt == expected_prompt, f"Expected '{expected_prompt}', but got '{enhanced_prompt}'"

    def test_process_2(self):
        """
        Test NovaCanvasProcessor.process() for a sports image with inpainting operation and default config.

        This test verifies that:
        1. The image is correctly identified as sports-related.
        2. The default config is used when none is provided.
        3. The inpainting operation is correctly set up.
        4. The bedrock runtime is invoked with the correct parameters.
        5. The response is properly processed and returned as image bytes.
        """
        # Mock the SportsImageClassifier
        mock_classifier = Mock()
        mock_classifier.is_sports_image.return_value = (True, ["sports"])

        # Mock the bedrock runtime client
        mock_bedrock = Mock()
        mock_response = Mock()
        mock_response.get.return_value.read.return_value = json.dumps({"images": ["base64_image_data"]})
        mock_bedrock.invoke_model.return_value = mock_response

        # Create a NovaCanvasProcessor instance with mocked dependencies
        processor = NovaCanvasProcessor()
        processor.sports_classifier = mock_classifier
        processor.bedrock_runtime = mock_bedrock

        # Test inputs
        image_bytes = b"fake_image_data"
        negative_prompt = "negative prompt"
        main_prompt = "main prompt"
        mask_prompt = "mask prompt"
        operation_type = "INPAINTING"

        # Call the process method
        with patch('image_and_video.llm.DEFAULT_IMAGE_CONFIG', {'key': 'value'}):
            result = processor.process(image_bytes, negative_prompt, main_prompt, mask_prompt, operation_type)

        # Assertions
        mock_classifier.is_sports_image.assert_called_once_with(image_bytes)
        mock_bedrock.invoke_model.assert_called_once()
        invoke_args = mock_bedrock.invoke_model.call_args[1]
        assert invoke_args['modelId'] == "amazon.nova-canvas-v1:0"
        assert invoke_args['accept'] == "application/json"
        assert invoke_args['contentType'] == "application/json"

        body = json.loads(invoke_args['body'])
        assert body['taskType'] == "INPAINTING"
        assert body['imageGenerationConfig'] == {'key': 'value'}
        assert body['inPaintingParams']['text'] == main_prompt
        assert body['inPaintingParams']['maskPrompt'] == mask_prompt
        assert body['inPaintingParams']['negativeText'] == negative_prompt
        assert body['inPaintingParams']['image'] == base64.b64encode(image_bytes).decode('utf-8')

        assert isinstance(result, bytes)

    def test_process_2_2(self):
        """
        Test that the process method returns "NOT_SPORTS_IMAGE" when the image is not sports-related
        and no status callback is provided.
        """
        # Arrange
        nova_reel_processor = NovaReelProcessor()
        nova_reel_processor.sports_classifier = MagicMock()
        nova_reel_processor.sports_classifier.is_sports_image.return_value = (False, [])
        image_bytes = b"mock_image_bytes"
        prompt = "Test prompt"

        # Act
        result = nova_reel_processor.process(image_bytes, prompt)

        # Assert
        self.assertEqual(result, "NOT_SPORTS_IMAGE")
        nova_reel_processor.sports_classifier.is_sports_image.assert_called_once_with(image_bytes)

    def test_process_3_inpainting_with_custom_config(self):
        """
        Test the process method of NovaCanvasProcessor for inpainting operation
        with a custom configuration on a sports-related image.

        This test verifies that:
        1. The image is classified as sports-related
        2. A custom configuration is used instead of the default
        3. The inpainting operation is correctly set up
        4. The bedrock runtime is invoked with the correct parameters
        5. The response is properly processed and returned as image bytes
        """
        # Mock setup
        mock_sports_classifier = MagicMock()
        mock_sports_classifier.is_sports_image.return_value = (True, ["sports"])

        mock_bedrock_runtime = MagicMock()
        mock_response = MagicMock()
        mock_response.get.return_value.read.return_value = json.dumps({"images": ["base64_encoded_image"]})
        mock_bedrock_runtime.invoke_model.return_value = mock_response

        # Create NovaCanvasProcessor instance with mocked dependencies
        processor = NovaCanvasProcessor()
        processor.sports_classifier = mock_sports_classifier
        processor.bedrock_runtime = mock_bedrock_runtime

        # Test data
        image_bytes = b"fake_image_data"
        negative_prompt = "negative prompt"
        main_prompt = "main prompt"
        mask_prompt = "mask prompt"
        operation_type = "INPAINTING"
        custom_config = {"key": "value"}

        # Execute the method
        result = processor.process(image_bytes, negative_prompt, main_prompt, mask_prompt, operation_type, config=custom_config)

        # Assertions
        assert result is not None
        mock_sports_classifier.is_sports_image.assert_called_once_with(image_bytes)
        mock_bedrock_runtime.invoke_model.assert_called_once()

        # Verify the correct body was passed to invoke_model
        call_args = mock_bedrock_runtime.invoke_model.call_args
        body_arg = json.loads(call_args[1]['body'])
        assert body_arg['taskType'] == "INPAINTING"
        assert body_arg['imageGenerationConfig'] == custom_config
        assert 'inPaintingParams' in body_arg
        assert body_arg['inPaintingParams']['text'] == main_prompt
        assert body_arg['inPaintingParams']['maskPrompt'] == mask_prompt
        assert body_arg['inPaintingParams']['negativeText'] == negative_prompt
        assert body_arg['inPaintingParams']['image'] == base64.b64encode(image_bytes).decode('utf-8')

    def test_process_exception(self):
        """
        Test the process method when an exception occurs.
        This tests the edge case where an unexpected exception is raised,
        which is explicitly handled in the method.
        """
        processor = NovaReelProcessor()
        sports_image = b"fake_sports_image_bytes"
        prompt = "Test prompt"

        # Mock the sports classifier to raise an exception
        processor.sports_classifier.is_sports_image = lambda x: (_ for _ in ()).throw(Exception("Test exception"))

        result = processor.process(sports_image, prompt)

        assert result is None

    def test_process_exception_handling(self):
        """
        Test the process method's exception handling.
        This tests the edge case where an exception occurs during processing,
        which is explicitly handled in the focal method.
        """
        processor = NovaCanvasProcessor()

        # Mock the sports classifier to raise an exception
        with patch.object(processor.sports_classifier, 'is_sports_image', side_effect=Exception("Test exception")):
            result = processor.process(
                image_bytes=b'dummy_image_data',
                negative_prompt='negative',
                main_prompt='main',
                mask_prompt='mask',
                operation_type='INPAINTING'
            )

        assert result is None

    def test_process_failed_job(self):
        """
        Test the process method when the job fails.
        This tests the edge case where the video generation job fails,
        which is explicitly handled in the method.
        """
        processor = NovaReelProcessor()
        sports_image = b"fake_sports_image_bytes"
        prompt = "Test prompt"

        # Mock the necessary methods
        processor.sports_classifier.is_sports_image = lambda x: (True, [])
        processor.bedrock_runtime.start_async_invoke = lambda **kwargs: {"invocationArn": "test_arn"}
        processor.bedrock_runtime.get_async_invoke = lambda **kwargs: {"status": "Failed", "failureMessage": "Test failure"}

        result = processor.process(sports_image, prompt)

        assert result is None

    def test_process_non_sports_image(self):
        """
        Test that the process method returns "NOT_SPORTS_IMAGE" when the input image is not sports-related.

        This test verifies that when the SportsImageClassifier determines the input image
        is not sports-related, the process method immediately returns "NOT_SPORTS_IMAGE"
        without proceeding to further processing steps.
        """
        processor = NovaCanvasProcessor()
        processor.sports_classifier.is_sports_image = lambda x: (False, [])  # Mock the classifier

        result = processor.process(
            image_bytes=b"dummy_image_data",
            negative_prompt="dummy_negative",
            main_prompt="dummy_main",
            mask_prompt="dummy_mask",
            operation_type="INPAINTING"
        )

        assert result == "NOT_SPORTS_IMAGE"

    def test_process_non_sports_image_2(self):
        """
        Test the process method when a non-sports image is provided.
        This tests the edge case where the input image is not sports-related,
        which is explicitly handled in the focal method.
        """
        processor = NovaCanvasProcessor()

        # Mock the sports classifier to return False (not a sports image)
        with patch.object(processor.sports_classifier, 'is_sports_image', return_value=(False, [])):
            result = processor.process(
                image_bytes=b'dummy_image_data',
                negative_prompt='negative',
                main_prompt='main',
                mask_prompt='mask',
                operation_type='INPAINTING'
            )

        assert result == "NOT_SPORTS_IMAGE"

    def test_process_non_sports_image_3(self):
        """
        Test the process method with a non-sports image.
        This tests the edge case where the input image is not sports-related,
        which is explicitly handled in the method.
        """
        processor = NovaReelProcessor()
        non_sports_image = b"fake_non_sports_image_bytes"
        prompt = "Test prompt"

        # Mock the sports classifier to return False
        processor.sports_classifier.is_sports_image = lambda x: (False, [])

        result = processor.process(non_sports_image, prompt)

        assert result == "NOT_SPORTS_IMAGE"

    def test_process_not_sports_image(self):
        """
        Test that the process method returns "NOT_SPORTS_IMAGE" when the image is not sports-related
        and calls the status_callback with an error message.
        """
        # Arrange
        processor = NovaReelProcessor()
        mock_image_bytes = b'fake_image_data'
        mock_prompt = "Test prompt"
        mock_status_callback = Mock()

        # Mock the sports_classifier to return False
        with patch.object(processor.sports_classifier, 'is_sports_image', return_value=(False, [])):
            # Act
            result = processor.process(mock_image_bytes, mock_prompt, status_callback=mock_status_callback)

        # Assert
        self.assertEqual(result, "NOT_SPORTS_IMAGE")
        mock_status_callback.assert_called_once_with("error", "The uploaded image is not sports-related. Please upload an image related to sports for creating a sports marketing video.")

    def test_process_operation_type_invalid(self):
        """
        Test process method with an invalid operation type.

        This test verifies the behavior when:
        - The image is sports-related (is_sports is True)
        - No config is provided (config is None)
        - An invalid operation type is given (not "INPAINTING" or "OUTPAINTING")

        Expected: The method should return the processed image bytes.
        """
        processor = NovaCanvasProcessor()
        processor.sports_classifier = Mock()
        processor.sports_classifier.is_sports_image.return_value = (True, ["sports"])

        mock_response = Mock()
        mock_response.get.return_value.read.return_value = json.dumps({"images": ["base64_encoded_image"]})

        processor.bedrock_runtime = Mock()
        processor.bedrock_runtime.invoke_model.return_value = mock_response

        image_bytes = b"test_image"
        negative_prompt = "negative"
        main_prompt = "main"
        mask_prompt = "mask"
        operation_type = "INVALID_TYPE"

        result = processor.process(image_bytes, negative_prompt, main_prompt, mask_prompt, operation_type)

        assert result is not None
        assert isinstance(result, bytes)

    def test_process_outpainting_with_default_config(self):
        """
        Test the process method of NovaCanvasProcessor for outpainting with default config.

        This test verifies that:
        1. The image is classified as sports-related
        2. The default config is used when none is provided
        3. The outpainting operation is correctly set up
        4. The Bedrock runtime is invoked with the correct parameters
        5. The response is properly processed and returned
        """
        # Mock the SportsImageClassifier
        mock_classifier = Mock()
        mock_classifier.is_sports_image.return_value = (True, ["sports"])

        # Mock the Bedrock runtime client
        mock_bedrock = Mock()
        mock_response = Mock()
        mock_response.get.return_value.read.return_value = json.dumps({"images": ["base64_image_data"]})
        mock_bedrock.invoke_model.return_value = mock_response

        # Create the NovaCanvasProcessor instance
        processor = NovaCanvasProcessor()
        processor.sports_classifier = mock_classifier
        processor.bedrock_runtime = mock_bedrock

        # Test inputs
        image_bytes = b"test_image_bytes"
        negative_prompt = "negative prompt"
        main_prompt = "main prompt"
        mask_prompt = "mask prompt"
        operation_type = "OUTPAINTING"

        # Call the process method
        with patch('image_and_video.llm.DEFAULT_IMAGE_CONFIG', {'key': 'value'}):
            result = processor.process(image_bytes, negative_prompt, main_prompt, mask_prompt, operation_type)

        # Assertions
        mock_classifier.is_sports_image.assert_called_once_with(image_bytes)
        mock_bedrock.invoke_model.assert_called_once()
        assert result == b"base64_image_data"
