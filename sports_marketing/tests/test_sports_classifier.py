"""
Test cases for the SportsImageClassifier class
"""
import pytest
from unittest.mock import MagicMock

from image_and_video.sports_classifier import SportsImageClassifier

class TestSportsImageClassifier:
    """Test cases for the SportsImageClassifier class"""
    
    @pytest.fixture
    def sports_classifier(self, mock_boto3_client, mock_rekognition_client):
        """Set up test fixtures"""
        # Configure the mock boto3.client to return our mock clients
        mock_boto3_client.side_effect = lambda service, region_name=None: {
            'rekognition': mock_rekognition_client
        }[service]
        
        # Create an instance of SportsImageClassifier
        return SportsImageClassifier()
    
    def test_is_sports_image_positive_match(self, sports_classifier, mock_rekognition_client):
        """Test identifying a sports image with direct keyword match"""
        # Mock the response from Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Basketball', 'Confidence': 98.5},
                {'Name': 'Person', 'Confidence': 99.2},
                {'Name': 'Court', 'Confidence': 95.7}
            ]
        }
        
        # Test data
        image_bytes = b'test_image_bytes'
        
        # Call the method
        is_sports, labels = sports_classifier.is_sports_image(image_bytes)
        
        # Assertions
        assert is_sports is True
        assert 'basketball' in labels
        assert 'court' in labels
        
        # Verify that Rekognition was called with the correct parameters
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': image_bytes})
    
    def test_is_sports_image_high_confidence(self, sports_classifier, mock_rekognition_client):
        """Test identifying a sports image with high confidence but indirect match"""
        # Mock the response from Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Ball', 'Confidence': 95.0},  # Not an exact match but contains "ball" which is in sports_keywords
                {'Name': 'Person', 'Confidence': 99.2},
                {'Name': 'Field', 'Confidence': 90.5}  # Not an exact match but contains "field" which is in sports_keywords
            ]
        }
        
        # Test data
        image_bytes = b'test_image_bytes'
        
        # Call the method
        is_sports, labels = sports_classifier.is_sports_image(image_bytes)
        
        # Assertions
        assert is_sports is True
        assert 'ball' in labels
        assert 'field' in labels
        
        # Verify that Rekognition was called with the correct parameters
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': image_bytes})
    
    def test_is_sports_image_negative(self, sports_classifier, mock_rekognition_client):
        """Test identifying a non-sports image"""
        # Mock the response from Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Car', 'Confidence': 98.5},
                {'Name': 'Road', 'Confidence': 99.2},
                {'Name': 'Building', 'Confidence': 95.7}
            ]
        }
        
        # Test data
        image_bytes = b'test_image_bytes'
        
        # Call the method
        is_sports, labels = sports_classifier.is_sports_image(image_bytes)
        
        # Assertions
        assert is_sports is False
        assert 'car' in labels
        assert 'road' in labels
        
        # Verify that Rekognition was called with the correct parameters
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': image_bytes})
    
    def test_is_sports_image_exception(self, sports_classifier, mock_rekognition_client):
        """Test handling exceptions during image classification"""
        # Mock the Rekognition client to raise an exception
        mock_rekognition_client.detect_labels.side_effect = Exception("Test exception")
        
        # Test data
        image_bytes = b'test_image_bytes'
        
        # Call the method
        is_sports, labels = sports_classifier.is_sports_image(image_bytes)
        
        # Assertions
        assert is_sports is False
        assert labels == []
        
        # Verify that Rekognition was called with the correct parameters
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': image_bytes})

    def test_init_sports_keywords(self):
        """
        Test that the __init__ method correctly initializes the sports_keywords list
        with the expected keywords for image analysis.
        """
        classifier = SportsImageClassifier()

        expected_keywords = [
            "sports", "athlete", "game", "match", "competition", "team", 
            "stadium", "field", "court", "ball", "player", "race", "tournament",
            "basketball", "football", "soccer", "baseball", "tennis", "golf",
            "hockey", "rugby", "volleyball", "swimming", "track", "fitness",
            "running", "cycling", "boxing", "martial arts", "olympics"
        ]

        assert classifier.sports_keywords == expected_keywords
        assert len(classifier.sports_keywords) == 30
        assert all(isinstance(keyword, str) for keyword in classifier.sports_keywords)

    def test_is_sports_image_high_confidence_2(self, sports_classifier, mock_rekognition_client):
        """
        Test that is_sports_image returns True when a sports-related label has high confidence,
        even if the exact keyword is not in the labels list.
        """
        # Mock the response from Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Person', 'Confidence': 99.9},
                {'Name': 'Football Player', 'Confidence': 95.5},
                {'Name': 'Ball', 'Confidence': 85.0},
                {'Name': 'Field', 'Confidence': 80.0}
            ]
        }

        # Call the method under test
        result, labels = sports_classifier.is_sports_image(b'dummy_image_bytes')

        # Assert the expected outcome
        assert result == True
        assert 'football player' in [label.lower() for label in labels]
        assert len(labels) == 4

    def test_is_sports_image_keyword_in_labels(self, sports_classifier, mock_rekognition_client):
        """
        Test that is_sports_image returns True when a sports keyword is present in the labels.

        This test verifies that the method correctly identifies a sports image when
        one of the sports keywords is found in the labels returned by Amazon Rekognition.
        """
        # Mock the response from Amazon Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Person', 'Confidence': 99.9},
                {'Name': 'Sport', 'Confidence': 95.0},
                {'Name': 'Football', 'Confidence': 90.0}
            ]
        }

        # Call the method with a dummy image bytes
        result, labels = sports_classifier.is_sports_image(b'dummy_image_bytes')

        # Assert that the method returns True and the correct labels
        assert result is True
        assert labels == ['person', 'sport', 'football']

        # Verify that detect_labels was called with the correct parameters
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': b'dummy_image_bytes'})

    def test_is_sports_image_no_match_low_confidence(self, sports_classifier, mock_rekognition_client):
        """
        Test is_sports_image when no sports keywords match directly,
        a sports-related label is found with low confidence,
        and the method should return False.
        """
        # Mock the response from Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Person', 'Confidence': 99.9},
                {'Name': 'Football Field', 'Confidence': 65.0},
                {'Name': 'Grass', 'Confidence': 95.0}
            ]
        }

        # Call the method under test
        result, labels = sports_classifier.is_sports_image(b'dummy_image_bytes')

        # Assert the expected outcome
        assert result == False
        assert labels == ['person', 'football field', 'grass']
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': b'dummy_image_bytes'})

    def test_is_sports_image_non_sports_related(self, sports_classifier, mock_rekognition_client):
        """
        Test the is_sports_image method when the image is not sports-related.

        This test verifies that the method returns False when the image labels
        do not contain any sports keywords and the confidence scores for any
        sports-related activities are below the threshold.
        """
        # Mock the response from Rekognition
        mock_rekognition_client.detect_labels.return_value = {
            'Labels': [
                {'Name': 'Nature', 'Confidence': 95.0},
                {'Name': 'Landscape', 'Confidence': 90.0},
                {'Name': 'Outdoors', 'Confidence': 85.0}
            ]
        }

        # Call the method under test
        result, labels = sports_classifier.is_sports_image(b'dummy_image_bytes')

        # Assert the expected results
        assert result == False
        assert labels == ['nature', 'landscape', 'outdoors']
        mock_rekognition_client.detect_labels.assert_called_once_with(Image={'Bytes': b'dummy_image_bytes'})

    def test_is_sports_image_rekognition_exception(self, sports_classifier, mock_rekognition_client):
        """
        Test the is_sports_image method when Rekognition client raises an exception.
        Verify that the method handles the exception and returns False with an empty list.
        """
        # Mock the Rekognition client to raise an exception
        mock_rekognition_client.detect_labels.side_effect = Exception("Rekognition error")

        # Call the method with some dummy image bytes
        result, labels = sports_classifier.is_sports_image(b"dummy_image_bytes")

        # Assert that the method returns False and an empty list
        assert result == False
        assert labels == []
