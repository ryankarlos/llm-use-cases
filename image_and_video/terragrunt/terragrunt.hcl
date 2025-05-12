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
}

inputs = {
  hosted_zone_name = "ryannaz-mlops.com"
  image_uri = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/canvas-video"
  bucket_name = "image-llm-example"
  target_group_name = "lb-target"
  region  = local.region
  subdomain = "llm-image-app"
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
}
