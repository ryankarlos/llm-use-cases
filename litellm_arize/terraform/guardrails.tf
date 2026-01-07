# Bedrock Guardrails for Content Filtering and PII Detection
# Requirements: 1.5, 1.7

resource "aws_bedrock_guardrail" "content_filter" {
  name        = "litellm-content-filter"
  description = "Content filtering guardrail for LiteLLM demo with hate, violence, sexual content filters and PII anonymization"

  blocked_input_messaging   = "Your request contains content that cannot be processed due to content policy restrictions."
  blocked_outputs_messaging = "The response was filtered due to content policy restrictions."

  # Content policy filters for hate, violence, and sexual content
  content_policy_config {
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "VIOLENCE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "SEXUAL"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "INSULTS"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }
    filters_config {
      type            = "MISCONDUCT"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  # PII anonymization for email and phone
  sensitive_information_policy_config {
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "NAME"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "US_SOCIAL_SECURITY_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }
  }

  tags = {
    Name        = "litellm-content-filter"
    Project     = var.project_name
    Environment = var.env
  }
}

# Create a guardrail version for production use
resource "aws_bedrock_guardrail_version" "content_filter" {
  guardrail_arn = aws_bedrock_guardrail.content_filter.guardrail_arn
  description   = "Initial version of LiteLLM content filter guardrail"
}
