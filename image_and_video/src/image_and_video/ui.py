import streamlit as st
from PIL import Image
import io
from llm import NovaCanvasProcessor, NovaReelProcessor
from sports_classifier import SportsImageClassifier
from config import SPORTS_MARKETING_VIDEOS, DEFAULT_VIDEO_CONFIG
from utils import resize_image

class StreamlitUI:
    """Simplified UI for Sports Marketing Video Generator"""
    
    def __init__(self):
        self.nova_canvas = NovaCanvasProcessor()
        self.nova_reel = NovaReelProcessor()
        self.sports_marketing_videos = SPORTS_MARKETING_VIDEOS
        self.sports_prompt_templates = SPORTS_MARKETING_VIDEOS
        
        # Initialize session state for persistent storage
        if 'processed_image' not in st.session_state:
            st.session_state.processed_image = None
        if 'original_image' not in st.session_state:
            st.session_state.original_image = None
        if 'current_image' not in st.session_state:
            st.session_state.current_image = None
    
    def status_callback(self, status_type, message):
        """Handle status updates"""
        if not hasattr(self, 'status_placeholder'):
            self.status_placeholder = st.empty()
            
        if status_type == "start" or status_type == "progress":
            self.status_placeholder.info(message)
        elif status_type == "complete":
            self.status_placeholder.success("✅ Sports marketing video generated successfully!")
            st.video(message)  # message contains the presigned URL
            st.markdown(f"[Download Sports Marketing Video]({message})")
        elif status_type == "warning":
            self.status_placeholder.warning(message)
        elif status_type == "error":
            self.status_placeholder.error(message)
    
    def run(self):
        """Run the simplified Sports Marketing Video Generator UI"""

        # Apply colorful background and styling with green shades
        st.markdown("""
        <style>
        .main {
            background: linear-gradient(135deg, #1b5e20 0%, #43a047 100%);
            color: white;
        }
        .sidebar .sidebar-content {
            background: linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%);
        }
        .stButton button {
            background-color: #388e3c;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 0.5rem 1rem;
        }
        .stButton button:hover {
            background-color: #2e7d32;
        }
        h1, h2, h3 {
            color: #c8e6c9;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #388e3c;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 20px;
            color: white;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1b5e20;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.title("🏆 Sports Marketing Video Generator 🏆")
        
        # Sidebar configuration
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Image processing options
            st.subheader("Image Processing Options")
            
            # Always show processing options
            main_prompt = st.text_input(
                "Processing prompt:",
                placeholder="Describe what to add/modify"
            )
            mask_prompt = st.text_input(
                "Mask prompt:",
                placeholder="Describe area to modify"
            )
            negative_prompt = st.text_input(
                "Negative prompt:",
                placeholder="What to avoid"
            )
            
            # Video options
            st.subheader("Video Settings")
            
            # Marketing template selection
            marketing_template = st.selectbox(
                "Marketing Video Style:",
                list(self.sports_marketing_videos.keys()),
                format_func=lambda x: x.replace('_', ' ').title()
            )
            
            # Sport type will be automatically detected from the image
            
            # Brand name input
            brand_name = st.text_input("Brand Name (optional)")
            
            # Using default video config instead of showing options
            video_config = DEFAULT_VIDEO_CONFIG
        
        # Main content area
        uploaded_file = st.file_uploader("Upload a sports image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            # Display the uploaded image
            image = Image.open(uploaded_file)
            
            # Convert to bytes for processing
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format=image.format if image.format else 'PNG')
            image_bytes = img_byte_arr.getvalue()
            
            # Resize image to 1280x720
            from utils import resize_image
            image_bytes = resize_image(image_bytes, width=1280, height=720)
            
            # Check if image is sports-related and get sport type
            sports_classifier = SportsImageClassifier()
            is_sports, labels, sport_type = sports_classifier.is_sports_image(image_bytes)
            
            if not is_sports:
                st.error("⚠️ This doesn't appear to be a sports image. Please upload a sports-related image.")
                return
            
            # Display image and detected sports
            col1, col2 = st.columns([1, 1])
            
            # Store the original image in session state
            st.session_state.original_image = image_bytes
            st.session_state.current_image = image_bytes  # Initially set current image to original
            
            # Display the original image in col1
            with col1:
                st.image(image, caption="Uploaded Image", use_column_width=True)
                st.success("✅ Sports image detected!")
                st.write("Detected sports elements: " + ", ".join([label for label in labels 
                                                            if label in " ".join(sports_classifier.sports_keywords)]))
                st.info(f"Detected sport type: {sport_type}")
            
            # Image processing section
            with col2:
                st.subheader("Image Processing")
                
                # Show current processed image if available in session state
                if st.session_state.processed_image:
                    st.image(st.session_state.processed_image, caption="Processed Image", use_column_width=True)
                    st.success("✅ Image processed successfully!")
                    st.info("This processed image will be used for video generation")
                
                # Create two columns for the processing buttons
                process_col1, process_col2 = st.columns(2)
                
                # Only enable processing buttons if prompts are provided
                process_button_disabled = not (main_prompt and mask_prompt)
                
                # Inpainting button
                if process_col1.button("Apply Inpainting", 
                                      disabled=process_button_disabled,
                                      help="Apply inpainting with the provided prompts",
                                      use_container_width=True):
                    if main_prompt and mask_prompt:
                        with st.spinner("Applying inpainting..."):
                            # Ensure image is properly sized to 1280x720 before processing
                            resized_image = resize_image(st.session_state.current_image, width=1280, height=720)
                            
                            # Use resized image for processing
                            processed_result = self.nova_canvas.process(
                                image_bytes=resized_image,
                                negative_prompt=negative_prompt,
                                main_prompt=main_prompt,
                                mask_prompt=mask_prompt,
                                operation_type="INPAINTING"
                            )
                            
                            if processed_result == "NOT_SPORTS_IMAGE":
                                st.error("The image was not recognized as sports-related.")
                            elif processed_result:
                                # Store in session state for persistence
                                st.session_state.processed_image = processed_result
                                st.session_state.current_image = processed_result  # Update current image
                                st.success("✅ Inpainting applied successfully!")
                                # Display the processed image
                                st.image(st.session_state.processed_image, caption="Inpainted Result", use_column_width=True)
                                st.rerun()  # Rerun to update the UI
                            else:
                                st.error("Failed to process the image with inpainting")
                
                # Outpainting button
                if process_col2.button("Apply Outpainting", 
                                      disabled=process_button_disabled,
                                      help="Apply outpainting with the provided prompts",
                                      use_container_width=True):
                    if main_prompt and mask_prompt:
                        with st.spinner("Applying outpainting..."):
                            # Ensure image is properly sized to 1280x720 before processing
                            resized_image = resize_image(st.session_state.current_image, width=1280, height=720)
                            
                            # Use resized image for processing
                            processed_result = self.nova_canvas.process(
                                image_bytes=resized_image,
                                negative_prompt=negative_prompt,
                                main_prompt=main_prompt,
                                mask_prompt=mask_prompt,
                                operation_type="OUTPAINTING"
                            )
                            
                            if processed_result == "NOT_SPORTS_IMAGE":
                                st.error("The image was not recognized as sports-related.")
                            elif processed_result:
                                # Store in session state for persistence
                                st.session_state.processed_image = processed_result
                                st.session_state.current_image = processed_result  # Update current image
                                st.success("✅ Outpainting applied successfully!")
                                # Display the processed image
                                st.image(st.session_state.processed_image, caption="Outpainted Result", use_column_width=True)
                                st.rerun()  # Rerun to update the UI
                            else:
                                st.error("Failed to process the image with outpainting")
                
                # Reset button to go back to original image
                if st.button("Reset to Original Image", use_container_width=True):
                    st.session_state.current_image = st.session_state.original_image
                    st.session_state.processed_image = None
                    st.rerun()  # Rerun to update the UI
            
            # Video generation section
            st.markdown("---")
            st.header("Generate Sports Marketing Video")
            
            # Get base prompt from template
            base_prompt = self.sports_marketing_videos[marketing_template]
            
            # Enhance the prompt with Nova Reel base prompt using detected sport type
            enhanced_prompt = self.nova_reel.enhance_prompt(
                marketing_prompt=base_prompt,
                brand=brand_name,
                sport_type=sport_type
            )
            
            # Show final prompt with option to edit
            with st.expander("Review Final Prompt (Advanced)"):
                final_prompt = st.text_area("Final Marketing Prompt", value=enhanced_prompt, height=100)
            
            # Generate button with clearer label
            if st.button("🎬 Generate Sports Marketing Video with Current Image", use_container_width=True):
                # Use current image for video generation, ensuring it's properly sized to 1280x720
                image_to_use = resize_image(st.session_state.current_image, width=1280, height=720)
                
                # Process with Nova Reel
                with st.spinner("Generating sports marketing video..."):
                    result = self.nova_reel.process(
                        image_bytes=image_to_use,
                        prompt=final_prompt,
                        status_callback=self.status_callback,
                        video_config=video_config
                    )
                    
                    if result == "NOT_SPORTS_IMAGE":
                        st.error("The image was not recognized as sports-related.")
        
        else:
            # Show placeholder when no image is uploaded
            st.info("👆 Upload a sports image to get started")
        
        # Footer
        st.markdown("---")
        st.markdown("Powered by AWS Bedrock Nova Reel and Nova Canvas")