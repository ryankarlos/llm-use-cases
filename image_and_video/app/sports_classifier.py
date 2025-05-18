import boto3
import logging

# Configure logging
logger = logging.getLogger(__name__)

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