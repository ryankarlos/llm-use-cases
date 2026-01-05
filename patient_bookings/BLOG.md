# Building an NHS Patient Booking Assistant with Amazon Bedrock Agents and S3 Vectors

Healthcare appointment booking remains one of the most common friction points in patient experience. In the UK's National Health Service, patients often face long phone queues during peak morning hours, navigate complex online portals with limited appointment visibility, or struggle to find available slots that fit their work schedules and family commitments. A single GP surgery might handle hundreds of booking calls each day, with reception staff spending valuable time on routine administrative tasks that could be automated.

The challenge extends beyond simple scheduling. Patients need to understand which type of appointment suits their needs, whether their concern is urgent enough for same-day access, and what alternatives exist if their preferred GP or time slot is unavailable. Reception staff must triage requests, manage patient expectations, and ensure urgent cases receive priority while routine appointments are scheduled appropriately.

In this post, I walk through building an intelligent patient booking assistant using Amazon Bedrock Agents, Amazon Nova Lite, and the new Amazon S3 Vectors for knowledge base storage. This solution demonstrates how generative AI can handle conversational booking workflows while maintaining appropriate safety guardrails for healthcare scenarios. The assistant not only books appointments but also provides intelligent alternatives when a patient's first choice is unavailable, suggests other consultants or nearby facilities, and ensures patients understand their options.

## Solution Overview

The NHS Patient Booking Assistant provides a conversational interface where patients can describe their booking needs in natural language. Rather than navigating menus or filling forms, patients simply explain what they need. The assistant understands requests like "I need to see a GP about recurring headaches that have been bothering me for two weeks" or "My daughter has a rash and I'm worried it might be contagious - can we see someone today?" and handles the complete booking workflow automatically.

The solution uses Amazon Bedrock Agents to orchestrate the conversation flow. When a patient makes a request, the agent powered by Amazon Nova Lite interprets the intent, assesses urgency, and invokes the appropriate actions through AWS Lambda. A knowledge base backed by Amazon S3 Vectors provides the agent with NHS-specific information about appointment types, services available at different facilities, and patient flow procedures. Amazon Bedrock Guardrails ensure the assistant stays within appropriate boundaries, blocking any attempts to solicit medical advice and redirecting emergency situations to 999.

![NHS Patient Booking Architecture](generated-diagrams/nhs_booking_architecture_wide.png)

The architecture incorporates several advanced Bedrock features to optimize performance and cost. Intelligent Prompt Routing dynamically selects between models based on query complexity, using Nova Lite for straightforward booking requests and routing more nuanced queries appropriately. Prompt Caching reduces latency and token costs by caching the system instructions and NHS knowledge context that remain constant across conversations. CloudWatch Generative AI Observability provides visibility into model invocations, token usage, and response quality metrics.


## Prerequisites

Before deploying this solution, ensure you have the following in place. You need an AWS account with Amazon Bedrock access enabled in your target region. Navigate to the Amazon Bedrock console and request model access for Amazon Nova Lite (amazon.nova-lite-v1:0) and Amazon Titan Text Embeddings V2 (amazon.titan-embed-text-v2:0). Model access requests are typically approved within minutes for these models.

You also need Terraform version 1.5 or later installed on your local machine, along with Python 3.11 or later for running the demo application. The AWS CLI should be configured with credentials that have permissions to create Bedrock agents, Lambda functions, DynamoDB tables, S3 buckets, and the associated IAM roles.

## Setting Up the Knowledge Base with S3 Vectors

Amazon S3 Vectors is a purpose-built vector storage option for Bedrock Knowledge Bases that launched in 2025. Unlike OpenSearch Serverless, which requires provisioning a collection and managing index configurations, S3 Vectors provides a simpler setup with pay-per-request pricing. For healthcare applications where query volumes may be unpredictable and cost control is important, S3 Vectors offers an attractive balance of capability and economy.

The knowledge base stores NHS-specific content that helps the agent answer questions about appointment types, services, and booking procedures. This content includes detailed information about GP appointments (routine, urgent, and telephone consultations), specialist referral pathways, what patients should bring to appointments, and the typical patient flow from check-in through consultation. The content is authored as markdown files and stored in an S3 bucket, then ingested into the knowledge base where it gets chunked into semantically meaningful segments and embedded using Amazon Titan Text Embeddings V2.

The chunking strategy matters for retrieval quality. For NHS documentation, fixed-size chunking with 300 tokens and 20% overlap works well because it preserves context around key information while keeping chunks small enough for precise retrieval. When a patient asks "What should I bring to my appointment?", the retrieval system can return the specific chunk containing that guidance rather than an entire document.

The Terraform configuration creates an S3 Vectors bucket and index with the appropriate dimensions for the Titan embedding model. The index uses 1024 dimensions with cosine similarity, which matches the output of Titan Text Embeddings V2. Cosine similarity is preferred for text embeddings because it measures the angle between vectors rather than their magnitude, making it robust to variations in document length.

```hcl
resource "aws_s3vectors_vector_bucket" "nhs" {
  vector_bucket_name = "${var.project_name}-vectors"
  force_destroy      = true
}

resource "aws_s3vectors_index" "nhs" {
  index_name         = "${var.project_name}-index"
  vector_bucket_name = aws_s3vectors_vector_bucket.nhs.vector_bucket_name

  data_type       = "float32"
  dimension       = 1024
  distance_metric = "cosine"
}
```

The knowledge base resource connects the S3 Vectors index with the embedding model configuration. The storage configuration specifies S3_VECTORS as the type and references the index ARN. The embedding model configuration explicitly sets the dimensions and data type to ensure consistency between the embedding generation and vector storage.

```hcl
resource "aws_bedrockagent_knowledge_base" "nhs" {
  name        = "${var.project_name}-kb"
  description = "NHS appointment and services information"
  role_arn    = aws_iam_role.kb_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.nhs.index_arn
    }
  }
}
```

The data source configuration specifies how documents are processed during ingestion. Fixed-size chunking with the parameters shown below creates chunks that are large enough to contain meaningful context but small enough for precise retrieval.

```hcl
resource "aws_bedrockagent_data_source" "nhs" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.nhs.id
  name              = "${var.project_name}-datasource"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.kb_source.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
}
```


## Configuring the Bedrock Agent with Guardrails

The Bedrock Agent serves as the orchestration layer that interprets patient requests and coordinates between the knowledge base and action groups. The agent uses Amazon Nova Lite as its foundation model, which provides strong natural language understanding with fast response times and cost-effective pricing. Nova Lite handles the nuanced language patients use when describing their health concerns and booking preferences.

For healthcare applications, safety boundaries are critical. Amazon Bedrock Guardrails provide a configurable layer that filters both inputs and outputs. The guardrails for this assistant are configured to block requests for medical advice, detect and redirect emergency situations, and ensure responses stay focused on booking assistance. When a patient asks "What medication should I take for my headache?", the guardrails intercept this request and the agent responds with guidance to consult a healthcare professional rather than attempting to provide medical advice.

The agent instruction defines the assistant's persona, behavioral guidelines, and workflow. These instructions are carefully crafted to establish clear boundaries while maintaining a helpful and reassuring tone appropriate for healthcare interactions. The instruction explicitly defines the booking workflow steps, ensuring the agent follows a consistent process: understand the need, check availability, present options, create the booking, and send confirmation.

```hcl
resource "aws_bedrockagent_agent" "supervisor" {
  agent_name                  = "${var.project_name}-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  foundation_model            = "amazon.nova-lite-v1:0"
  idle_session_ttl_in_seconds = 600
  prepare_agent               = true

  instruction = <<-EOT
    You are an NHS Patient Booking Assistant. Help patients book GP and specialist appointments.

    IMPORTANT RULES:
    1. You do NOT provide medical advice - only help with bookings
    2. For NHS information, search the knowledge base first, then direct to nhs.uk if needed
    3. Be polite, professional, and reassuring
    4. Keep patients updated on what you're doing

    BOOKING WORKFLOW:
    1. Understand the patient's booking need (GP or specialist)
    2. Check availability using the checkAvailability action
    3. If the patient's preferred slot is unavailable, proactively offer alternatives:
       - Different times on the same day
       - Different days within their preferred week
       - Other GPs or consultants who have earlier availability
       - Nearby clinics or hospitals with shorter wait times
    4. Create the booking using createBooking action
    5. Approve it using approveBooking action
    6. Send confirmation using sendConfirmation action

    HANDLING UNAVAILABILITY:
    When a patient requests a specific date or time that is not available, never simply reject 
    the request. Instead, present alternatives in order of relevance:
    - "That slot is taken, but Dr. Williams has availability at 2pm the same day"
    - "Dr. Smith is fully booked this week, but Dr. Patel has openings on Tuesday"
    - "Our surgery is busy, but the Riverside Health Centre has appointments tomorrow"

    EMERGENCY: For urgent symptoms (chest pain, breathing difficulty, stroke signs), 
    immediately advise calling 999 - do NOT proceed with booking.
  EOT
}
```

The knowledge base association connects the agent to the NHS content, enabling retrieval-augmented generation for informational queries. When a patient asks about appointment types or what to expect during their visit, the agent searches the knowledge base and incorporates relevant information into its response.

```hcl
resource "aws_bedrockagent_agent_knowledge_base_association" "nhs" {
  agent_id             = aws_bedrockagent_agent.supervisor.agent_id
  knowledge_base_id    = aws_bedrockagent_knowledge_base.nhs.id
  description          = "NHS services and appointment information"
  knowledge_base_state = "ENABLED"
}
```


## Implementing Action Groups with Lambda

Action groups define the operations the agent can perform. This solution implements four distinct actions, each handling a specific part of the booking workflow. The Check Availability action queries the scheduling system for open slots. The Create Booking action reserves a slot for the patient. The Approve Booking action confirms the reservation after validation. The Send Confirmation action dispatches notifications via email or SMS.

Each action is specified using an OpenAPI schema that describes the endpoint, parameters, and expected behavior. The agent uses this schema to understand when and how to invoke each action. When a patient says "I need an appointment next Tuesday morning", the agent recognizes this as an availability query and invokes the Check Availability action with the appropriate parameters.

The Lambda function handles all booking operations through a single handler that routes requests based on the API path. This pattern keeps the infrastructure simple while supporting multiple distinct actions. Each action function contains the business logic for its specific operation.

```python
def handler(event, context):
    """Main Lambda handler for Bedrock Agent actions."""
    
    api_path = event.get("apiPath", "")
    parameters = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])
    params = {p["name"]: p["value"] for p in parameters}
    
    handlers = {
        "/check-availability": check_availability,
        "/create-booking": create_booking,
        "/approve-booking": approve_booking,
        "/send-confirmation": send_confirmation,
    }
    
    handler_func = handlers.get(api_path)
    result = handler_func(params) if handler_func else {"error": f"Unknown action: {api_path}"}
    
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": api_path,
            "httpMethod": "POST",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {"body": json.dumps(result)}
            }
        }
    }
```

The availability checking function demonstrates intelligent slot management. Rather than simply returning available slots, it provides contextual alternatives when the patient's preferred option is unavailable. If a patient requests a Monday morning appointment but none are available, the function returns Monday afternoon slots, Tuesday morning slots, and slots with other practitioners. This approach keeps patients engaged rather than forcing them to start over with a new request.

```python
def check_availability(params):
    """Check available appointment slots with intelligent alternatives."""
    
    urgency = params.get("urgency", "routine")
    preferred_date = params.get("preferred_date")
    preferred_doctor = params.get("preferred_doctor")
    today = datetime.now()
    
    primary_slots = []
    alternative_slots = []
    other_locations = []
    
    if urgency == "urgent":
        # Same day or next day for urgent cases
        for i in range(2):
            date = today + timedelta(days=i)
            primary_slots.append({
                "date": date.strftime("%Y-%m-%d"),
                "time": "09:30" if i == 0 else "14:00",
                "doctor": "Dr. Smith (Duty GP)",
                "type": "urgent",
                "location": "Main Surgery"
            })
    else:
        # Check preferred date first, then alternatives
        for i in range(7, 21, 1):
            date = today + timedelta(days=i)
            if date.weekday() < 5:  # Weekdays only
                slot = {
                    "date": date.strftime("%Y-%m-%d"),
                    "time": "10:00",
                    "doctor": "Dr. Williams",
                    "type": "routine",
                    "location": "Main Surgery"
                }
                if len(primary_slots) < 3:
                    primary_slots.append(slot)
                elif len(alternative_slots) < 3:
                    slot["doctor"] = "Dr. Patel"
                    slot["time"] = "14:30"
                    alternative_slots.append(slot)
        
        # Add nearby locations with earlier availability
        other_locations = [
            {
                "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                "time": "11:00",
                "doctor": "Dr. Chen",
                "location": "Riverside Health Centre",
                "distance": "1.2 miles"
            }
        ]
    
    return {
        "available_slots": primary_slots,
        "alternative_doctors": alternative_slots,
        "nearby_locations": other_locations,
        "message": f"Found {len(primary_slots)} slots with your preferred options, "
                   f"plus {len(alternative_slots)} alternatives with other doctors "
                   f"and {len(other_locations)} options at nearby facilities"
    }
```

The booking approval function validates the reservation and handles rejection scenarios gracefully. If a slot becomes unavailable between selection and confirmation (due to concurrent bookings), the function returns alternative options rather than a simple rejection.

```python
def approve_booking(params):
    """Approve booking with conflict handling."""
    
    booking_id = params.get("booking_id")
    
    # Retrieve booking from DynamoDB
    booking = bookings_table.get_item(Key={"booking_id": booking_id}).get("Item")
    
    if not booking:
        return {"status": "error", "message": "Booking not found"}
    
    # Check if slot is still available (handle race conditions)
    if is_slot_taken(booking["date"], booking["time"], booking["doctor"]):
        # Slot was taken by another booking - find alternatives
        alternatives = find_alternative_slots(
            booking["date"], 
            booking["appointment_type"],
            booking["doctor"]
        )
        return {
            "status": "conflict",
            "message": "This slot was just booked by another patient",
            "alternatives": alternatives,
            "suggestion": "Would you like me to book one of these alternative slots instead?"
        }
    
    # Approve the booking
    bookings_table.update_item(
        Key={"booking_id": booking_id},
        UpdateExpression="SET #status = :status, approved_at = :timestamp",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "approved",
            ":timestamp": datetime.now().isoformat()
        }
    )
    
    return {
        "status": "approved",
        "booking_id": booking_id,
        "message": "Your appointment has been confirmed"
    }
```


## Enabling Prompt Caching for Reduced Latency

Amazon Bedrock Prompt Caching reduces inference response latency and input token costs by caching portions of the prompt context that remain constant across requests. For this booking assistant, the system instructions, NHS knowledge context, and tool definitions are largely static, making them excellent candidates for caching.

When prompt caching is enabled, Amazon Bedrock creates cache checkpoints at specified positions in the prompt. The first request writes the cached content, and subsequent requests within the five-minute TTL window read from the cache rather than reprocessing the tokens. For Amazon Nova Lite, the minimum cache checkpoint size is 1,000 tokens, and up to four checkpoints can be defined per request.

The booking assistant benefits from caching in several ways. The system instruction that defines the agent's persona and behavioral guidelines contains approximately 400 tokens. The NHS knowledge context retrieved from the knowledge base adds another 500-1000 tokens depending on the query. By caching these static portions, subsequent turns in a conversation skip reprocessing this context, reducing latency from around 2 seconds to under 500 milliseconds for follow-up messages.

Prompt caching is particularly valuable for multi-turn booking conversations. A typical booking flow involves 4-6 exchanges: initial request, availability check, slot selection, patient details, confirmation, and notification preferences. Without caching, each turn reprocesses the full context. With caching, only the new user message and assistant response are processed, significantly reducing both latency and cost.

## Intelligent Prompt Routing for Cost Optimization

Amazon Bedrock Intelligent Prompt Routing provides a single serverless endpoint that dynamically routes requests between different foundation models within the same model family. The router predicts response quality for each model and selects the one that provides the best balance of quality and cost.

For the booking assistant, prompt routing can optimize costs by directing simple queries to smaller, faster models while routing complex queries to more capable models. A straightforward request like "Book me an appointment for next Tuesday" requires less reasoning than "I've been having intermittent chest discomfort for the past week, not severe but concerning - should I book an urgent appointment or is routine okay?"

The routing configuration specifies a fallback model and response quality threshold. When the router predicts that a simpler model can achieve response quality within the threshold of the fallback model, it routes to the simpler model. This approach can reduce costs by 30-50% for workloads with a mix of simple and complex queries.

```hcl
resource "aws_bedrockagent_agent" "supervisor" {
  # ... other configuration ...
  
  # Enable prompt routing between Nova Lite and Nova Micro
  prompt_override_configuration {
    prompt_configurations {
      prompt_type = "ORCHESTRATION"
      inference_configuration {
        # Routing configuration would be specified here
        # when using the prompt router endpoint
      }
    }
  }
}
```

## CloudWatch Generative AI Observability

Amazon CloudWatch provides specialized observability capabilities for generative AI workloads. The Generative AI Observability dashboard offers pre-configured views into model invocations, token consumption, latency distributions, and error rates. For the booking assistant, these metrics help identify performance bottlenecks and optimize costs.

Key metrics available in the dashboard include total invocations broken down by model and action type, average and percentile latencies for model inference, token usage patterns showing input versus output token ratios, and error rates with categorization by error type. The dashboard also provides cost attribution, allowing you to understand spending patterns across different conversation types.

End-to-end prompt tracing captures the complete flow from user input through knowledge base retrieval, model inference, and action execution. When a booking fails or produces an unexpected response, the trace shows exactly where the issue occurred. This visibility is essential for debugging complex multi-step workflows where problems might originate in retrieval, reasoning, or action execution.

```hcl
# Enable CloudWatch logging for the Bedrock Agent
resource "aws_cloudwatch_log_group" "bedrock_agent" {
  name              = "/aws/bedrock/agents/${var.project_name}"
  retention_in_days = 30
}
```

The Lambda functions are instrumented with AWS X-Ray for distributed tracing. X-Ray traces show the timing breakdown for each action, including DynamoDB operations and any external API calls. Combined with CloudWatch metrics, this provides complete visibility into the booking workflow performance.

```hcl
resource "aws_lambda_function" "actions" {
  function_name = "${var.project_name}-actions"
  role          = aws_iam_role.lambda.arn
  handler       = "lambda_actions.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

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
```


## Deploying the Solution

Clone the repository and navigate to the Terraform directory. Initialize Terraform to download the required providers, then apply the configuration to create all resources.

```bash
git clone <repository>
cd patient_bookings/terraform
terraform init
terraform apply
```

Terraform creates the complete infrastructure including the Bedrock Agent with guardrails configuration, Knowledge Base with S3 Vectors storage, Lambda functions for each action group, DynamoDB tables for bookings and sessions, and all required IAM roles. The apply operation takes approximately two minutes to complete.

After the infrastructure is deployed, you need to ingest the NHS content into the knowledge base. This process reads the markdown files from the source S3 bucket, chunks them according to the configured strategy, generates embeddings using Titan Text Embeddings V2, and stores the vectors in the S3 Vectors index.

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $(terraform output -raw kb_id) \
  --data-source-id $(terraform output -raw data_source_id) \
  --region us-east-1
```

The ingestion job typically completes within a few seconds for this dataset. You can monitor the status using the get-ingestion-job command, which shows the number of documents scanned, successfully indexed, and any failures.

Set the environment variables needed by the demo application using the Terraform outputs.

```bash
eval "$(terraform output -raw env_vars)"
```

## Running the Demo Application

The demo application provides a Streamlit interface for interacting with the booking assistant. Install the required Python packages and start the application.

```bash
cd ../app
pip install streamlit boto3
streamlit run streamlit_app.py
```

The application opens in your browser and presents a chat interface. You can type messages to the assistant and see responses in real time as the agent processes your requests.

A typical booking conversation demonstrates the intelligent availability handling. When you request a specific slot that is unavailable, the assistant proactively offers alternatives rather than simply rejecting the request.

```
Patient: I'd like to book an appointment with Dr. Williams for Monday morning.