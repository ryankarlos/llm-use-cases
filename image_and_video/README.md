# Canvas Video - AI-Powered Image Generation and Video Advertisement Creation

Canvas Video is a secure, AWS-based application that helps users generate special images using Amazon Canvas and convert them to video advertisements. It provides a user-friendly interface for creating professional-quality video content with minimal effort.

The application allows users to:
1. Generate custom images using Amazon Canvas's AI image generation capabilities
2. Customize generated images with text, logos, and other branding elements
3. Convert static images into dynamic video advertisements
4. Export videos in various formats suitable for different platforms

Built with Streamlit and deployed on AWS ECS, Canvas Video offers a user-friendly interface while maintaining enterprise-grade security and scalability. The system leverages AWS services like Amazon Bedrock for image generation, AWS Elemental MediaConvert for video processing, and Amazon S3 for storage.

## Repository Structure
```
.
├── app/                           # Core application code
│   ├── canvas.py                 # Amazon Canvas integration for image generation
│   ├── video.py                  # Video conversion functionality
│   ├── streamlit_app.py          # Main Streamlit application interface
│   ├── utils.py                  # Utility functions
│   └── requirements.txt          # Python dependencies for the application
├── terraform/                     # Infrastructure as Code
│   └── products/canvas-video/    # Terraform configurations for AWS deployment
├── Dockerfile                    # Container definition for application deployment
├── ecr-build-push.sh            # Script for building and pushing to AWS ECR
└── requirements.txt             # Development dependencies
```

## Usage Instructions
### Prerequisites
- AWS Account with access to:
  - AWS Bedrock
  - Amazon Canvas
  - AWS Elemental MediaConvert
  - AWS Cognito
  - AWS ECR
  - AWS ECS
  - AWS S3
  - AWS Route 53
- Docker installed locally
- AWS CLI configured with appropriate credentials
- Terraform >= 0.14
- Python 3.12+

### Installation

#### Local Development
```bash
# Clone the repository
git clone <repository-url>
cd canvas-video

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -r app/requirements.txt

# Set required environment variables
export POOL_ID="your-cognito-pool-id"
export APP_CLIENT_ID="your-cognito-client-id"
export APP_CLIENT_SECRET="your-cognito-client-secret"
export AWS_REGION="your-aws-region"

# Run the application locally
cd app
streamlit run streamlit_app.py
```

#### Docker Deployment
```bash
# Build and push to ECR
./ecr-build-push.sh
```

### Quick Start
1. Access the Canvas Video web interface
2. Log in using your Cognito credentials
3. Choose "Create New Image" to generate an image using Amazon Canvas
4. Customize your image with text, logos, and other elements
5. Convert your image to a video advertisement
6. Download or share your video

## Data Flow
Canvas Video processes images and creates videos through a secure, multi-stage pipeline:

```ascii
User Request → Cognito Auth → Streamlit Frontend → Image Generation (Canvas)
     ↓                                                    ↓
Video Processing ←────────── Image Customization ←──── Image Storage (S3)
     ↓
Final Video → S3 Storage → Streamlit Frontend → User Download/Share
```

## Infrastructure

### Compute Resources
- ECS Cluster for application hosting
- Fargate tasks for serverless container execution
- Application Load Balancer for traffic distribution

### Security
- Cognito User Pool for authentication
- Private VPC endpoints for AWS services
- ACM certificates for TLS termination

### Storage
- S3 buckets for image and video storage
- ECR for container images
- CloudWatch for logging

### Media Processing
- AWS Elemental MediaConvert for video creation
- Amazon Bedrock for AI image generation

## Deployment

The deployment process is fully automated through CI/CD pipelines:

1. Validation Stage
```yaml
# Automated checks run on merge requests and main branch pushes
- Python code formatting (black)
- Python linting (ruff)
- Terragrunt validation
- Infrastructure security scanning (Checkov)
```

2. Build Stage
```yaml
# Automated Docker image build and push to ECR
- Builds application container
- Tags with environment-specific version
- Pushes to AWS ECR repository
```

3. Deployment Stages
```yaml
# Infrastructure deployment through Terragrunt
- Plan stage generates and validates infrastructure changes
- Apply stage (manual trigger) deploys to target environment
- Supports multiple environments (dev, prod)
```