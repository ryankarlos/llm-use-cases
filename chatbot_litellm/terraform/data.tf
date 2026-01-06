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

# Get public subnets for all resources (ALB, ECS, Aurora, ElastiCache)
data "aws_subnets" "public_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "tag:Name"
    values = ["*public*"]
  }
}

data "aws_iam_session_context" "current" {
  arn = data.aws_caller_identity.current.arn
}
