terraform {
   source = "${get_parent_terragrunt_dir()}"
}

remote_state {
  backend = "local"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }
  config = {
    path = "${get_terragrunt_dir()}/terraform.tfstate"
  }
}

locals {
  account_id =  get_aws_account_id()
  region = "us-east-1"
  # Add username and email for Cognito user
  username = "ryan"
  email = "ryankarlos@gmail.com"
  ecr_repo_name = "canvas-video"
}

inputs = {
  hosted_zone_name = "ryannaz-mlops.com"
  ecr_repo_name = local.ecr_repo_name
  image_uri = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${local.ecr_repo_name}"
  bucket_name = "image-llm-example"
  target_group_name = "lb-target"
  region  = local.region
  subdomain = "nova-video"
  tag = {name="llm-image-app"}
  alb_name = "llm-image-app-lb"
  cluster_name = "llm-image-app-cluster"
  service_name = "llm-image-app-service"
  container_name = "llm-image-app-container"
  launch_type = "FARGATE"
  min_capacity = 2
  max_capacity = 4
  desired_count = 2
  task_execution_role_name = "TaskExecutionRole"
  task_role_name = "TaskRole"
  security_group_id = "sg-048d64314bdae5e24"
  vpc_id = "vpc-05c7628a7a70e7e0f"
  subnet_ids = ["subnet-04fd3ba1aa9d56cb0", "subnet-0e165015f85692b36"]
  # Add Cognito user variables
  cognito_username = local.username
  cognito_email = local.email
  cognito_generate_password = true
  cognito_send_email = true
  cognito_user_pool_name = "nova_app_pool"
  cognito_redirect_uri = "https://nova-video.awscommunity.com/"
}