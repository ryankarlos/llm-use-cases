# Neptune Database for GraphRAG Toolkit lexical-graph
# This creates the graph store required for the lexical graph model

locals {
  neptune_cluster_id = "cv-matcher-neptune-${var.env}"
}

# Neptune Cluster
resource "aws_neptune_cluster" "graphrag" {
  cluster_identifier                  = local.neptune_cluster_id
  engine                              = "neptune"
  engine_version                      = "1.3.1.0"
  backup_retention_period             = 7
  preferred_backup_window             = "02:00-03:00"
  skip_final_snapshot                 = var.env != "prod"
  iam_database_authentication_enabled = true
  storage_encrypted                   = true
  kms_key_arn                         = module.kms_neptune.key_arn

  vpc_security_group_ids = [aws_security_group.neptune.id]
  neptune_subnet_group_name = aws_neptune_subnet_group.graphrag.name

  serverless_v2_scaling_configuration {
    min_capacity = 1.0
    max_capacity = 8.0
  }

  tags = {
    Name        = "cv-matcher-neptune"
    Environment = var.env
    Purpose     = "GraphRAG lexical-graph store"
  }
}

# Neptune Instance (Serverless v2)
resource "aws_neptune_cluster_instance" "graphrag" {
  count              = 1
  cluster_identifier = aws_neptune_cluster.graphrag.id
  instance_class     = "db.serverless"
  engine             = "neptune"

  tags = {
    Name        = "cv-matcher-neptune-instance"
    Environment = var.env
  }
}

# Neptune Subnet Group
resource "aws_neptune_subnet_group" "graphrag" {
  name       = "cv-matcher-neptune-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "cv-matcher-neptune-subnet-group"
    Environment = var.env
  }
}

# Security Group for Neptune
resource "aws_security_group" "neptune" {
  name        = "cv-matcher-neptune-sg"
  description = "Security group for Neptune GraphRAG cluster"
  vpc_id      = var.vpc_id

  ingress {
    description = "Neptune from VPC"
    from_port   = 8182
    to_port     = 8182
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "cv-matcher-neptune-sg"
    Environment = var.env
  }
}

# KMS Key for Neptune encryption
module "kms_neptune" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-kms.git"

  description = "KMS key for Neptune cluster encryption"
  key_usage   = "ENCRYPT_DECRYPT"

  key_administrators = var.allowed_users
  key_users          = var.allowed_users

  aliases = ["cv-matcher-neptune-${var.env}"]

  tags = {
    Environment = var.env
  }
}

# IAM Policy for Neptune access
resource "aws_iam_policy" "neptune_access" {
  name        = "cv-matcher-neptune-access-${var.env}"
  description = "Policy for accessing Neptune GraphRAG cluster"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "neptune-db:connect",
          "neptune-db:ReadDataViaQuery",
          "neptune-db:WriteDataViaQuery",
          "neptune-db:DeleteDataViaQuery",
          "neptune-db:GetQueryStatus",
          "neptune-db:CancelQuery"
        ]
        Resource = "${aws_neptune_cluster.graphrag.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = module.kms_neptune.key_arn
      }
    ]
  })
}

# SSM Parameters for Neptune endpoints
resource "aws_ssm_parameter" "neptune_endpoint" {
  # checkov:skip=CKV2_AWS_34
  name  = "neptune-endpoint-${var.env}"
  type  = "String"
  value = aws_neptune_cluster.graphrag.endpoint
}

resource "aws_ssm_parameter" "neptune_reader_endpoint" {
  # checkov:skip=CKV2_AWS_34
  name  = "neptune-reader-endpoint-${var.env}"
  type  = "String"
  value = aws_neptune_cluster.graphrag.reader_endpoint
}
