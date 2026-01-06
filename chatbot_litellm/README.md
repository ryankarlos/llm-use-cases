# LiteLLM ECS Demo with Arize Phoenix Observability

A production-ready deployment of LiteLLM proxy on AWS ECS with Arize Phoenix for LLM observability, Amazon Lex chatbot integration, and AWS Bedrock models with guardrails.

## Architecture

![LiteLLM ECS Architecture](generated-diagrams/litellm_ecs_architecture.png)

### Components

| Component | Description |
|-----------|-------------|
| **LiteLLM Proxy** | Unified API gateway for multiple LLM providers with cost-based routing |
| **Arize Phoenix Cloud** | LLM observability platform for tracing and evaluation (cloud-hosted) |
| **Amazon Lex** | Conversational AI chatbot (QAAssistant) for natural language Q&A |
| **AWS Bedrock** | Managed LLM service (Claude, Titan, Nova models) |
| **Bedrock Guardrails** | Content filtering and PII detection |
| **CloudFront + Route53** | CDN and DNS for public HTTPS access |
| **Aurora PostgreSQL** | Serverless database for LiteLLM persistence |
| **Valkey/Redis** | In-memory cache for session management |

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
- Private CA for TLS certificates

## Quick Start

### 1. Build and Push LiteLLM Image

Build base image (one-time):

```bash
docker build -f Dockerfile.base -t litellm-base .
```

Push to ECR:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag litellm-base:latest <account>.dkr.ecr.us-east-1.amazonaws.com/base_images:litellm_base_image
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/base_images:litellm_base_image
```

### 2. Configure Terraform Variables

Create a `terraform.tfvars` file:

```hcl
env                       = "dev"
project_name              = "litellm-demo"
hosted_zone_name          = "example.com"
subdomain                 = "litellm"
cloudfront_subdomain      = "api"
certificate_authority_arn = "arn:aws:acm-pca:us-east-1:123456789:certificate-authority/xxx"
image_uri_litellm         = "<account>.dkr.ecr.us-east-1.amazonaws.com/litellm:latest"

s3_buckets = {
  lb_access_logs = "my-lb-logs-bucket"
  litellm        = "my-litellm-config-bucket"
}

litellm_secret_name   = "litellm-secrets"
litellm_secret_values = jsonencode({
  LITELLM_MASTER_KEY = "sk-xxx"
  LITELLM_SALT_KEY   = "salt-xxx"
})
```

### 3. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 4. Access Services

- **LiteLLM API**: `https://litellm.example.com/`
- **Phoenix Cloud**: `https://app.phoenix.arize.com/` (configure API key in terraform.tfvars)
- **Lex Bot**: Available in AWS Console under Amazon Lex > QAAssistant

## Using the Lex Chatbot

The QAAssistant bot forwards all queries to LiteLLM via Lambda:

```python
import boto3

lex = boto3.client('lexv2-runtime')

response = lex.recognize_text(
    botId='<bot-id>',
    botAliasId='<alias-id>',
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
- **Callbacks**: Arize Phoenix for tracing, Prometheus for metrics
- **Guardrails**: Bedrock content filter with PII anonymization

## Arize Phoenix Evaluation

Use SQuAD dataset for ground truth evaluation:

```python
from phoenix.client import Client
from datasets import load_dataset

# Load SQuAD from HuggingFace
squad = load_dataset("squad", split="validation[:100]")

# Create Phoenix dataset
client = Client()
dataset = client.create_dataset(
    name="squad-qa-evaluation",
    description="SQuAD Q&A pairs for LLM evaluation"
)

# Add examples with ground truth
for item in squad:
    client.add_example(
        dataset_id=dataset.id,
        input={"question": item["question"], "context": item["context"]},
        output={"answer": item["answers"]["text"][0]}
    )
```

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

## Cost Optimization

- ECS Fargate Spot for non-production
- Aurora Serverless v2 scales to zero
- CloudFront caching reduces origin requests
- Cost-based routing selects cheapest model

## Security

- All traffic encrypted with TLS 1.2+
- Secrets stored in AWS Secrets Manager
- VPC endpoints for AWS services
- Bedrock Guardrails for content safety
- PII anonymization enabled

## Monitoring

- CloudWatch Logs for all services
- Arize Phoenix Cloud for LLM-specific metrics
- Prometheus metrics from LiteLLM
- CloudWatch alarms for ECS health

## Arize Phoenix Cloud Setup

1. Create an account at [Arize Phoenix](https://phoenix.arize.com/)
2. Get your API key from the Phoenix dashboard
3. Set the `phoenix_api_key` variable in your `terraform.tfvars`
4. Traces will automatically be sent to your Phoenix cloud account

## License

MIT License
