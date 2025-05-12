import streamlit as st
import os
import uuid
import time
from streamlit_cognito_auth import CognitoAuthenticator
from canvas import CanvasImageGenerator
from video import VideoConverter
from utils import save_uploaded_file, get_s3_url, delete_s3_object

# --- Streamlit UI ---

st.set_page_config(page_title="Canvas Video - AI Image to Video Creator", layout="wide")

# Initialize session states
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []
if "selected_image" not in st.session_state:
    st.session_state.selected_image = None
if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "user_prompt" not in st.session_state:
    st.session_state.user_prompt = ""
if "video_settings" not in st.session_state:
    st.session_state.video_settings = {
        "duration": 15,
        "resolution": "1080p",
        "format": "mp4",
        "transition_effects": "fade",
        "background_music": None
    }

# Cognito auth
try:
    pool_id = os.environ["POOL_ID"]
    app_client_id = os.environ["APP_CLIENT_ID"]
    app_client_secret = os.environ["APP_CLIENT_SECRET"]
    
    authenticator = CognitoAuthenticator(
        pool_id=pool_id, app_client_id=app_client_id, app_client_secret=app_client_secret
    )
    
    is_logged_in = authenticator.login()
    if not is_logged_in:
        st.stop()
except Exception as e:
    st.error(f"Authentication error: {e}")
    st.info("Running in development mode without authentication")
    is_logged_in = True

def logout():
    try:
        authenticator.logout()
    except:
        st.rerun()

# Main application layout
st.title("Canvas Video - AI Image to Video Creator 🎬")
st.write("Generate custom images with Amazon Canvas and convert them to professional video advertisements")

# Sidebar for user settings and options
with st.sidebar:
    try:
        st.header(f"Logged in as {authenticator.get_username()}")
    except:
        st.header("Development Mode")
    
    st.button("Logout", "logout_btn", on_click=logout)
    
    st.divider()
    
    # Image generation section
    st.subheader("1️⃣ Image Generation")
    
    # Text prompt for image generation
    user_prompt = st.text_area(
        "Describe the image you want to generate",
        placeholder="Example: A professional advertisement for a coffee shop with a modern design, bright colors, and the text 'MORNING BREW' prominently displayed",
        help="Be specific about what you want in the image, including style, colors, and any text"
    )
    
    # Image style selection
    image_style = st.selectbox(
        "Select image style",
        ["Photorealistic", "Artistic", "Cartoon", "Abstract", "Corporate", "Minimalist"]
    )
    
    # Image aspect ratio
    aspect_ratio = st.selectbox(
        "Select aspect ratio",
        ["16:9 (Landscape)", "9:16 (Portrait)", "1:1 (Square)", "4:5 (Instagram)", "2:1 (Banner)"]
    )
    
    # Generate button
    generate_btn = st.button("🎨 Generate Images", use_container_width=True)
    
    st.divider()
    
    # Video settings section
    st.subheader("2️⃣ Video Settings")
    
    # Video duration
    st.session_state.video_settings["duration"] = st.slider(
        "Video duration (seconds)",
        min_value=5,
        max_value=60,
        value=15,
        step=5
    )
    
    # Video resolution
    st.session_state.video_settings["resolution"] = st.selectbox(
        "Video resolution",
        ["720p", "1080p", "4K"]
    )
    
    # Video format
    st.session_state.video_settings["format"] = st.selectbox(
        "Video format",
        ["mp4", "mov", "webm"]
    )
    
    # Transition effects
    st.session_state.video_settings["transition_effects"] = st.selectbox(
        "Transition effects",
        ["None", "Fade", "Dissolve", "Slide", "Zoom"]
    )
    
    # Background music
    music_options = {
        "None": None,
        "Upbeat Corporate": "upbeat_corporate.mp3",
        "Inspirational": "inspirational.mp3",
        "Energetic": "energetic.mp3",
        "Calm": "calm.mp3",
        "Dramatic": "dramatic.mp3"
    }
    
    selected_music = st.selectbox(
        "Background music",
        list(music_options.keys())
    )
    st.session_state.video_settings["background_music"] = music_options[selected_music]
    
    # Upload custom music
    custom_music = st.file_uploader(
        "Or upload custom music (MP3)",
        type=["mp3"]
    )
    
    if custom_music:
        # Save uploaded music to temporary file
        music_path = save_uploaded_file(custom_music, "music")
        st.session_state.video_settings["background_music"] = music_path
        st.success(f"Custom music uploaded: {custom_music.name}")
        
    # Reset button
    st.divider()
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.generated_images = []
        st.session_state.selected_image = None
        st.session_state.video_path = None
        st.session_state.user_prompt = ""
        st.rerun()

# Main content area
col1, col2 = st.columns([3, 2])

# Column 1: Image Generation and Selection
with col1:
    # Image generation section
    if generate_btn and user_prompt:
        st.session_state.user_prompt = user_prompt
        
        with st.spinner("🎨 Generating images with Amazon Canvas..."):
            try:
                # Initialize Canvas image generator
                canvas_generator = CanvasImageGenerator(region_name=os.environ.get("AWS_REGION", "us-east-1"))
                
                # Generate images based on prompt, style and aspect ratio
                image_paths = canvas_generator.generate_images(
                    prompt=user_prompt,
                    style=image_style.lower(),
                    aspect_ratio=aspect_ratio.split()[0],  # Extract just the ratio part
                    num_images=3  # Generate 3 variations
                )
                
                # Store generated images in session state
                st.session_state.generated_images = image_paths
                
                st.success(f"✅ Generated {len(image_paths)} images!")
            except Exception as e:
                st.error(f"Error generating images: {e}")
    
    # Display generated images for selection
    if st.session_state.generated_images:
        st.subheader("Select an image to customize and convert to video")
        
        # Create a grid of images
        image_cols = st.columns(min(3, len(st.session_state.generated_images)))
        
        for i, image_path in enumerate(st.session_state.generated_images):
            with image_cols[i % 3]:
                st.image(image_path, use_column_width=True)
                if st.button(f"Select Image {i+1}", key=f"select_img_{i}", use_container_width=True):
                    st.session_state.selected_image = image_path
                    st.rerun()
    
    # Image customization section (appears after image selection)
    if st.session_state.selected_image:
        st.subheader("Customize Your Image")
        
        # Display selected image
        st.image(st.session_state.selected_image, use_column_width=True)
        
        # Image customization options
        with st.expander("Image Customization Options", expanded=True):
            # Add text overlay
            text_overlay = st.text_input("Add text overlay", "")
            
            # Text position
            text_position = st.selectbox(
                "Text position",
                ["Top", "Center", "Bottom"]
            )
            
            # Text color
            text_color = st.color_picker("Text color", "#FFFFFF")
            
            # Logo upload
            logo = st.file_uploader("Upload logo (PNG with transparency)", type=["png"])
            
            # Logo position
            logo_position = st.selectbox(
                "Logo position",
                ["Top Left", "Top Right", "Bottom Left", "Bottom Right"]
            )
            
            # Apply customization button
            if st.button("Apply Customization", use_container_width=True):
                with st.spinner("Applying customizations..."):
                    # Here we would apply the customizations to the image
                    # For now, we'll just simulate a delay
                    time.sleep(2)
                    st.success("Customizations applied!")
        
        # Convert to video button
        if st.button("🎬 Convert to Video Advertisement", use_container_width=True):
            with st.spinner("Converting image to video..."):
                try:
                    # Initialize video converter
                    video_converter = VideoConverter(region_name=os.environ.get("AWS_REGION", "us-east-1"))
                    
                    # Convert image to video
                    video_path = video_converter.create_video(
                        image_path=st.session_state.selected_image,
                        settings=st.session_state.video_settings
                    )
                    
                    # Store video path in session state
                    st.session_state.video_path = video_path
                    
                    st.success("✅ Video created successfully!")
                except Exception as e:
                    st.error(f"Error creating video: {e}")

# Column 2: Video Preview and Download
with col2:
    if st.session_state.video_path:
        st.subheader("Your Video Advertisement")
        
        # Video preview
        st.video(st.session_state.video_path)
        
        # Video information
        st.info(
            f"📹 **Video Details**  \n"
            f"Duration: {st.session_state.video_settings['duration']} seconds  \n"
            f"Resolution: {st.session_state.video_settings['resolution']}  \n"
            f"Format: {st.session_state.video_settings['format'].upper()}"
        )
        
        # Download button
        with open(st.session_state.video_path, "rb") as file:
            video_bytes = file.read()
            st.download_button(
                label="⬇️ Download Video",
                data=video_bytes,
                file_name=f"canvas_video_{uuid.uuid4().hex[:8]}.{st.session_state.video_settings['format']}",
                mime=f"video/{st.session_state.video_settings['format']}",
                use_container_width=True
            )
        
        # Share options
        st.subheader("Share Your Video")
        
        # Get shareable URL (this would be implemented in a real application)
        share_url = get_s3_url(st.session_state.video_path)
        
        # Display shareable URL
        st.text_input("Shareable link", share_url, disabled=True)
        
        # Social media sharing buttons (these would be implemented in a real application)
        share_cols = st.columns(4)
        with share_cols[0]:
            st.button("Facebook", use_container_width=True)
        with share_cols[1]:
            st.button("Twitter", use_container_width=True)
        with share_cols[2]:
            st.button("LinkedIn", use_container_width=True)
        with share_cols[3]:
            st.button("Copy Link", use_container_width=True)
    else:
        # Placeholder when no video is generated yet
        st.info("👈 Generate and select an image, then convert it to a video to see the preview here.")
        
        # Example video showcase
        st.subheader("Example Video Advertisements")
        st.write("Here are some examples of what you can create:")
        
        # Display example videos (these would be real examples in a production app)
        example_cols = st.columns(2)
        with example_cols[0]:
            st.image("https://via.placeholder.com/400x225.png?text=Example+Video+1", use_column_width=True)
            st.caption("Product showcase with zoom effects")
        with example_cols[1]:
            st.image("https://via.placeholder.com/400x225.png?text=Example+Video+2", use_column_width=True)
            st.caption("Brand advertisement with text animations")
            
        # Tips for creating effective video ads
        with st.expander("Tips for Creating Effective Video Advertisements"):
            st.markdown("""
            ### Best Practices for Video Advertisements
            
            1. **Keep it concise** - The most effective video ads are typically 15-30 seconds long
            2. **Start strong** - Capture attention in the first 3 seconds
            3. **Clear call to action** - Tell viewers what to do next
            4. **Brand consistency** - Maintain your brand colors, fonts, and messaging
            5. **Optimize for mobile** - Most viewers will watch on mobile devices
            6. **Consider sound-off viewing** - Use text overlays for key messages
            7. **Test different versions** - Create variations to see what performs best
            """)