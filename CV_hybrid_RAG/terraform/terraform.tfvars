env        = "dev"
aws_region = "us-east-1"

# OpenSearch Serverless
allow_public_access = true
vpc_endpoint_ids    = []
allowed_principals  = ["arn:aws:iam::376337229415:user/ryankarlos"]

# Neptune (VPC settings)
vpc_id             = "vpc-05c7628a7a70e7e0f"
vpc_cidr           = "10.0.0.0/16"
private_subnet_ids = ["subnet-04fd3ba1aa9d56cb0", "subnet-0d52c6f2a1e754f4e"]
allowed_users      = ["arn:aws:iam::376337229415:user/ryankarlos"]
