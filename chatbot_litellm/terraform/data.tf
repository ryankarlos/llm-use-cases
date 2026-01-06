data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_security_group" "workload_security_group" {
  vpc_id = data.aws_vpc.main.id
  name   = "default"
}

data "aws_availability_zones" "available" {
  state = "available"
}

# Get public subnets with Internet Gateway for ECS/ALB
data "aws_subnets" "public_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "subnet-id"
    values = ["subnet-0e165015f85692b36", "subnet-04fd3ba1aa9d56cb0"]
  }
}

# Keep existing subnets for Aurora/ElastiCache (can't be changed while in use)
locals {
  database_subnet_ids = ["subnet-0b84a76c5e30c472a", "subnet-0d52c6f2a1e754f4e"]
}

data "aws_iam_session_context" "current" {
  arn = data.aws_caller_identity.current.arn
}
