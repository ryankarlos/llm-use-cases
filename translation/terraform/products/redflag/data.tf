
data "aws_vpc" "main" {}


data "aws_security_group" "workload_security_group" {
  name = "default"
}
data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_security_group" "endpoint_security_group" {
  name = "endpoints-sg"
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
