# Lambda function for CV Matcher API with GraphRAG (using Function URL instead of API Gateway)

locals {
  lambda_name = "cv-matcher-api-${var.env}"
}

# ECR Repository for Lambda container
resource "aws_ecr_repository" "cv_matcher" {
  name                 = "cv-matcher-api-${var.env}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "cv-matcher-api"
    Environment = var.env
  }
}

# Null resource to build and push initial image
resource "null_resource" "docker_build" {
  depends_on = [aws_ecr_repository.cv_matcher]

  triggers = {
    handler_hash = filemd5("${path.module}/../lambda/handler.py")
    docker_hash  = filemd5("${path.module}/../lambda/Dockerfile")
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/../lambda"
    command     = <<-EOT
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com
      docker build -t cv-matcher-api-${var.env}:latest .
      docker tag cv-matcher-api-${var.env}:latest ${aws_ecr_repository.cv_matcher.repository_url}:latest
      docker push ${aws_ecr_repository.cv_matcher.repository_url}:latest
    EOT
  }
}

# Lambda function (container-based for GraphRAG dependencies)
resource "aws_lambda_function" "cv_matcher" {
  function_name = local.lambda_name
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.cv_matcher.repository_url}:latest"
  timeout       = 60
  memory_size   = 1024

  environment {
    variables = {
      NEPTUNE_ENDPOINT    = aws_neptune_cluster.graphrag.endpoint
      OPENSEARCH_ENDPOINT = aws_opensearchserverless_collection.vectors.collection_endpoint
      AWS_REGION_NAME     = var.aws_region
    }
  }

  # VPC config for Neptune access
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = {
    Name        = local.lambda_name
    Environment = var.env
  }

  depends_on = [null_resource.docker_build]

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# Lambda Function URL (replaces API Gateway)
resource "aws_lambda_function_url" "cv_matcher" {
  function_name      = aws_lambda_function.cv_matcher.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
    max_age       = 300
  }
}

# Security group for Lambda
resource "aws_security_group" "lambda" {
  name        = "${local.lambda_name}-sg"
  description = "Security group for CV Matcher Lambda"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${local.lambda_name}-sg"
    Environment = var.env
  }
}

# Allow Lambda to access Neptune
resource "aws_security_group_rule" "neptune_from_lambda" {
  type                     = "ingress"
  from_port                = 8182
  to_port                  = 8182
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lambda.id
  security_group_id        = aws_security_group.neptune.id
}

# Lambda IAM role
resource "aws_iam_role" "lambda_role" {
  name = "${local.lambda_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Lambda basic execution + VPC access
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda policy for Neptune, OpenSearch, and Bedrock
resource "aws_iam_role_policy" "lambda_services" {
  name = "${local.lambda_name}-services"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["neptune-db:*"]
        Resource = "${aws_neptune_cluster.graphrag.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["aoss:APIAccessAll"]
        Resource = aws_opensearchserverless_collection.vectors.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}
