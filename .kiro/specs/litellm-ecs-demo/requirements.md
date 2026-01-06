# Requirements Document

## Introduction

This feature extends the existing LiteLLM ECS deployment with Arize Phoenix OSS for LLM observability/evaluation, Amazon Lex chatbot integration focused on fitness/gym topics, and CloudFront/Route53 for public access. The demo uses AWS Bedrock models exclusively with guardrails, prompt management, and cost/latency-based routing.

## Glossary

- **LiteLLM**: An open-source proxy that provides a unified API for multiple LLM providers with routing, guardrails, and prompt management
- **Arize_Phoenix**: Open-source LLM observability platform for tracing, evaluation, and debugging
- **Amazon_Lex**: AWS managed service for building conversational interfaces using voice and text
- **CloudFront**: AWS CDN service for content delivery and edge caching
- **ALB**: Application Load Balancer for distributing traffic to ECS services
- **Bedrock_Guardrails**: AWS service for implementing content filtering, PII detection, and safety controls on LLM responses
- **Prompt_Routing**: LiteLLM feature to route requests based on cost or latency optimization strategies
- **Ground_Truth**: Known correct answers used as reference for evaluating LLM response quality

## Requirements

### Requirement 1: ECS Services for LiteLLM and Arize Phoenix with Bedrock Integration

**User Story:** As a developer, I want to deploy LiteLLM and Arize Phoenix as ECS services with AWS Bedrock models, guardrails, and intelligent routing, so that I can proxy LLM requests with cost/latency optimization and observe performance.

#### Acceptance Criteria

1. THE Terraform_Module SHALL deploy Arize Phoenix as an ECS Fargate service alongside existing LiteLLM service
2. WHEN Arize Phoenix service starts, THE ECS_Service SHALL expose port 6006 for the Phoenix UI
3. THE LiteLLM_Service SHALL be configured to send traces to Arize Phoenix using the `arize_phoenix` callback
4. THE LiteLLM_Config SHALL use only AWS Bedrock models (Claude, Titan, or Nova)
5. THE LiteLLM_Config SHALL configure Bedrock Guardrails for content filtering and PII detection
6. THE LiteLLM_Config SHALL implement prompt routing with `cost-based-routing` or `latency-based-routing` strategy
7. THE Terraform_Module SHALL create Bedrock Guardrail resource with appropriate filters

### Requirement 2: CloudFront, Route53 and ALB Configuration

**User Story:** As a user, I want to access LiteLLM docs and Phoenix UI via friendly URLs, so that I can easily interact with the services.

#### Acceptance Criteria

1. THE ALB SHALL route traffic to both LiteLLM and Arize Phoenix services based on path patterns
2. WHEN a request is made to /phoenix/*, THE ALB SHALL forward to Arize Phoenix target group
3. WHEN a request is made to /*, THE ALB SHALL forward to LiteLLM target group (default)
4. THE CloudFront_Distribution SHALL cache static assets and provide HTTPS termination
5. THE Route53_Record SHALL create a DNS alias pointing to CloudFront distribution
6. THE Terraform_Module SHALL configure health checks for both target groups

### Requirement 3: Amazon Lex Q&A Chatbot Integration

**User Story:** As a user, I want to interact with a general Q&A chatbot, so that I can ask questions and receive answers in a natural way.

#### Acceptance Criteria

1. THE Amazon_Lex_Bot SHALL be configured as a general "QAAssistant" bot for answering questions
2. THE Lex_Bot SHALL include a fallback intent to forward all queries to the LLM
3. WHEN a user sends a message to Lex, THE Lambda_Function SHALL forward the request to LiteLLM proxy
4. THE Lambda_Function SHALL return LiteLLM response back to Lex for user display
5. THE Terraform_Module SHALL create Lex bot, intents, and Lambda fulfillment function

## Demo Topic: SQuAD Dataset for Ground Truth Evaluation

For demonstrating Arize Phoenix evaluation capabilities, the **SQuAD (Stanford Question Answering Dataset)** will be used:

### SQuAD Dataset Integration with Arize Phoenix
SQuAD can be easily imported into Phoenix using the Datasets API:

```python
from phoenix.client import Client
from datasets import load_dataset

# Load SQuAD from HuggingFace
squad = load_dataset("squad", split="validation[:100]")  # Sample 100 examples

# Create Phoenix dataset with ground truth
client = Client()
dataset = client.create_dataset(
    name="squad-qa-evaluation",
    description="SQuAD Q&A pairs for LLM evaluation"
)

# Add examples with ground truth answers
for item in squad:
    client.add_example(
        dataset_id=dataset.id,
        input={"question": item["question"], "context": item["context"]},
        output={"answer": item["answers"]["text"][0]}  # Ground truth
    )
```

### Why SQuAD Works Well
- **100K+ Q&A pairs** with verified ground truth answers
- **Easy HuggingFace integration** - `load_dataset("squad")`
- **Phoenix-compatible format** - input/output structure matches Phoenix Datasets API
- **Diverse topics** - History, science, geography, literature from Wikipedia

### Evaluation Metrics in Arize Phoenix
- **Exact Match (EM)**: Does LLM answer exactly match ground truth?
- **F1 Score**: Token overlap between LLM answer and ground truth
- **Semantic Similarity**: Embedding-based comparison
- **Latency Tracking**: Response times across Bedrock models
- **Cost Analysis**: Token usage per model
