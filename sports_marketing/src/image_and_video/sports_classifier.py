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
            
            # Determine the specific sport type from labels
            sport_type = self.determine_sport_type(labels, response['Labels'])
            
            # Check if any sports keywords are in the labels
            for keyword in self.sports_keywords:
                if keyword.lower() in labels:
                    return True, labels, sport_type
                    
            # Check for confidence scores on sports-related activities
            for label in response['Labels']:
                if any(keyword.lower() in label['Name'].lower() for keyword in self.sports_keywords):
                    if label['Confidence'] > 70:
                        return True, labels, sport_type
            
            return False, labels, "General Sports"
            
        except Exception as e:
            logger.error(f"Error in sports image classification: {str(e)}")
            return False, [], "General Sports"
            
    def determine_sport_type(self, labels, raw_labels):
        """Determine the specific sport type from detected labels"""
        # Map of specific sports to look for in labels
        sport_mapping = {
            "basketball": "Basketball",
            "football": "Football",
            "soccer": "Soccer",
            "tennis": "Tennis",
            "golf": "Golf",
            "swimming": "Swimming",
            "running": "Running",
            "cycling": "Cycling",
            "baseball": "Baseball",
            "volleyball": "Volleyball"
        }
        
        # First check for exact matches with high confidence
        for label in raw_labels:
            label_name = label['Name'].lower()
            if label_name in sport_mapping and label['Confidence'] > 75:
                return sport_mapping[label_name]
        
        # Then check for partial matches in all labels
        for label in labels:
            for sport_keyword, sport_name in sport_mapping.items():
                if sport_keyword in label:
                    return sport_name
        
        # Default to General Sports if no specific sport is detected
        return "General Sports"