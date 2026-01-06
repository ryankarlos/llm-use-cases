# NHS Patient Booking Demo - Simplified Infrastructure
# No VPC endpoints, minimal resources for demo/blog

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket for demo files (audio, etc.)
resource "aws_s3_bucket" "demo" {
  bucket        = "${var.project_name}-demo-${data.aws_caller_identity.current.account_id}"
  force_destroy = true  # Allow easy cleanup for demo
}

# DynamoDB for sessions - simple, on-demand
resource "aws_dynamodb_table" "sessions" {
  name         = "${var.project_name}-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# DynamoDB for bookings
resource "aws_dynamodb_table" "bookings" {
  name         = "${var.project_name}-bookings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "booking_id"

  attribute {
    name = "booking_id"
    type = "S"
  }
}

# Lambda for agent actions with X-Ray tracing
resource "aws_lambda_function" "actions" {
  function_name = "${var.project_name}-actions"
  role          = aws_iam_role.lambda.arn
  handler       = "lambda_actions.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      BOOKINGS_TABLE = aws_dynamodb_table.bookings.name
      SESSIONS_TABLE = aws_dynamodb_table.sessions.name
    }
  }
}

# Lambda alias for versioning
resource "aws_lambda_alias" "actions_live" {
  name             = "live"
  function_name    = aws_lambda_function.actions.function_name
  function_version = "$LATEST"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# X-Ray tracing permissions
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-dynamodb"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ]
      Resource = [
        aws_dynamodb_table.sessions.arn,
        aws_dynamodb_table.bookings.arn
      ]
    }]
  })
}

# Amazon Location Service permissions for hospital search
resource "aws_iam_role_policy" "lambda_location" {
  name = "${var.project_name}-lambda-location"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "geo:SearchPlaceIndexForText",
        "geo:SearchPlaceIndexForPosition",
        "geo-places:Geocode",
        "geo-places:SearchNearby",
        "geo-places:SearchText"
      ]
      Resource = "*"
    }]
  })
}

# Lambda permission for Bedrock Agent
resource "aws_lambda_permission" "bedrock" {
  statement_id  = "AllowBedrock"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.actions.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
}

# IAM role for Bedrock Agent
resource "aws_iam_role" "bedrock_agent" {
  name = "${var.project_name}-bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_agent" {
  name = "${var.project_name}-bedrock-agent-policy"
  role = aws_iam_role.bedrock_agent.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*",
          "arn:aws:bedrock:us-east-1::foundation-model/*",
          "arn:aws:bedrock:us-west-2::foundation-model/*"
        ]
      },
      {
        # Cross-region inference profiles for Nova Premier
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/*"
      },
      {
        # Web Grounding system tool
        Effect   = "Allow"
        Action   = ["bedrock:InvokeTool"]
        Resource = "arn:aws:bedrock:*:*:system-tool/amazon.nova_grounding"
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.actions.arn
      }
    ]
  })
}

# Lambda code archive
data "archive_file" "lambda" {
  type        = "zip"
  output_path = "${path.module}/.terraform/lambda.zip"

  source {
    content  = file("${path.module}/../src/lambda_actions.py")
    filename = "lambda_actions.py"
  }
}
