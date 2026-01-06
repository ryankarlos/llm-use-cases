# Bedrock Knowledge Base with S3 Vectors
# Cost-effective vector storage for NHS documentation RAG

# S3 bucket for source documents (NHS content)
resource "aws_s3_bucket" "kb_source" {
  bucket        = "${var.project_name}-kb-source-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

# Upload NHS content to source bucket
resource "aws_s3_object" "nhs_appointments" {
  bucket  = aws_s3_bucket.kb_source.id
  key     = "nhs_content/appointments.md"
  content = <<-EOT
# NHS Appointment Types

## GP Appointments
- Routine appointments: Usually available within 1-2 weeks
- Urgent appointments: Same day or next day for urgent issues
- Telephone consultations: Quick advice without visiting surgery

## Specialist Referrals
- Referrals made by your GP
- Waiting times vary by specialty
- Two-week wait for suspected cancer

## What to Bring
- NHS number if known
- List of current medications
- Any relevant test results

## Cancellation Policy
- Please cancel at least 24 hours in advance
- Missed appointments waste NHS resources
EOT
}

resource "aws_s3_object" "nhs_services" {
  bucket  = aws_s3_bucket.kb_source.id
  key     = "nhs_content/services.md"
  content = <<-EOT
# NHS Services Overview

## Primary Care
- GP surgeries for general health concerns
- Walk-in centres for minor illnesses
- NHS 111 for urgent medical advice

## Emergency Services
- A&E for life-threatening emergencies
- Call 999 for immediate danger
- Minor injuries units for non-life-threatening injuries

## Mental Health
- IAPT services for anxiety and depression
- Crisis teams for urgent mental health support
- Community mental health teams

## Pharmacy Services
- Minor ailment consultations
- Prescription collection
- Health advice
EOT
}

resource "aws_s3_object" "nhs_patient_flow" {
  bucket  = aws_s3_bucket.kb_source.id
  key     = "nhs_content/patient_flow.md"
  content = <<-EOT
# Patient Flow and Booking Process

## Booking an Appointment
1. Contact your GP surgery by phone or online
2. Describe your symptoms to the receptionist
3. You may be offered telephone triage first
4. Appointment booked based on clinical need

## On the Day
1. Arrive 10 minutes before your appointment
2. Check in at reception or self-service kiosk
3. Wait to be called by your clinician
4. Consultation typically lasts 10-15 minutes

## After Your Appointment
- Collect any prescriptions from pharmacy
- Book follow-up appointments if needed
- Access your records via NHS App

## Improving Patient Flow
- Book appropriate appointment type
- Cancel if you can't attend
- Use NHS 111 for advice before booking
EOT
}

# S3 Vectors - Vector Bucket
resource "aws_s3vectors_vector_bucket" "nhs" {
  vector_bucket_name = "${var.project_name}-vectors"
  force_destroy      = true
}

# S3 Vectors - Index (Titan Embed v2 uses 1024 dimensions)
resource "aws_s3vectors_index" "nhs" {
  index_name         = "${var.project_name}-index"
  vector_bucket_name = aws_s3vectors_vector_bucket.nhs.vector_bucket_name

  data_type       = "float32"
  dimension       = 1024
  distance_metric = "cosine"
}

# IAM Role for Knowledge Base
resource "aws_iam_role" "kb_role" {
  name = "${var.project_name}-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}


resource "aws_iam_role_policy" "kb_policy" {
  name = "${var.project_name}-kb-policy"
  role = aws_iam_role.kb_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.kb_source.arn,
          "${aws_s3_bucket.kb_source.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3vectors:CreateIndex",
          "s3vectors:DeleteIndex",
          "s3vectors:GetIndex",
          "s3vectors:ListIndexes",
          "s3vectors:PutVectors",
          "s3vectors:GetVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:QueryVectors"
        ]
        Resource = [
          aws_s3vectors_vector_bucket.nhs.vector_bucket_arn,
          "${aws_s3vectors_vector_bucket.nhs.vector_bucket_arn}/*",
          aws_s3vectors_index.nhs.index_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      }
    ]
  })
}

# Bedrock Knowledge Base with S3 Vectors storage
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

  depends_on = [aws_iam_role_policy.kb_policy]
}

# Data Source - S3 bucket with NHS content
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

  depends_on = [
    aws_s3_object.nhs_appointments,
    aws_s3_object.nhs_services,
    aws_s3_object.nhs_patient_flow
  ]
}

# Associate Knowledge Base with Agent
resource "aws_bedrockagent_agent_knowledge_base_association" "nhs" {
  agent_id             = aws_bedrockagent_agent.supervisor.agent_id
  knowledge_base_id    = aws_bedrockagent_knowledge_base.nhs.id
  description          = "NHS services and appointment information"
  knowledge_base_state = "ENABLED"
}

# Outputs
output "kb_id" {
  description = "Knowledge Base ID"
  value       = aws_bedrockagent_knowledge_base.nhs.id
}

output "kb_source_bucket" {
  description = "S3 bucket containing NHS source documents"
  value       = aws_s3_bucket.kb_source.id
}

output "s3_vectors_bucket" {
  description = "S3 Vectors bucket name"
  value       = aws_s3vectors_vector_bucket.nhs.vector_bucket_name
}

output "s3_vectors_index" {
  description = "S3 Vectors index ARN"
  value       = aws_s3vectors_index.nhs.index_arn
}

output "data_source_id" {
  description = "Data Source ID"
  value       = aws_bedrockagent_data_source.nhs.data_source_id
}
