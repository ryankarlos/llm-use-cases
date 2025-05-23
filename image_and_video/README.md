# Sports Marketing Video Generator

A Streamlit application that generates sports marketing videos using AWS Bedrock AI models.

## Features

- Sports image classification using Amazon Rekognition
- Sports-specific prompt enhancement for marketing videos
- Video generation with AWS Bedrock Nova Reel
- Image editing with AWS Bedrock Nova Canvas
- Optional Cognito authentication

## Setup

1. Install dependencies:
   ```
   pip install -r app/requirements.txt
   ```

2. Configure AWS credentials:
   ```
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=us-east-1
   ```

3. (Optional) Configure Cognito authentication:
   ```
   export COGNITO_USER_POOL_ID=your_user_pool_id
   export COGNITO_APP_CLIENT_ID=your_app_client_id
   export COGNITO_DOMAIN=your_cognito_domain
   ```

## Running the Application

### Demo Mode (No Authentication)

If Cognito environment variables are not set, the application will run in demo mode without authentication:

```
streamlit run app/main.py
```

### Authenticated Mode

If Cognito environment variables are set, the application will require user authentication:

```
export COGNITO_USER_POOL_ID=your_user_pool_id
export COGNITO_APP_CLIENT_ID=your_app_client_id
export COGNITO_DOMAIN=your_cognito_domain
streamlit run app/main.py
```

## Configuration

You can customize the application behavior using environment variables:

- `AWS_REGION`: AWS region for Bedrock and other services (default: us-east-1)
- `S3_BUCKET`: S3 bucket for storing generated videos (default: nova-reel-videos-demo)
- `POLL_INTERVAL`: Interval in seconds to check video generation status (default: 30)
- `COGNITO_USER_POOL_ID`: Cognito user pool ID for authentication
- `COGNITO_APP_CLIENT_ID`: Cognito app client ID for authentication
- `COGNITO_DOMAIN`: Cognito domain for authentication