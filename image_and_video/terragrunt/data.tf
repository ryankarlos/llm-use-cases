
data "aws_region" "current" {}


data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_route53_zone" "selected" {
  name         = var.hosted_zone_name
}