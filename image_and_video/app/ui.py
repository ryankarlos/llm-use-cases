import streamlit as st
from PIL import Image
import io
from .processors import NovaCanvasProcessor, NovaReelProcessor
from .sports_classifier import SportsImageClassifier
from .config import SPORTS_PROMPT_TEMPLATES

class StreamlitUI:
    """Simplified UI for Sports Marketing Video Generator"""
    
    def __init__(self):
        self.nova_canvas = NovaCanvasProcessor()
        self.nova_reel = NovaReelProcessor()
        self.sports_prompt_templates = SPORTS_PROMPT_TEMPLATES
        self.processed_image = None
    
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
        # Set page config
        st.set_page_config(page_title="Sports Marketing Video Generator", layout="wide")
        
        # Apply colorful background and styling
        st.markdown("""
        <style>
        .main {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
        }
        .stButton button {
            background-color: #FF9900;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            padding: 0.5rem 1rem;
        }
        .stButton button:hover {
            background-color: #FF8000;
        }
        h1, h2, h3 {
            color: #FF9900;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #2a5298;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 20px;
            color: white;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FF9900;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.title("🏆 Sports Marketing Video Generator 🏆")
        
        # Sidebar configuration
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Image processing options
            st.subheader("Image Processing")
            image_processing = st.selectbox(
                "Select image processing option:",
                ["None", "Inpainting", "Outpainting"]
            )
            
            if image_processing != "None":
                st.subheader("Processing Options")
                main_prompt = st.text_input(
                    f"{image_processing} prompt:",
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
                "Marketing Template:",
                list(self.sports_prompt_templates.keys()),
                format_func=lambda x: x.replace('_', ' ').title()
            )
            
            # Video duration
            duration = st.slider("Duration (seconds)", 3, 10, 6)
            
            # Video quality
            quality_options = {
                "Standard (720p)": "1280x720",
                "High (1080p)": "1920x1080"
            }
            quality = st.selectbox("Quality", options=list(quality_options.keys()))
            
            # Create video config
            video_config = {
                "durationSeconds": duration,
                "fps": 24,
                "dimension": quality_options[quality],
                "seed": 0
            }
        
        # Main content area
        uploaded_file = st.file_uploader("Upload a sports image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            # Display the uploaded image
            image = Image.open(uploaded_file)
            
            # Convert to bytes for processing
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format=image.format if image.format else 'PNG')
            image_bytes = img_byte_arr.getvalue()
            
            # Check if image is sports-related
            sports_classifier = SportsImageClassifier()
            is_sports, labels = sports_classifier.is_sports_image(image_bytes)
            
            if not is_sports:
                st.error("⚠️ This doesn't appear to be a sports image. Please upload a sports-related image.")
                return
            
            # Display image and detected sports
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.image(image, caption="Uploaded Image", use_column_width=True)
                st.success("✅ Sports image detected!")
                st.write("Detected sports elements: " + ", ".join([label for label in labels 
                                                                if label in " ".join(sports_classifier.sports_keywords)]))
            
            # Process image if inpainting/outpainting selected
            processed_image_bytes = image_bytes
            
            if image_processing != "None" and main_prompt and mask_prompt:
                with col2:
                    with st.spinner(f"Applying {image_processing.lower()}..."):
                        operation_type = image_processing.upper()
                        processed_image_bytes = self.nova_canvas.process(
                            image_bytes=image_bytes,
                            negative_prompt=negative_prompt,
                            main_prompt=main_prompt,
                            mask_prompt=mask_prompt,
                            operation_type=operation_type
                        )
                        
                        if processed_image_bytes == "NOT_SPORTS_IMAGE":
                            st.error("The image was not recognized as sports-related.")
                        elif processed_image_bytes:
                            st.image(processed_image_bytes, caption=f"After {image_processing}", use_column_width=True)
                            self.processed_image = processed_image_bytes
                        else:
                            st.error(f"Failed to process the image with {image_processing}")
            
            # Video generation section
            st.markdown("---")
            st.header("Generate Sports Marketing Video")
            
            # Get base prompt from template
            base_prompt = self.sports_prompt_templates[marketing_template]
            
            # Customization options in columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                brand_name = st.text_input("Brand Name (optional)")
            
            with col2:
                target_audience = st.selectbox(
                    "Target Audience",
                    ["General Sports Fans", "Young Athletes", "Professional Athletes", 
                     "Fitness Enthusiasts", "Team Supporters"]
                )
            
            with col3:
                cta_options = {
                    "Shop Now": "with a 'Shop Now' call to action",
                    "Learn More": "with a 'Learn More' call to action",
                    "Join Today": "with a 'Join Today' call to action",
                    "Sign Up": "with a 'Sign Up' call to action",
                    "Visit Website": "with a 'Visit Website' call to action"
                }
                cta = st.selectbox("Call to Action", list(cta_options.keys()))
            
            # Build the final prompt
            final_prompt = base_prompt
            if brand_name:
                final_prompt += f" for {brand_name}"
            final_prompt += f" targeting {target_audience.lower()} {cta_options[cta]}"
            
            # Show final prompt with option to edit
            with st.expander("Review and Edit Final Prompt"):
                final_prompt = st.text_area("Final Marketing Prompt", value=final_prompt, height=100)
            
            # Generate button
            if st.button("🎬 Generate Sports Marketing Video", use_container_width=True):
                # Use processed image if available, otherwise use original
                image_to_use = self.processed_image if self.processed_image else image_bytes
                
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