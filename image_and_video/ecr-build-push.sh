#!/bin/bash
# Make this script executable with: chmod +x ecr-build-push.sh

# Exit on error
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
ECR_REPOSITORY=${ECR_REPOSITORY:-"canvas-video"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
ECS_CLUSTER=${ECS_CLUSTER:-"llm-image-app-cluster"}
ECS_SERVICE=${ECS_SERVICE:-"llm-image-app-service"}

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

# Build the Docker image
echo "Building Docker image..."
docker build -t ${ECR_REPOSITORY_URI}:${IMAGE_TAG} .

# Push the Docker image
echo "Pushing Docker image to ECR..."
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Done! Image pushed to ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"

echo "Updating ${ECS_SERVICE} in ${ECS_CLUSTER}"
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --force-new-deployment