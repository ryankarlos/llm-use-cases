import os
import uuid
import boto3
from PIL import Image, ImageDraw, ImageFont
import io


def save_uploaded_file(uploaded_file, file_type="image"):
    """
    Save an uploaded file to a temporary location
    
    Args:
        uploaded_file: Streamlit uploaded file object
        file_type (str): Type of file (image, music, etc.)
        
    Returns:
        str: Path to the saved file
    """
    # Create temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)
    os.makedirs(f"temp/{file_type}s", exist_ok=True)
    
    # Generate unique filename
    filename = f"{file_type}_{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
    file_path = os.path.join("temp", f"{file_type}s", filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path


def get_s3_url(file_path):
    """
    Get the S3 URL for a file
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: S3 URL of the file
    """
    # In a production environment, this would return the actual S3 URL
    # For now, we'll return a placeholder URL
    return f"https://canvas-video-example.s3.amazonaws.com/{os.path.basename(file_path)}"


def delete_s3_object(s3_url):
    """
    Delete an object from S3
    
    Args:
        s3_url (str): S3 URL of the object to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse bucket name and key from S3 URL
        parts = s3_url.replace("https://", "").split("/")
        bucket_name = parts[0].split(".")[0]
        key = "/".join(parts[1:])
        
        # Initialize S3 client
        s3_client = boto3.client("s3")
        
        # Delete object
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        
        return True
    except Exception as e:
        print(f"Error deleting S3 object: {e}")
        return False


def add_text_to_image(image_path, text, position="bottom", text_color="#FFFFFF"):
    """
    Add text overlay to an image
    
    Args:
        image_path (str): Path to the image
        text (str): Text to add
        position (str): Position of the text (top, center, bottom)
        text_color (str): Color of the text
        
    Returns:
        str: Path to the modified image
    """
    try:
        # Open the image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Calculate text position
        width, height = image.size
        
        # Try to load a font, use default if not available
        try:
            font = ImageFont.truetype("arial.ttf", size=int(height/20))
        except:
            font = ImageFont.load_default()
        
        # Calculate text size
        text_width, text_height = draw.textsize(text, font=font)
        
        # Calculate text position based on specified position
        if position.lower() == "top":
            text_position = ((width - text_width) / 2, height * 0.1)
        elif position.lower() == "center":
            text_position = ((width - text_width) / 2, (height - text_height) / 2)
        else:  # bottom
            text_position = ((width - text_width) / 2, height * 0.9 - text_height)
        
        # Add text shadow for better visibility
        shadow_offset = int(height/200)
        draw.text((text_position[0] + shadow_offset, text_position[1] + shadow_offset), 
                 text, fill="#000000", font=font)
        
        # Add text
        draw.text(text_position, text, fill=text_color, font=font)
        
        # Save modified image
        output_path = image_path.replace(".", "_text.")
        image.save(output_path)
        
        return output_path
    
    except Exception as e:
        print(f"Error adding text to image: {e}")
        return image_path


def add_logo_to_image(image_path, logo_path, position="bottom-right"):
    """
    Add a logo to an image
    
    Args:
        image_path (str): Path to the image
        logo_path (str): Path to the logo
        position (str): Position of the logo (top-left, top-right, bottom-left, bottom-right)
        
    Returns:
        str: Path to the modified image
    """
    try:
        # Open the image and logo
        image = Image.open(image_path)
        logo = Image.open(logo_path)
        
        # Resize logo to be proportional to the image (max 10% of image width)
        width, height = image.size
        max_logo_width = int(width * 0.1)
        logo_width, logo_height = logo.size
        
        if logo_width > max_logo_width:
            ratio = max_logo_width / logo_width
            logo = logo.resize((max_logo_width, int(logo_height * ratio)), Image.LANCZOS)
        
        # Calculate logo position
        logo_width, logo_height = logo.size
        padding = int(width * 0.02)  # 2% padding
        
        if position.lower() == "top-left":
            logo_position = (padding, padding)
        elif position.lower() == "top-right":
            logo_position = (width - logo_width - padding, padding)
        elif position.lower() == "bottom-left":
            logo_position = (padding, height - logo_height - padding)
        else:  # bottom-right
            logo_position = (width - logo_width - padding, height - logo_height - padding)
        
        # Paste logo onto image (handling transparency)
        if logo.mode == 'RGBA':
            image.paste(logo, logo_position, logo)
        else:
            image.paste(logo, logo_position)
        
        # Save modified image
        output_path = image_path.replace(".", "_logo.")
        image.save(output_path)
        
        return output_path
    
    except Exception as e:
        print(f"Error adding logo to image: {e}")
        return image_path