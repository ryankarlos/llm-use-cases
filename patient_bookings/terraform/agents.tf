# Bedrock Agent for NHS Patient Booking Demo
# Simple agent with booking actions

# Supervisor Agent
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
    2. For NHS information, direct patients to nhs.uk website
    3. Be polite, professional, and reassuring
    4. Keep patients updated on what you're doing

    BOOKING WORKFLOW:
    1. Understand the patient's booking need (GP or specialist)
    2. Check availability using the checkAvailability action
    3. Create the booking using createBooking action
    4. Approve it using approveBooking action
    5. Send confirmation using sendConfirmation action

    EMERGENCY: For urgent symptoms (chest pain, breathing difficulty, stroke signs), 
    immediately advise calling 999 - do NOT proceed with booking.

    When patients ask about NHS services or health topics, provide general guidance
    and recommend they visit nhs.uk for detailed information. You cannot give medical advice.
  EOT

  description = "NHS Patient Booking Assistant"
}

# Prepare agent after creation
resource "null_resource" "prepare_agent" {
  depends_on = [
    aws_bedrockagent_agent.supervisor,
    aws_bedrockagent_agent_action_group.booking
  ]

  provisioner "local-exec" {
    command = "sleep 10 && aws bedrock-agent prepare-agent --agent-id ${aws_bedrockagent_agent.supervisor.agent_id} --region ${var.aws_region}"
  }
}

# Agent Alias
resource "aws_bedrockagent_agent_alias" "live" {
  agent_id         = aws_bedrockagent_agent.supervisor.agent_id
  agent_alias_name = "live"
  description      = "Live alias"

  depends_on = [null_resource.prepare_agent]
}

# Action Group for booking operations
resource "aws_bedrockagent_agent_action_group" "booking" {
  agent_id          = aws_bedrockagent_agent.supervisor.agent_id
  agent_version     = "DRAFT"
  action_group_name = "BookingActions"
  description       = "Actions for booking appointments"

  action_group_executor {
    lambda = aws_lambda_function.actions.arn
  }

  api_schema {
    payload = jsonencode({
      openapi = "3.0.0"
      info = {
        title   = "NHS Booking API"
        version = "1.0.0"
      }
      paths = {
        "/check-availability" = {
          post = {
            operationId = "checkAvailability"
            description = "Check available appointment slots for GP or specialist"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      appointment_type = { type = "string", description = "gp or specialist" }
                      urgency          = { type = "string", description = "routine or urgent" }
                    }
                  }
                }
              }
            }
            responses = { "200" = { description = "Available slots returned" } }
          }
        }
        "/create-booking" = {
          post = {
            operationId = "createBooking"
            description = "Create a new appointment booking"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      patient_name     = { type = "string", description = "Patient full name" }
                      appointment_type = { type = "string", description = "gp or specialist" }
                      date             = { type = "string", description = "Date YYYY-MM-DD" }
                      time             = { type = "string", description = "Time HH:MM" }
                      reason           = { type = "string", description = "Reason for appointment" }
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
            description = "Approve and confirm a booking"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      booking_id = { type = "string", description = "Booking reference" }
                    }
                    required = ["booking_id"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Booking approved" } }
          }
        }
        "/send-confirmation" = {
          post = {
            operationId = "sendConfirmation"
            description = "Send booking confirmation via email/SMS"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      booking_id = { type = "string", description = "Booking reference" }
                      email      = { type = "string", description = "Patient email" }
                      phone      = { type = "string", description = "Patient phone" }
                    }
                    required = ["booking_id"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Confirmation sent" } }
          }
        }
      }
    })
  }
}

# Note: Web search/grounding can be enabled at inference time using Nova's 
# nova_grounding system tool when invoking the model directly.
# For this demo, the agent directs users to nhs.uk for health information.
