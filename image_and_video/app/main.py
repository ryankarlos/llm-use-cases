import streamlit as st
import boto3
import base64
import json
import os
from PIL import Image
import io
import time

# Configure AWS credentials from environment variables
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.getenv("AWS_REGION", "us-east-1")
)


def generate_image(prompt, negative_prompt="", seed=None):
    """Generate image using Amazon Nova Canvas"""
    try:
        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "negativeText": negative_prompt
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "cfgScale": 8.0,
                "seed": seed if seed else int(time.time())
            }
        }

        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-canvas-v1:0",
            body=json.dumps(body)
        )

        response_body = json.loads(response['body'].read())
        image_data = base64.b64decode(response_body['images'][0])

        return Image.open(io.BytesIO(image_data))

    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None


def generate_video(prompt, image_base64):
    """Generate video using Amazon Nova Reel"""
    try:
        body = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": prompt,
                "images": [{
                    "format": "png",
                    "source": {
                        "bytes": image_base64
                    }
                }]
            },
            "videoGenerationConfig": {
                "duration": 6,
                "fps": 24,
                "dimension": {
                    "width": 1280,
                    "height": 720
                }
            }
        }

        invocation = bedrock_runtime.start_async_invoke(
            modelId="amazon.nova-reel-v1:1",
            modelInput=body,
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": f"s3://nova-reel-videos-demo"}}
        )

        invocation_arn = invocation["invocationArn"]
        s3_prefix = invocation_arn.split('/')[-1]
        s3_location = f"s3://nova-reel-videos-demo/{s3_prefix}"
        print(f"\nS3 URI: {s3_location}")

        while True:
            response = bedrock_runtime.get_async_invoke(
                invocationArn=invocation_arn
            )
            status = response["status"]
            st.info(f"Status: {status}")
            if status != "InProgress":
                break
            time.sleep(30)

        if status == "Completed":
            st.info(f"\nVideo is ready at {s3_location}/output.mp4")
        else:
            st.info(f"\nVideo generation status: {status}")

        return json.loads(response['body'].read())

    except Exception as e:
        st.error(f"Error generating video: {str(e)}")
        return None


def main():
    st.title("Ad Content Generator using Amazon Nova")
    st.write("Generate custom images and videos for your advertisements")

    # Image Generation Section
    st.header("1. Generate Image")

    image_prompt = st.text_area(
        "Enter image prompt:",
        placeholder="Example: A modern minimalist living room with sleek furniture"
    )

    negative_prompt = st.text_area(
        "Enter negative prompt (optional):",
        placeholder="Example: blurry, low quality, distorted"
    )

    seed = st.number_input("Seed (optional)", min_value=0, value=None)

    if st.button("Generate Image"):
        if image_prompt:
            with st.spinner("Generating image..."):
                generated_image = generate_image(image_prompt, negative_prompt, seed)
                if generated_image:
                    st.session_state['generated_image'] = generated_image
                    st.image(generated_image, caption="Generated Image")
        else:
            st.warning("Please enter an image prompt")

    # Video Generation Section
    st.header("2. Convert to Video")

    if 'generated_image' in st.session_state:
        video_prompt = st.text_area(
            "Enter video prompt:",
            placeholder="Example: Dolly zoom into the living room, focusing on the modern furniture"
        )

        if st.button("Generate Video"):
            if video_prompt:
                with st.spinner("Generating video... This may take a few minutes"):
                    # Convert image to base64
                    buffered = io.BytesIO()
                    st.session_state['generated_image'].save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode()

                    # Generate video
                    video_response = generate_video(video_prompt, img_base64)

                    if video_response:
                        st.success("Video generated successfully!")
                        # Display video details or download link
                        st.json(video_response)
            else:
                st.warning("Please enter a video prompt")
    else:
        st.info("Generate an image first before creating a video")


if __name__ == "__main__":
    st.set_page_config(page_title="Ad Content Generator", layout="wide")
    main()
