# Bedrock Agent for NHS Patient Booking Demo
# Uses Nova Premier with Web Grounding for real-time search

# Supervisor Agent with Nova Premier and Web Search
resource "aws_bedrockagent_agent" "supervisor" {
  agent_name                  = "${var.project_name}-agent"
  agent_resource_role_arn     = aws_iam_role.bedrock_agent.arn
  foundation_model            = "us.amazon.nova-premier-v1:0"  # Cross-region inference profile for web grounding
  idle_session_ttl_in_seconds = 600
  prepare_agent               = true

  instruction = <<-EOT
    You are an NHS Patient Booking Assistant. Help patients book GP and specialist appointments.

    IMPORTANT RULES:
    1. You do NOT provide medical advice - only help with bookings
    2. Be polite, professional, and reassuring
    3. Keep patients updated on what you're doing

    BOOKING WORKFLOW:
    1. Understand the patient's booking need (GP or specialist)
    2. Check availability using the checkAvailability action
    3. Create the booking using createBooking action
    4. Approve it using approveBooking action
    5. Send confirmation using sendConfirmation action

    FINDING NEARBY HOSPITALS:
    When a patient asks about nearby hospitals, clinics, or NHS facilities:
    1. First ask for their full name if not already provided
    2. Ask for their full address including postcode (e.g., "10 Downing Street, London SW1A 2AA")
    3. Use the findNearbyHospitals action with their name and address
    4. Present the results showing hospital name, distance, and services available

    WEB SEARCH:
    You have access to real-time web search. Use it to:
    - Find current NHS service information and opening hours
    - Look up specific hospital or clinic details
    - Get up-to-date NHS guidance and policies
    - Search for NHS services in specific areas
    Always cite your sources when providing web search results.

    EMERGENCY: For urgent symptoms (chest pain, breathing difficulty, stroke signs), 
    immediately advise calling 999 - do NOT proceed with booking.

    When patients ask about NHS services, appointment types, or patient flow:
    - First search the knowledge base for relevant information
    - Use web search for current/real-time information
    - Always clarify you cannot give medical advice
  EOT

  description = "NHS Patient Booking Assistant with Web Search"
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
        "/find-nearby-hospitals" = {
          post = {
            operationId = "findNearbyHospitals"
            description = "Find nearby NHS hospitals and clinics based on patient address. IMPORTANT: You must ask the patient for their name and full address (including postcode) before calling this action."
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      patient_name    = { type = "string", description = "Patient full name" }
                      patient_address = { type = "string", description = "Patient full address including postcode (e.g., '10 Downing Street, London SW1A 2AA')" }
                      max_results     = { type = "integer", description = "Maximum number of hospitals to return (default 5)" }
                    }
                    required = ["patient_name", "patient_address"]
                  }
                }
              }
            }
            responses = { "200" = { description = "List of nearby hospitals with distance and contact info" } }
          }
        }
      }
    })
  }
}

# Note: Web Grounding is enabled via Nova Premier (us.amazon.nova-premier-v1:0).
# The nova_grounding system tool is automatically available for real-time web search.
# Web Grounding requires the bedrock:InvokeTool permission for the system tool.

# IAM permission for Web Grounding
resource "aws_iam_role_policy" "bedrock_agent_web_grounding" {
  name = "${var.project_name}-agent-web-grounding"
  role = aws_iam_role.bedrock_agent.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["bedrock:InvokeTool"]
      Resource = "arn:aws:bedrock:*:*:system-tool/amazon.nova_grounding"
    }]
  })
}
