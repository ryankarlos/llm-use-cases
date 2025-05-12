#!/bin/bash
# Make this script executable with: chmod +x ecr-build-push.sh

# Exit on error
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"eu-west-1"}
ECR_REPOSITORY=${ECR_REPOSITORY:-"canvas-video"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ECR repository URI
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo "Building and pushing Docker image to ECR..."
echo "Repository: ${ECR_REPOSITORY_URI}"
echo "Tag: ${IMAGE_TAG}"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Create repository if it doesn't exist
echo "Ensuring repository exists..."
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY} --region ${AWS_REGION} || \
    aws ecr create-repository --repository-name ${ECR_REPOSITORY} --region ${AWS_REGION}

# Build the Docker image
echo "Building Docker image..."
docker build -t ${ECR_REPOSITORY_URI}:${IMAGE_TAG} .

# Push the Docker image
echo "Pushing Docker image to ECR..."
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Done! Image pushed to ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"