## Litellm

Building and deploying the litellm application is a two step process

### Base Image Build

The base litellm image Dockerfile.base and all core dependencies are built manually as per dockerfile and instructions in litellm docs
https://docs.litellm.ai/docs/proxy/deploy#build-from-litellm-pip-package

This is pushed to ecr repo litellm in each environment. This needs to be done only once, unless the litellm package version needs to be updated.
The base image is built with packages and dependencies listed in requirements.txt

```
 docker build -f Dockerfile.base -t litellm-base .
```

Follow the AWS docs https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html to build and push the image to ECR base images repo.
Use image tag litellm_base_image, so using base image in Dockerfile from this repo should follow format
`FROM ${ECR_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/<your-ecr-repo>/base_images:litellm_base_image`


### Image Build in CI-CD

The Dockerfile.litellm is uses the base litellm image and copies the config from the folder into the image so its upto date with any changes from the user e.g. new model updates or other features. This is built and pushed with every ci-cd run and tagged with ci-cd commit which is then deployed and run as service in EKS.
