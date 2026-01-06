# Amazon Lex V2 Bot for Q&A Assistant
# This bot forwards all queries to LiteLLM via Lambda fulfillment

# IAM Role for Lex Bot
resource "aws_iam_role" "lex_bot_role" {
  name = "lex-qa-assistant-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lexv2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

resource "aws_iam_role_policy" "lex_bot_policy" {
  name = "lex-qa-assistant-policy"
  role = aws_iam_role.lex_bot_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lex V2 Bot
resource "aws_lexv2models_bot" "qa_assistant" {
  name        = "QAAssistant"
  description = "General Q&A chatbot powered by LiteLLM and AWS Bedrock"
  role_arn    = aws_iam_role.lex_bot_role.arn

  data_privacy {
    child_directed = false
  }

  idle_session_ttl_in_seconds = 300

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}


# Bot Locale (English US)
resource "aws_lexv2models_bot_locale" "en_us" {
  bot_id                           = aws_lexv2models_bot.qa_assistant.id
  bot_version                      = "DRAFT"
  locale_id                        = "en_US"
  n_lu_intent_confidence_threshold = 0.40

  voice_settings {
    voice_id = "Joanna"
    engine   = "neural"
  }
}

# QA Intent - forwards queries to LLM
resource "aws_lexv2models_intent" "qa_intent" {
  bot_id      = aws_lexv2models_bot.qa_assistant.id
  bot_version = aws_lexv2models_bot_locale.en_us.bot_version
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id
  name        = "QAIntent"
  description = "Intent that forwards queries to LiteLLM"

  sample_utterance {
    utterance = "help me with something"
  }
  sample_utterance {
    utterance = "I have a question"
  }
  sample_utterance {
    utterance = "tell me about something"
  }
  sample_utterance {
    utterance = "what is this"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# Bot Version (created after locale and intents are configured)
resource "aws_lexv2models_bot_version" "qa_assistant_v1" {
  bot_id = aws_lexv2models_bot.qa_assistant.id

  locale_specification = {
    (aws_lexv2models_bot_locale.en_us.locale_id) = {
      source_bot_version = "DRAFT"
    }
  }

  depends_on = [
    aws_lexv2models_intent.qa_intent
  ]
}

# Lambda permission for Lex to invoke the fulfillment function
# Uses the TestBotAlias which is automatically created for DRAFT version
resource "aws_lambda_permission" "lex_invoke" {
  statement_id  = "AllowLexInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lex_fulfillment.function_name
  principal     = "lexv2.amazonaws.com"
  source_arn    = "${aws_lexv2models_bot.qa_assistant.arn}/*"
}


# =============================================================================
# Lambda Fulfillment Function for Lex Bot
# =============================================================================

# IAM Role for Lambda
resource "aws_iam_role" "lex_lambda_role" {
  name = "lex-fulfillment-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lex_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda VPC access policy (for accessing LiteLLM in VPC)
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lex_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom policy for Secrets Manager access
resource "aws_iam_role_policy" "lambda_secrets_policy" {
  name = "lex-lambda-secrets-policy"
  role = aws_iam_role.lex_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.litellm_master_salt.arn
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "lex_fulfillment" {
  filename         = "${path.module}/../lambda/lex_fulfillment.zip"
  function_name    = "lex-qa-fulfillment"
  role             = aws_iam_role.lex_lambda_role.arn
  handler          = "lex_fulfillment.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../lambda/lex_fulfillment.zip")
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  vpc_config {
    subnet_ids         = local.public_subnet_ids
    security_group_ids = [data.aws_security_group.workload_security_group.id]
  }

  environment {
    variables = {
      LITELLM_ENDPOINT = "https://${aws_lb.litellm.dns_name}"
      LITELLM_API_KEY  = "" # Will be populated from Secrets Manager in production
      MODEL_NAME       = "claude-3-sonnet"
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lex_lambda_logs" {
  name              = "/aws/lambda/lex-qa-fulfillment"
  retention_in_days = 14

  tags = {
    Project     = var.project_name
    Environment = var.env
  }
}
