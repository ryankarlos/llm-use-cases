# NHS Patient Booking Demo

AI-powered patient booking assistant using Amazon Bedrock Agents with multi-agent collaboration.

## Overview

This demo showcases an intelligent patient booking system using Amazon Bedrock Agents. The solution features a multi-agent architecture where a supervisor agent orchestrates specialist agents for triage, scheduling, and information queries. Patients interact through natural conversation to book GP and specialist appointments.

## Architecture

![NHS Patient Booking Architecture](generated-diagrams/nhs_booking_architecture_new.png)

The architecture includes:

- **Multi-Agent Supervisor**: Orchestrates workflow across specialist agents
- **Triage Agent**: Assesses urgency (emergency, urgent, routine)
- **Scheduling Agent**: Handles availability and bookings via Lambda
- **Information Agent**: Answers NHS questions via Knowledge Base
- **Bedrock Guardrails**: Safety rules for no medical advice, emergency 999 redirect
- **Lambda Actions**: Check availability, Create booking, Approve booking, Send confirmation
- **S3 Vectors Knowledge Base**: NHS services and appointment information
- **DynamoDB**: Stores bookings and session data
- **X-Ray & CloudWatch**: Observability and tracing

## Quick Start

### 1. Deploy Infrastructure

```bash
cd patient_bookings/terraform
terraform init
terraform apply -auto-approve
```

### 2. Set Environment Variables

```bash
# Get outputs from terraform
export BEDROCK_AGENT_ID=$(terraform output -raw agent_id)
export BEDROCK_AGENT_ALIAS_ID=$(terraform output -raw agent_alias_id)
export SUPERVISOR_AGENT_ID=$(terraform output -raw supervisor_agent_id)
export SUPERVISOR_ALIAS_ID=$(terraform output -raw supervisor_alias_id)
export AWS_REGION=us-east-1
```

### 3. Run the Streamlit App

```bash
cd patient_bookings
pip install streamlit boto3
streamlit run scripts/streamlit_app.py
```

Open http://localhost:8501 in your browser. Select between Single Agent or Multi-Agent Supervisor mode in the sidebar.

### 4. Test via CLI

```bash
cd patient_bookings
python scripts/test_multi_agent.py --agent supervisor
python scripts/test_multi_agent.py --agent single
python scripts/test_multi_agent.py --agent both
```

### 5. Run Load Tests

```bash
cd patient_bookings
pip install locust
locust -f scripts/locustfile.py --headless -u 2 -r 1 -t 30s
```

## Project Structure

```
patient_bookings/
├── scripts/
│   ├── streamlit_app.py      # Demo UI with agent selection
│   ├── test_multi_agent.py   # CLI test script
│   └── locustfile.py         # Load testing
├── src/
│   ├── lambda_actions.py     # Lambda handler for agent actions
│   ├── bedrock_client.py     # Bedrock Agent client
│   └── notifications.py      # Email/SMS utilities
├── terraform/
│   ├── main.tf               # Lambda, DynamoDB, S3, IAM
│   ├── agents.tf             # Single Bedrock Agent
│   ├── multi_agent.tf        # Multi-agent supervisor setup
│   ├── knowledge_base.tf     # S3 Vectors Knowledge Base
│   ├── variables.tf          # Configuration variables
│   └── outputs.tf            # Output values
├── knowledge_base/
│   └── nhs_content/          # NHS documentation for KB
├── tests/
│   ├── test_lambda_actions.py
│   └── test_bedrock_client.py
└── requirements.txt
```

## Agent Configurations

| Agent | ID | Description |
|-------|-----|-------------|
| Single Agent | P7QFL8LKUN | All-in-one booking agent |
| Supervisor | R5CKKTHOFB | Multi-agent orchestrator |
| Triage | MR73PAVETH | Urgency assessment |
| Scheduling | 9ESYPRBHBS | Booking with Lambda actions |
| Information | E90JQ9YHKP | NHS knowledge queries |

## Example Conversations

**Booking a GP Appointment:**
```
Patient: I need to book a GP appointment for next week. My name is Jane Doe.
Agent: [Routes to Scheduling Agent]
       [Calls checkAvailability Lambda]
       I found several available slots for you:
       - January 12th at 10:00 AM with Dr. Williams
       - January 14th at 10:00 AM with Dr. Williams
       Which would you prefer?
```

**Urgent Request:**
```
Patient: I have severe chest pain and difficulty breathing
Agent: [Routes to Triage Agent]
       This sounds like a medical emergency. Please call 999 immediately 
       or go to your nearest A&E department. Do not wait for an appointment.
```

**NHS Information:**
```
Patient: What should I bring to my appointment?
Agent: [Routes to Information Agent]
       [Searches Knowledge Base]
       Please bring your NHS number, a list of current medications, 
       and any relevant test results or referral letters.
```

## Cleanup

```bash
cd terraform
terraform destroy -auto-approve
```

## References

- [Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [Amazon Nova Models](https://aws.amazon.com/ai/generative-ai/nova/)
- [S3 Vectors](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-s3-vectors.html)
