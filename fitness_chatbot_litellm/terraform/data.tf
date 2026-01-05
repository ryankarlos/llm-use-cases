data "aws_vpc" "main" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_security_group" "workload_security_group" {
  vpc_id = data.aws_vpc.main.id
  name   = "default"
}
data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_security_group" "endpoint_security_group" {
  vpc_id = data.aws_vpc.main.id
  name   = "endpoints-sg"
}
data "aws_subnets" "workload_subnet" {
  for_each = toset([data.aws_availability_zones.available.names[0], data.aws_availability_zones.available.names[1], data.aws_availability_zones.available.names[2]])
  filter {
    name   = "tag:Name"
    values = ["workload-${each.value}"]
  }
}
data "aws_subnets" "endpoint_subnet" {
  for_each = toset([data.aws_availability_zones.available.names[0], data.aws_availability_zones.available.names[1], data.aws_availability_zones.available.names[2]])
  filter {
    name   = "tag:Name"
    values = ["endpoints-${each.value}"]
  }
}


data "aws_iam_openid_connect_provider" "eks_oidc" {
  url = var.eks_oidc_provider_url
}

data "aws_iam_session_context" "current" {
  arn = data.aws_caller_identity.current.arn
}
