# NHS Patient Booking Demo

AI-powered patient booking assistant using Amazon Bedrock Agents with Amazon Nova Lite.

## Overview

This demo showcases how to build an intelligent patient booking system using Amazon Bedrock Agents. The agent helps patients book GP and specialist appointments through natural conversation, while maintaining safety guardrails around medical advice.

## Architecture

![NHS Patient Booking Architecture](generated-diagrams/nhs_booking_architecture_wide.png)

The architecture consists of:

- **Streamlit App**: Demo frontend for patient interaction
- **Bedrock Agent**: Orchestrates conversation using Amazon Nova Lite
- **Safety Guardrails**: Built-in rules for no medical advice, emergency 999 redirect, NHS.uk referrals
- **Action Groups (Lambda)**:
  - Booking Actions: Check availability, Create booking
  - Approval Actions: Validate booking, Approve booking
  - Notification Actions: Send confirmation, Send letter
- **DynamoDB**: Stores bookings and session data
- **S3**: Stores audio files for voice interactions
- **X-Ray & CloudWatch**: Tracing and logging for observability

## Features

- **Natural Language Booking**: Book GP or specialist appointments through conversation
- **Availability Checking**: Query available appointment slots
- **Booking Confirmation**: Automated approval and confirmation workflow
- **Notifications**: Email/SMS confirmations (simulated in demo)
- **X-Ray Tracing**: Full observability of Lambda invocations
- **Safety Guardrails**: Agent refuses medical advice, directs emergencies to 999

## Prerequisites

- AWS Account with Bedrock access
- Amazon Nova Lite model enabled in your account
- Terraform >= 1.5
- Python 3.11+
- AWS CLI configured

## Quick Start

### 1. Enable Amazon Nova Lite

Before deploying, ensure Amazon Nova Lite is enabled in your AWS account:
1. Go to Amazon Bedrock console
2. Navigate to Model access
3. Request access to `amazon.nova-lite-v1:0`

### 2. Deploy Infrastructure

```bash
cd patient_bookings/terraform
terraform init
terraform apply -auto-approve
```

### 3. Set Environment Variables

```bash
eval "$(terraform output -raw env_vars)"
```

### 4. Run the Demo App

```bash
cd ../app
pip install -r ../requirements.txt
streamlit run streamlit_app.py
```

### 5. Test via CLI

```python
import boto3
import uuid

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='YOUR_AGENT_ID',
    agentAliasId='YOUR_ALIAS_ID',
    sessionId=str(uuid.uuid4()),
    inputText='I need to book a GP appointment',
    enableTrace=False
)

for event in response.get('completion', []):
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
```

## Project Structure

```
patient_bookings/
├── terraform/
│   ├── main.tf          # Lambda, DynamoDB, S3, IAM
│   ├── agents.tf        # Bedrock Agent configuration
│   ├── variables.tf     # Configuration variables
│   ├── outputs.tf       # Output values
│   └── data.tf          # Data sources
├── src/
│   ├── lambda_actions.py    # Lambda handler for agent actions
│   ├── bedrock_client.py    # Bedrock Agent client
│   ├── audio_utils.py       # Transcribe/Polly utilities
│   └── notifications.py     # Email/SMS utilities
├── app/
│   └── streamlit_app.py     # Demo UI
├── tests/
│   ├── test_lambda_actions.py
│   └── test_bedrock_client.py
├── load_tests/
│   └── locustfile.py        # Load testing
└── requirements.txt
```

## Agent Actions

The Bedrock Agent has access to these actions via Lambda:

| Action | Description |
|--------|-------------|
| `checkAvailability` | Query available appointment slots |
| `createBooking` | Create a new appointment booking |
| `approveBooking` | Approve and confirm a booking |
| `sendConfirmation` | Send email/SMS confirmation |

## Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region |
| `project_name` | `nhs-booking-demo` | Resource name prefix |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `BEDROCK_AGENT_ID` | Bedrock Agent ID |
| `BEDROCK_AGENT_ALIAS_ID` | Agent alias ID |
| `AWS_REGION` | AWS region |
| `AUDIO_BUCKET` | S3 bucket for audio files |

## Testing

### Unit Tests

```bash
cd patient_bookings
pytest tests/ -v
```

### Load Tests

```bash
cd load_tests
locust -f locustfile.py --headless -u 5 -r 1 -t 30s
```

## Observability

X-Ray tracing is enabled on the Lambda function. View traces in the AWS console:

```
https://us-east-1.console.aws.amazon.com/xray/home?region=us-east-1#/traces
```

## Cleanup

```bash
cd terraform
terraform destroy -auto-approve
```

## Cost Considerations

- **Bedrock**: Pay per token with Nova Lite (~$0.00006/1K input tokens)
- **Lambda**: Free tier covers most demo usage
- **DynamoDB**: On-demand pricing, minimal for demo
- **S3**: Minimal storage costs
- **S3 Vectors** (optional): Cost-effective vector storage for RAG

## Knowledge Base with S3 Vectors (Optional)

For enhanced NHS information retrieval, you can add a Knowledge Base using S3 Vectors:

### Benefits of S3 Vectors vs OpenSearch Serverless

| Feature | S3 Vectors | OpenSearch Serverless |
|---------|------------|----------------------|
| Cost | ~$0.0025/GB/month | ~$0.24/OCU/hour |
| Setup | Simple, managed | Complex, requires OCUs |
| Latency | Sub-second | Milliseconds |
| Best for | Cost-sensitive RAG | Low-latency search |

### Setup S3 Vectors Knowledge Base

1. Deploy the Knowledge Base resources:
```bash
terraform apply -target=aws_s3_bucket.kb_source -target=aws_s3_bucket.vectors
```

2. Create S3 Vector Bucket in Bedrock console:
   - Go to Amazon Bedrock > Knowledge bases
   - Create knowledge base
   - Select "S3 vector bucket" as vector store
   - Use "Quick create" option

3. Configure data source:
   - Point to `nhs-booking-demo-kb-source-*` bucket
   - Select Titan Embeddings model

4. Associate with Agent:
   - Edit the agent in Bedrock console
   - Add the Knowledge Base
   - Update agent alias

### Source Documents

The terraform deploys sample NHS content to the source bucket:
- `appointments.md` - Appointment types and booking info
- `services.md` - NHS services overview
- `patient_flow.md` - Patient flow and booking process

## Safety Notes

- This is a **demo application** - not for production use
- The agent does **not provide medical advice**
- For emergencies, the agent directs users to call 999
- No real patient data should be used

## References

- [Amazon Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Amazon Nova Models](https://aws.amazon.com/ai/generative-ai/nova/)
- [NHS Patient Flow Improvement](https://www.england.nhs.uk/improvement-hub/)
