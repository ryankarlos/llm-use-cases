# Implementation Plan: LiteLLM ECS Demo with Arize Phoenix

## Overview

This implementation extends the existing `chatbot_litellm/terraform` infrastructure to add Arize Phoenix observability, CloudFront/Route53 access, and Amazon Lex chatbot integration. The implementation is kept minimal to stay under 50 credits.

## Tasks

- [x] 1. Add Arize Phoenix ECS Service and ALB Routing
  - [x] 1.1 Create Phoenix ECS service module in `chatbot_litellm/terraform/phoenix.tf`
    - Add ECS task definition for Phoenix container (port 6006)
    - Add ECS service with Fargate launch type
    - Add target group for Phoenix
    - _Requirements: 1.1, 1.2_
  - [x] 1.2 Update ALB with path-based routing rules
    - Add listener rule for `/phoenix/*` → Phoenix target group (priority 100)
    - Update default rule for `/*` → LiteLLM target group (priority 200)
    - Add health check for Phoenix (`/` on port 6006)
    - _Requirements: 2.1, 2.2, 2.3, 2.6_
  - [x] 1.3 Update LiteLLM config with Arize Phoenix callback
    - Add `arize_phoenix` to callbacks in `config.yaml`
    - Add `PHOENIX_COLLECTOR_HTTP_ENDPOINT` environment variable
    - Configure Bedrock models only with cost-based routing
    - _Requirements: 1.3, 1.4, 1.6_

- [x] 2. Add CloudFront, Route53, and Bedrock Guardrails
  - [x] 2.1 Create CloudFront distribution in `chatbot_litellm/terraform/cloudfront.tf`
    - Add CloudFront distribution with ALB as origin
    - Configure HTTPS-only viewer protocol
    - Add ACM certificate for CloudFront
    - _Requirements: 2.4_
  - [x] 2.2 Create Route53 record for CloudFront
    - Add alias record pointing to CloudFront distribution
    - _Requirements: 2.5_
  - [x] 2.3 Create Bedrock Guardrail resource in `chatbot_litellm/terraform/guardrails.tf`
    - Add content policy filters (hate, violence, sexual)
    - Add PII anonymization for email and phone
    - Update LiteLLM config to reference guardrail ID
    - _Requirements: 1.5, 1.7_

- [x] 3. Add Amazon Lex Chatbot with Lambda Fulfillment
  - [x] 3.1 Create Lex bot and intents in `chatbot_litellm/terraform/lex.tf`
    - Add Lex V2 bot resource (QAAssistant)
    - Add fallback intent with fulfillment code hook
    - Add bot locale and version
    - _Requirements: 3.1, 3.2_
  - [x] 3.2 Create Lambda fulfillment function
    - Add Lambda function in `chatbot_litellm/lambda/lex_fulfillment.py`
    - Add IAM role with permissions for Lex and network access
    - Configure environment variables for LiteLLM endpoint
    - _Requirements: 3.3, 3.4, 3.5_
  - [x] 3.3 Update README and create AWS-style blog post
    - Update `chatbot_litellm/README.md` with new architecture
    - Create `chatbot_litellm/BLOG.md` with AWS-style blog post
    - Generate infrastructure diagram using AWS icons (MCP diagrams tool)
    - Include setup instructions and evaluation demo steps

## Notes

- All Terraform resources extend existing `chatbot_litellm/terraform` structure
- LiteLLM config updates go in existing `config.yaml` file
- Lambda function uses Python 3.11 runtime with urllib3 for HTTP requests
- Infrastructure diagram generated using AWS icons via MCP diagrams tool
