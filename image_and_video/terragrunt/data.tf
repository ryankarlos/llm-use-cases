
data "aws_region" "current" {}


data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "main"
  }
}

data "aws_subnets" "default_vpc_subnets" {
  filter {
    name   = "main"
    values = [aws_vpc.main.id]
  }
}

