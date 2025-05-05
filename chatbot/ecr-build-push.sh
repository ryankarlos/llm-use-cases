#!/bin/bash

# Exit on any error
set -e

# Set defaults if not provided
IMAGE_TAG=${IMAGE_TAG:-latest}
AWS_REGION=${AWS_REGION:-"eu-west-1"}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-"345594580133"}
ECR_REPO_NAME=${ECR_REPO_NAME:-"dsai/prometheus"}

# ECR Repository URL
ECR_REPO_URL=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
FULL_IMAGE_NAME=$ECR_REPO_URL/$ECR_REPO_NAME:$IMAGE_TAG

echo "=== Starting ECR Authentication and Image Push Process ==="

# Authenticate to ECR
echo "Authenticating to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REPO_URL

# Create repository if it doesn't exist
echo "Ensuring repository exists..."
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION

# Build Docker image
echo "Building Docker image..."
docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

# Tag the image
echo "Tagging image..."
docker tag $ECR_REPO_NAME:$IMAGE_TAG $FULL_IMAGE_NAME

# Push to ECR
echo "Pushing image to ECR..."
docker push $FULL_IMAGE_NAME

echo "=== Process completed successfully ==="
echo "Image pushed to: $FULL_IMAGE_NAME"
