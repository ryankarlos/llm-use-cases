# Environment
variable "env" {
  type        = string
  description = "Environment name (dev, staging, prod)"
  default     = "dev"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

# OpenSearch Serverless
variable "allow_public_access" {
  type        = bool
  description = "Allow public access to OpenSearch collection"
  default     = true
}

variable "vpc_endpoint_ids" {
  type        = list(string)
  description = "VPC endpoint IDs for private access (if allow_public_access is false)"
  default     = []
}

variable "allowed_principals" {
  type        = list(string)
  description = "IAM principals allowed to access the collection"
}

# Neptune
variable "vpc_id" {
  type        = string
  description = "VPC ID for Neptune cluster"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "List of private subnet IDs for Neptune"
}

variable "allowed_users" {
  type        = list(string)
  description = "IAM users allowed to administer KMS keys"
}
