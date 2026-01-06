# Building an Enterprise LLM Gateway on AWS: Unifying Model Access with Observability and Safety Controls

The adoption of Large Language Models (LLMs) in enterprise applications has accelerated dramatically. Organizations are integrating models like Claude, Titan, and GPT into customer service chatbots, document analysis pipelines, and knowledge management systems. However, this rapid adoption brings significant operational challenges that many teams discover only after reaching production.

Consider a typical scenario: your development team has built a promising chatbot using Claude 3 Sonnet. The proof-of-concept impresses stakeholders, and suddenly you're asked to deploy it across multiple business units. Each team wants different models—some prefer Haiku for cost efficiency, others need Sonnet for complex reasoning. The finance team demands cost tracking per department. Security requires content filtering and PII protection. Operations needs visibility into model performance and latency.

This is where the complexity begins. Without a unified approach, teams end up with fragmented implementations, inconsistent security controls, and limited visibility into how models are actually being used.

## The Challenge of Multi-Model LLM Operations

Running LLMs in production differs fundamentally from traditional application development. Models behave probabilistically—the same input can produce different outputs. Costs scale with usage in ways that are difficult to predict. Content safety requires continuous monitoring rather than one-time validation.

Most organizations encounter three core challenges when scaling LLM deployments:

**Model Management Complexity.** Different use cases benefit from different models. A simple FAQ bot doesn't need the reasoning capabilities of Claude 3 Sonnet when Haiku can respond faster at lower cost. But switching between models typically requires code changes, and comparing model performance across your application becomes nearly impossible without standardized instrumentation.

**Observability Gaps.** Traditional application monitoring tools weren't designed for LLM workloads. You need to understand not just latency and error rates, but token usage, prompt effectiveness, and output quality. When a user reports that "the AI gave a wrong answer," you need the ability to trace exactly what happened—what prompt was sent, what context was included, and how the model responded.

**Safety and Compliance Requirements.** Enterprise deployments require content filtering to prevent harmful outputs, PII protection to maintain compliance, and audit trails for governance. Implementing these controls consistently across multiple models and applications is operationally demanding.

## Architectural Approach: The LLM Gateway Pattern

The solution to these challenges is an LLM gateway—a centralized service that sits between your applications and the underlying models. This pattern, common in API management, proves equally valuable for LLM operations.

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
│                                    VPC                                           │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Public Subnets                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    Application Load Balancer                          │  │ │
│  │  └──────────────────────────────────┬───────────────────────────────────┘  │ │
│  └─────────────────────────────────────┼──────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┼──────────────────────────────────────┐ │
│  │                         Private Subnets                                     │ │
│  │                                     ▼                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    ECS Fargate - LiteLLM Gateway                      │  │ │
│  │  └──────────────────────────────────────────────────────────────────────┘  │ │
│  │           │                         │                         │            │ │
│  │           ▼                         ▼                         ▼            │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │ │
│  │  │ Aurora Postgres │    │  Valkey Cache   │    │  VPC Endpoints  │        │ │
│  │  └─────────────────┘    └─────────────────┘    └────────┬────────┘        │ │
│  └─────────────────────────────────────────────────────────┼──────────────────┘ │
└────────────────────────────────────────────────────────────┼────────────────────┘
                                                             │
                    ┌────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐             │
│  │ Amazon Bedrock  │───▶│    Guardrails   │    │  Arize Phoenix  │             │
│  │ Claude, Titan   │    │ Content Filter  │    │     Cloud       │             │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

The architecture centers on LiteLLM, an open-source proxy that provides a unified OpenAI-compatible API for multiple LLM providers. Running on Amazon ECS with Fargate, the gateway handles model routing, observability instrumentation, and integrates with AWS security services.

## Intelligent Model Routing

One of LiteLLM's most valuable capabilities is intelligent routing across models. Rather than hardcoding model selections, you can define routing strategies that automatically select the optimal model based on your criteria.

Cost-based routing examines the token pricing of available models and selects the least expensive option that can handle the request. This approach works well when you have multiple models with similar capabilities but different price points. For example, Claude 3 Haiku costs significantly less than Sonnet while handling many tasks equally well.

```yaml
model_list:
  - model_name: claude-3-sonnet
    litellm_params:
      model: bedrock/anthropic.claude-3-sonnet-20240229-v1:0
  - model_name: claude-3-haiku
    litellm_params:
      model: bedrock/anthropic.claude-3-haiku-20240307-v1:0
  - model_name: titan-text
    litellm_params:
      model: bedrock/amazon.titan-text-express-v1

router_settings:
  routing_strategy: "cost-based-routing"
  num_retries: 3
```

The gateway also provides fallback handling. If a model returns an error or times out, the request automatically retries on an alternative model. This resilience is crucial for production systems where model availability can vary.

## Deep Observability with Arize Phoenix

Traditional monitoring tells you that your LLM endpoint responded in 2.3 seconds. LLM-specific observability tells you that the response used 1,247 tokens, cost $0.0037, and the output quality score was 0.89 based on your evaluation criteria.

Arize Phoenix provides this depth of insight through automatic instrumentation. Every request flowing through LiteLLM generates a trace that captures the complete interaction: the original prompt, any system instructions, the model's response, token counts, latency breakdown, and cost calculation.

This observability proves invaluable for debugging. When a user reports an unexpected response, you can search traces by session ID, examine the exact prompt that was sent, and understand why the model responded as it did. Often, issues trace back to prompt construction or missing context rather than model limitations.

Phoenix also enables systematic evaluation. By creating datasets of expected question-answer pairs, you can continuously measure how well your models perform against ground truth. This capability transforms LLM quality from a subjective assessment into a measurable metric.

## Content Safety Through Bedrock Guardrails

Amazon Bedrock Guardrails provide a managed solution for content filtering that operates at the model layer. Rather than implementing filtering logic in your application, you define policies that Bedrock enforces automatically.

The guardrail configuration for this deployment blocks harmful content categories including hate speech, violence, and sexual content. Each category can be configured with different sensitivity levels for inputs versus outputs, allowing you to be more restrictive about what the model generates than what users can ask.

```hcl
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
}
```

PII protection adds another layer of compliance. The guardrail automatically detects and anonymizes email addresses and phone numbers in model outputs. This protection operates transparently—your application code doesn't need to implement PII detection, and users receive responses with sensitive information already masked.

## Conversational Interface with Amazon Lex

While the LiteLLM gateway provides an API for programmatic access, many use cases benefit from a conversational interface. Amazon Lex offers a managed chatbot service that integrates naturally with the gateway architecture.

The QAAssistant bot deployed in this architecture uses a simple but effective pattern: it captures user utterances and forwards them to LiteLLM via a Lambda function. This approach leverages Lex's conversation management—session handling, context tracking, and multi-turn dialogue—while using LiteLLM for the actual language understanding.

```python
def lambda_handler(event, context):
    user_message = event.get('inputTranscript', '')
    
    response = http.request(
        'POST',
        f"{LITELLM_ENDPOINT}/chat/completions",
        body=json.dumps({
            'model': 'claude-3-sonnet',
            'messages': [{'role': 'user', 'content': user_message}]
        })
    )
    
    result = json.loads(response.data)
    return build_lex_response(result['choices'][0]['message']['content'])
```

The Lambda function runs within the VPC, communicating with the internal load balancer. This design keeps LLM traffic on the private network while Lex handles the public-facing conversation interface.

## Infrastructure Design Decisions

Several architectural choices in this deployment reflect production requirements that aren't immediately obvious in proof-of-concept implementations.

**Aurora Serverless v2** provides the database backend for LiteLLM. The serverless configuration scales capacity automatically based on load, scaling down to 0.5 ACU during idle periods. For a development or low-traffic deployment, this approach significantly reduces costs compared to provisioned database instances. Aurora also handles the complexity of database high availability, with automatic failover and backup management.

**Valkey (Redis-compatible) caching** accelerates repeated operations and manages session state. LiteLLM uses the cache for rate limiting, request deduplication, and storing conversation context. The ElastiCache deployment includes encryption in transit and at rest, with authentication tokens managed through Secrets Manager.

**VPC endpoints for Bedrock** keep model invocations on the AWS private network. Without endpoints, requests to Bedrock would traverse the public internet, adding latency and potential security exposure. The endpoint configuration routes traffic through AWS's backbone network, improving both performance and security posture.

**Self-signed TLS certificates** on the internal load balancer provide encryption for traffic within the VPC. For production deployments with public access requirements, you would replace these with certificates from AWS Certificate Manager backed by a public or private certificate authority.

## Operational Considerations

Running this architecture in production requires attention to several operational aspects.

**Secret rotation** should be implemented for the LiteLLM master key and database credentials. AWS Secrets Manager supports automatic rotation, and the ECS task definition references secrets by ARN, allowing rotation without redeployment.

**Scaling configuration** in the ECS service definition sets minimum and maximum task counts. The auto-scaling policy monitors CPU utilization and adjusts capacity accordingly. For LLM workloads, you may also want to consider scaling based on request queue depth or response latency.

**Cost monitoring** becomes critical as usage grows. CloudWatch metrics from LiteLLM track token usage per model, and Phoenix provides detailed cost breakdowns per request. Setting up billing alerts based on these metrics helps prevent unexpected charges.

**Log retention** policies should align with your compliance requirements. The deployment configures 14-day retention for Lambda logs and ECS container logs. Adjust these values based on your audit and debugging needs.

## Extending the Architecture

This deployment provides a foundation that you can extend based on your specific requirements.

**Additional model providers** can be added to the LiteLLM configuration. The proxy supports OpenAI, Anthropic (direct), Cohere, and many other providers alongside Bedrock. This flexibility allows you to compare models from different providers or use specialized models for specific tasks.

**Custom evaluation pipelines** can leverage Phoenix's dataset and experiment features. By defining evaluation criteria specific to your use case—factual accuracy for knowledge bases, tone appropriateness for customer service, code correctness for development assistants—you can systematically measure and improve model performance.

**Fine-tuned models** deployed on SageMaker can be integrated through LiteLLM's SageMaker provider. This capability allows you to route specific request types to custom models while using foundation models for general queries.

## Conclusion

Building production LLM systems requires more than model access. Organizations need unified interfaces across providers, deep observability into model behavior, and robust safety controls. The architecture presented here addresses these requirements through a combination of open-source tooling and managed AWS services.

LiteLLM provides the gateway abstraction, offering a consistent API regardless of underlying model provider. Arize Phoenix delivers the observability depth that LLM operations demand. Amazon Bedrock Guardrails enforce content safety at the model layer. Together, these components create a foundation for enterprise LLM deployments that scales with your organization's needs.

The complete Terraform configuration for this architecture is available in the accompanying repository. The modular design allows you to adopt individual components—perhaps starting with just the LiteLLM gateway—and expand as your requirements evolve.

---

*The code for this architecture is available in the [chatbot_litellm](.) directory. See the README for deployment instructions.*
