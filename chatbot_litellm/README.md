# LiteLLM ECS Demo with Arize Phoenix Observability

A production-ready deployment of LiteLLM proxy on AWS ECS with Arize Phoenix for LLM observability, Amazon Lex chatbot integration, and AWS Bedrock models with guardrails.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    Users                                         │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
            ┌───────────────┐                   ┌───────────────┐
            │   Route53     │                   │  Amazon Lex   │
            │ litellmdemo.com│                   │ QAAssistant   │
            └───────┬───────┘                   └───────┬───────┘
                    │                                   │
                    ▼                                   ▼
            ┌───────────────┐                   ┌───────────────┐
            │  CloudFront   │                   │    Lambda     │
            │     CDN       │                   │  Fulfillment  │
            └───────┬───────┘                   └───────┬───────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VPC (project-vpc)                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Public Subnets                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │              Application Load Balancer (Self-Signed TLS)              │  │ │
│  │  └──────────────────────────────────┬───────────────────────────────────┘  │ │
│  └─────────────────────────────────────┼──────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┼──────────────────────────────────────┐ │
│  │                         Private Subnets                                     │ │
│  │                                     ▼                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    ECS Fargate Cluster                                │  │ │
│  │  │  ┌────────────────────────────────────────────────────────────────┐  │  │ │
│  │  │  │                   LiteLLM Service                               │  │  │ │
│  │  │  │  • Unified LLM API Gateway                                      │  │  │ │
│  │  │  │  • Cost-based routing                                           │  │  │ │
│  │  │  │  • Phoenix tracing                                              │  │  │ │
│  │  │  └────────────────────────────────────────────────────────────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────────────────────┘  │ │
│  │                                     │                                       │ │
│  │           ┌─────────────────────────┼─────────────────────────┐            │ │
│  │           ▼                         ▼                         ▼            │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │ │
│  │  │ Aurora Postgres │    │  Valkey/Redis   │    │  VPC Endpoints  │        │ │
│  │  │  Serverless v2  │    │     Cache       │    │    (Bedrock)    │        │ │
│  │  └─────────────────┘    └─────────────────┘    └────────┬────────┘        │ │
│  └─────────────────────────────────────────────────────────┼──────────────────┘ │
└────────────────────────────────────────────────────────────┼────────────────────┘
                                                             │
                    ┌────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AWS AI Services                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐             │
│  │ Amazon Bedrock  │───▶│    Guardrails   │    │  Arize Phoenix  │             │
│  │ Claude, Titan   │    │ Content Filter  │    │     Cloud       │             │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **LiteLLM Proxy** | Unified API gateway for multiple LLM providers with cost-based routing |
| **Arize Phoenix Cloud** | LLM observability platform for tracing and evaluation |
| **Amazon Lex** | Conversational AI chatbot (QAAssistant) for natural language Q&A |
| **AWS Bedrock** | Managed LLM service (Claude, Titan, Nova models) |
| **Bedrock Guardrails** | Content filtering and PII detection |
| **CloudFront + Route53** | CDN and DNS for public HTTPS access |
| **Aurora PostgreSQL** | Serverless v2 database for LiteLLM persistence |
| **Valkey/Redis** | In-memory cache for session management |

## Deployed Resources

After running `terraform apply`, the following resources are created:

| Resource | Value |
|----------|-------|
| Route53 Hosted Zone | `litellmdemo.com` |
| CloudFront Domain | `cdn.litellmdemo.com` |
| ALB DNS | `internal-litellm-*.elb.amazonaws.com` |
| Aurora Cluster | `litellm-aurora-postgresql` |
| ECS Cluster | `litellm-cluster` |
| Lex Bot | `QAAssistant` |
| Lambda Function | `lex-qa-fulfillment` |

## Features

- **Multi-model routing**: Cost-based or latency-based routing across Bedrock models
- **LLM Observability**: Full request tracing via Arize Phoenix Cloud
- **Content Safety**: Bedrock Guardrails for hate, violence, sexual content filtering
- **PII Protection**: Automatic anonymization of email and phone numbers
- **Chatbot Interface**: Amazon Lex bot with Lambda fulfillment for Q&A
- **High Availability**: ECS Fargate with auto-scaling and health checks

## Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- Docker for building LiteLLM image
- Existing VPC with public/private subnets

## Quick Start

### 1. Build and Push LiteLLM Image

```bash
# Create ECR repository
aws ecr create-repository --repository-name litellm-base

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -f Dockerfile.litellm -t litellm-base .
docker tag litellm-base:latest <account>.dkr.ecr.us-east-1.amazonaws.com/litellm-base:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/litellm-base:latest
```

### 2. Configure Terraform Variables

Create a `terraform.tfvars` file:

```hcl
env               = "dev"
project_name      = "litellm-demo"
hosted_zone_name  = "litellmdemo.com"
subdomain         = "api"
vpc_name          = "project-vpc"
image_uri_litellm = "<account>.dkr.ecr.us-east-1.amazonaws.com/litellm-base:latest"

tag = {
  name = "litellm-demo"
}

# Secrets - Update after deployment with actual keys
litellm_secret_name   = "litellm-secrets"
litellm_secret_values = "{\"LITELLM_MASTER_KEY\":\"sk-xxx\",\"LITELLM_SALT_KEY\":\"salt-xxx\"}"

# Phoenix API key (optional)
phoenix_api_key = ""

# Aurora scaling
aurora_scaling_config = {
  min_capacity = 0.5
  max_capacity = 2
}

skip_final_snapshot = true
```

### 3. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 4. Update Secrets

After deployment, update the secrets with actual values:

```bash
# Generate keys
MASTER_KEY=$(openssl rand -hex 32)
SALT_KEY=$(openssl rand -hex 32)

# Update secret
aws secretsmanager put-secret-value \
  --secret-id litellm-secrets \
  --secret-string "{\"LITELLM_MASTER_KEY\":\"sk-$MASTER_KEY\",\"LITELLM_SALT_KEY\":\"$SALT_KEY\"}"
```

### 5. Access Services

- **LiteLLM API**: `https://cdn.litellmdemo.com/` (via CloudFront)
- **Phoenix Cloud**: `https://app.phoenix.arize.com/`
- **Lex Bot**: AWS Console > Amazon Lex > QAAssistant

## Using the Lex Chatbot

The QAAssistant bot forwards all queries to LiteLLM via Lambda:

```python
import boto3

lex = boto3.client('lexv2-runtime')

response = lex.recognize_text(
    botId='XGILVCLOLH',  # Get from terraform output
    botAliasId='TSTALIASID',
    localeId='en_US',
    sessionId='user-123',
    text='What is the capital of France?'
)

print(response['messages'][0]['content'])
```

## LiteLLM Configuration

The `config.yaml` configures:

- **Models**: Claude 3 Sonnet/Haiku, Titan Text, Nova Pro
- **Routing**: Cost-based routing strategy
- **Callbacks**: Arize Phoenix for tracing
- **Guardrails**: Bedrock content filter with PII anonymization

## Terraform Resources

| Resource | File |
|----------|------|
| ECS Cluster & Services | `main.tf` |
| CloudFront & Route53 | `cloudfront.tf` |
| Bedrock Guardrails | `guardrails.tf` |
| Amazon Lex & Lambda | `lex.tf` |
| Aurora PostgreSQL | `main.tf` |
| Valkey/Redis | `main.tf` |
| KMS Keys | `kms.tf` |
| Secrets Manager | `main.tf` |

## Cost Optimization

- Aurora Serverless v2 scales to zero during idle periods
- Cost-based routing selects cheapest capable model
- CloudFront caching reduces origin requests
- Single-AZ deployment option for dev environments

## Security

- All traffic encrypted with TLS (self-signed cert for ALB)
- Secrets stored in AWS Secrets Manager
- VPC endpoints for Bedrock (private connectivity)
- Bedrock Guardrails for content safety
- PII anonymization enabled

## Cleanup

```bash
cd terraform
terraform destroy
```

## License

MIT License
