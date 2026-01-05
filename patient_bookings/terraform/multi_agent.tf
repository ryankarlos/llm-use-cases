# Multi-Agent Collaboration for NHS Patient Booking
# Supervisor agent orchestrates specialist collaborator agents

# ============================================================================
# COLLABORATOR AGENTS - Specialist agents for specific tasks
# ============================================================================

# Triage Agent - Assesses urgency and routes patients appropriately
resource "aws_bedrockagent_agent" "triage" {
  agent_name                  = "${var.project_name}-triage-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  foundation_model            = "amazon.nova-lite-v1:0"
  idle_session_ttl_in_seconds = 300
  prepare_agent               = true

  instruction = <<-EOT
    You are an NHS Triage Specialist. Your role is to assess patient requests and determine urgency.

    TRIAGE CATEGORIES:
    1. EMERGENCY - Chest pain, breathing difficulty, stroke symptoms, severe bleeding
       Action: Immediately advise calling 999, do not proceed with booking
    
    2. URGENT - High fever, severe pain, worsening symptoms, mental health crisis
       Action: Same-day or next-day appointment required
    
    3. ROUTINE - Ongoing conditions, follow-ups, general health concerns
       Action: Standard appointment within 1-2 weeks

    ASSESSMENT PROCESS:
    - Ask clarifying questions about symptoms if needed
    - Consider duration and severity of symptoms
    - Check for red flag symptoms that require emergency care
    - Return urgency level and recommended appointment type

    You do NOT provide medical advice or diagnoses. Only assess urgency for booking purposes.
  EOT

  description = "Triage specialist for assessing patient urgency"
}

resource "aws_bedrockagent_agent_alias" "triage_live" {
  agent_id         = aws_bedrockagent_agent.triage.agent_id
  agent_alias_name = "live"
  description      = "Live alias for triage agent"
}


# Scheduling Agent - Handles availability and booking logistics
resource "aws_bedrockagent_agent" "scheduling" {
  agent_name                  = "${var.project_name}-scheduling-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  foundation_model            = "amazon.nova-lite-v1:0"
  idle_session_ttl_in_seconds = 300
  prepare_agent               = true

  instruction = <<-EOT
    You are an NHS Scheduling Specialist. Your role is to find and book appointments.

    RESPONSIBILITIES:
    1. Check availability based on urgency level from triage
    2. Present multiple options to patients (different times, doctors, locations)
    3. Handle booking conflicts by offering alternatives
    4. Create and confirm bookings

    WHEN SLOTS ARE UNAVAILABLE:
    - Never simply reject a request
    - Offer alternative times on the same day
    - Suggest different doctors with earlier availability
    - Recommend nearby clinics or hospitals
    - For urgent cases, escalate to find emergency slots

    BOOKING CONFIRMATION:
    - Verify all patient details before confirming
    - Provide clear booking reference
    - Explain what to bring to the appointment
  EOT

  description = "Scheduling specialist for booking appointments"
}

resource "aws_bedrockagent_agent_alias" "scheduling_live" {
  agent_id         = aws_bedrockagent_agent.scheduling.agent_id
  agent_alias_name = "live"
  description      = "Live alias for scheduling agent"
}

# Action group for scheduling agent
resource "aws_bedrockagent_agent_action_group" "scheduling_actions" {
  agent_id          = aws_bedrockagent_agent.scheduling.agent_id
  agent_version     = "DRAFT"
  action_group_name = "SchedulingActions"
  description       = "Actions for scheduling appointments"

  action_group_executor {
    lambda = aws_lambda_function.actions.arn
  }

  api_schema {
    payload = jsonencode({
      openapi = "3.0.0"
      info    = { title = "NHS Scheduling API", version = "1.0.0" }
      paths = {
        "/check-availability" = {
          post = {
            operationId = "checkAvailability"
            description = "Check available appointment slots"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      appointment_type = { type = "string" }
                      urgency          = { type = "string" }
                      preferred_date   = { type = "string" }
                      preferred_doctor = { type = "string" }
                    }
                  }
                }
              }
            }
            responses = { "200" = { description = "Available slots" } }
          }
        }
        "/create-booking" = {
          post = {
            operationId = "createBooking"
            description = "Create appointment booking"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      patient_name = { type = "string" }
                      date         = { type = "string" }
                      time         = { type = "string" }
                      doctor       = { type = "string" }
                      reason       = { type = "string" }
                    }
                    required = ["patient_name", "date", "time"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Booking created" } }
          }
        }
        "/approve-booking" = {
          post = {
            operationId = "approveBooking"
            description = "Approve and confirm booking"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      booking_id = { type = "string" }
                    }
                    required = ["booking_id"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Booking approved" } }
          }
        }
      }
    })
  }
}


# Information Agent - Handles NHS knowledge queries
resource "aws_bedrockagent_agent" "information" {
  agent_name                  = "${var.project_name}-info-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  foundation_model            = "amazon.nova-lite-v1:0"
  idle_session_ttl_in_seconds = 300
  prepare_agent               = true

  instruction = <<-EOT
    You are an NHS Information Specialist. Your role is to answer questions about NHS services.

    RESPONSIBILITIES:
    1. Search the knowledge base for NHS information
    2. Explain appointment types (GP, specialist, urgent, routine)
    3. Describe what patients should bring to appointments
    4. Explain the patient flow and booking process
    5. Provide information about nearby facilities

    IMPORTANT:
    - You do NOT provide medical advice
    - For health questions, direct patients to NHS 111 or nhs.uk
    - Always cite the knowledge base when providing information
    - Be helpful and reassuring in your responses
  EOT

  description = "Information specialist for NHS queries"
}

resource "aws_bedrockagent_agent_alias" "information_live" {
  agent_id         = aws_bedrockagent_agent.information.agent_id
  agent_alias_name = "live"
  description      = "Live alias for information agent"
}

# Associate knowledge base with information agent
resource "aws_bedrockagent_agent_knowledge_base_association" "info_kb" {
  agent_id             = aws_bedrockagent_agent.information.agent_id
  knowledge_base_id    = aws_bedrockagent_knowledge_base.nhs.id
  description          = "NHS services and appointment information"
  knowledge_base_state = "ENABLED"
}

# ============================================================================
# SUPERVISOR AGENT - Orchestrates collaborator agents
# ============================================================================

resource "aws_bedrockagent_agent" "supervisor_multi" {
  agent_name                  = "${var.project_name}-supervisor"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  agent_collaboration         = "SUPERVISOR"
  foundation_model            = "amazon.nova-lite-v1:0"
  idle_session_ttl_in_seconds = 600
  prepare_agent               = false # Will prepare after collaborators are added

  instruction = <<-EOT
    You are the NHS Patient Booking Supervisor. You coordinate a team of specialist agents.

    YOUR TEAM:
    1. TRIAGE AGENT - Assesses urgency of patient requests
    2. SCHEDULING AGENT - Handles availability and bookings  
    3. INFORMATION AGENT - Answers questions about NHS services

    WORKFLOW:
    1. Greet the patient warmly
    2. If patient describes symptoms or health concerns:
       - Route to TRIAGE AGENT to assess urgency
       - If emergency, advise 999 immediately
    3. For booking requests:
       - Get urgency from TRIAGE if not already assessed
       - Route to SCHEDULING AGENT to find slots and book
    4. For questions about NHS services:
       - Route to INFORMATION AGENT
    5. Summarize outcomes and confirm next steps with patient

    IMPORTANT:
    - Keep the patient informed about what you're doing
    - Be empathetic and professional
    - Never provide medical advice yourself
    - Ensure smooth handoffs between agents
  EOT

  description = "Supervisor agent orchestrating NHS booking workflow"
}

resource "aws_bedrockagent_agent_alias" "supervisor_multi_live" {
  agent_id         = aws_bedrockagent_agent.supervisor_multi.agent_id
  agent_alias_name = "live"
  description      = "Live alias for supervisor"

  depends_on = [
    aws_bedrockagent_agent_collaborator.triage,
    aws_bedrockagent_agent_collaborator.scheduling,
    aws_bedrockagent_agent_collaborator.information
  ]
}


# ============================================================================
# COLLABORATOR ASSOCIATIONS - Link collaborators to supervisor
# ============================================================================

resource "aws_bedrockagent_agent_collaborator" "triage" {
  agent_id                   = aws_bedrockagent_agent.supervisor_multi.agent_id
  collaborator_name          = "TriageSpecialist"
  collaboration_instruction  = "Route patient symptom descriptions and urgency assessments to this agent. It will determine if the case is emergency, urgent, or routine."
  relay_conversation_history = "TO_COLLABORATOR"

  agent_descriptor {
    alias_arn = aws_bedrockagent_agent_alias.triage_live.agent_alias_arn
  }
}

resource "aws_bedrockagent_agent_collaborator" "scheduling" {
  agent_id                   = aws_bedrockagent_agent.supervisor_multi.agent_id
  collaborator_name          = "SchedulingSpecialist"
  collaboration_instruction  = "Route booking requests to this agent. Provide the urgency level from triage. It will check availability, offer alternatives, and create bookings."
  relay_conversation_history = "TO_COLLABORATOR"

  agent_descriptor {
    alias_arn = aws_bedrockagent_agent_alias.scheduling_live.agent_alias_arn
  }
}

resource "aws_bedrockagent_agent_collaborator" "information" {
  agent_id                   = aws_bedrockagent_agent.supervisor_multi.agent_id
  collaborator_name          = "InformationSpecialist"
  collaboration_instruction  = "Route questions about NHS services, appointment types, what to bring, and general NHS information to this agent."
  relay_conversation_history = "TO_COLLABORATOR"

  agent_descriptor {
    alias_arn = aws_bedrockagent_agent_alias.information_live.agent_alias_arn
  }
}

# Prepare supervisor after collaborators are associated
resource "null_resource" "prepare_supervisor" {
  depends_on = [
    aws_bedrockagent_agent_collaborator.triage,
    aws_bedrockagent_agent_collaborator.scheduling,
    aws_bedrockagent_agent_collaborator.information
  ]

  provisioner "local-exec" {
    command = "sleep 5 && aws bedrock-agent prepare-agent --agent-id ${aws_bedrockagent_agent.supervisor_multi.agent_id} --region ${var.aws_region}"
  }
}

# ============================================================================
# BEDROCK FLOW - Patient Booking Workflow
# ============================================================================

resource "aws_bedrockagent_flow" "booking_flow" {
  name               = "${var.project_name}-booking-flow"
  description        = "NHS patient booking workflow with triage and scheduling"
  execution_role_arn = aws_iam_role.flow_role.arn

  definition {
    # Input node - receives patient request
    node {
      name = "FlowInput"
      type = "Input"
      configuration { input {} }
      output {
        name = "document"
        type = "String"
      }
    }

    # Triage node - assess urgency using agent
    node {
      name = "TriageAssessment"
      type = "Agent"
      configuration {
        agent {
          agent_alias_arn = aws_bedrockagent_agent_alias.triage_live.agent_alias_arn
        }
      }
      input {
        name       = "agentInputText"
        type       = "String"
        expression = "$.data"
      }
      output {
        name = "agentResponse"
        type = "String"
      }
    }

    # Condition node - route based on urgency
    node {
      name = "UrgencyRouter"
      type = "Condition"
      configuration {
        condition {
          condition {
            name       = "IsEmergency"
            expression = "emergency"
          }
          condition {
            name       = "IsUrgent"
            expression = "urgent"
          }
          condition {
            name       = "IsRoutine"
            expression = "default"
          }
        }
      }
      input {
        name       = "urgencyLevel"
        type       = "String"
        expression = "$.data"
      }
    }

    # Emergency output - direct to 999
    node {
      name = "EmergencyOutput"
      type = "Output"
      configuration { output {} }
      input {
        name       = "document"
        type       = "String"
        expression = "$.data"
      }
    }

    # Scheduling node - book appointment
    node {
      name = "ScheduleAppointment"
      type = "Agent"
      configuration {
        agent {
          agent_alias_arn = aws_bedrockagent_agent_alias.scheduling_live.agent_alias_arn
        }
      }
      input {
        name       = "agentInputText"
        type       = "String"
        expression = "$.data"
      }
      output {
        name = "agentResponse"
        type = "String"
      }
    }

    # Final output
    node {
      name = "FlowOutput"
      type = "Output"
      configuration { output {} }
      input {
        name       = "document"
        type       = "String"
        expression = "$.data"
      }
    }

    # Connections
    connection {
      name   = "InputToTriage"
      source = "FlowInput"
      target = "TriageAssessment"
      type   = "Data"
      configuration {
        data {
          source_output = "document"
          target_input  = "agentInputText"
        }
      }
    }

    connection {
      name   = "TriageToRouter"
      source = "TriageAssessment"
      target = "UrgencyRouter"
      type   = "Data"
      configuration {
        data {
          source_output = "agentResponse"
          target_input  = "urgencyLevel"
        }
      }
    }

    connection {
      name   = "RouterToEmergency"
      source = "UrgencyRouter"
      target = "EmergencyOutput"
      type   = "Conditional"
      configuration {
        conditional {
          condition = "IsEmergency"
        }
      }
    }

    connection {
      name   = "RouterToScheduling"
      source = "UrgencyRouter"
      target = "ScheduleAppointment"
      type   = "Conditional"
      configuration {
        conditional {
          condition = "IsUrgent"
        }
      }
    }

    connection {
      name   = "RouterToSchedulingRoutine"
      source = "UrgencyRouter"
      target = "ScheduleAppointment"
      type   = "Conditional"
      configuration {
        conditional {
          condition = "IsRoutine"
        }
      }
    }

    connection {
      name   = "SchedulingToOutput"
      source = "ScheduleAppointment"
      target = "FlowOutput"
      type   = "Data"
      configuration {
        data {
          source_output = "agentResponse"
          target_input  = "document"
        }
      }
    }
  }
}


# ============================================================================
# IAM ROLE FOR FLOWS
# ============================================================================

resource "aws_iam_role" "flow_role" {
  name = "${var.project_name}-flow-role"

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

resource "aws_iam_role_policy" "flow_policy" {
  name = "${var.project_name}-flow-policy"
  role = aws_iam_role.flow_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent",
          "bedrock:GetAgentAlias"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent-alias/*"
        ]
      }
    ]
  })
}

# Update bedrock agent role to allow invoking collaborator agents
resource "aws_iam_role_policy" "bedrock_agent_collaborator" {
  name = "${var.project_name}-agent-collaborator-policy"
  role = aws_iam_role.bedrock_agent.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent",
          "bedrock:GetAgentAlias"
        ]
        Resource = [
          aws_bedrockagent_agent.triage.agent_arn,
          aws_bedrockagent_agent.scheduling.agent_arn,
          aws_bedrockagent_agent.information.agent_arn,
          "${aws_bedrockagent_agent.triage.agent_arn}/*",
          "${aws_bedrockagent_agent.scheduling.agent_arn}/*",
          "${aws_bedrockagent_agent.information.agent_arn}/*"
        ]
      }
    ]
  })
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "supervisor_agent_id" {
  description = "Multi-agent supervisor ID"
  value       = aws_bedrockagent_agent.supervisor_multi.agent_id
}

output "supervisor_alias_id" {
  description = "Multi-agent supervisor alias ID"
  value       = aws_bedrockagent_agent_alias.supervisor_multi_live.agent_alias_id
}

output "booking_flow_id" {
  description = "Booking flow ID"
  value       = aws_bedrockagent_flow.booking_flow.id
}

output "booking_flow_arn" {
  description = "Booking flow ARN"
  value       = aws_bedrockagent_flow.booking_flow.arn
}
