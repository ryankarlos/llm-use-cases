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
    You are an NHS Patient Booking Assistant. Help patients book GP and specialist appointments, request prescriptions, and find nearby pharmacies.

    IMPORTANT RULES:
    1. You do NOT provide medical advice - only help with bookings and prescriptions
    2. Be polite, professional, and reassuring
    3. Keep patients updated on what you're doing

    BOOKING WORKFLOW:
    1. Understand the patient's booking need (GP or specialist)
    2. For SPECIALIST/HOSPITAL appointments: Check if patient has GP referral using validateReferral
       - If no referral, explain they need to see GP first (unless self-referral service)
    3. Check availability using the checkAvailability action
    4. Create the booking using createBooking action
    5. Approve it using approveBooking action
    6. Send confirmation using sendConfirmation action

    GP REFERRAL REQUIREMENTS:
    - Most specialist and hospital appointments require a GP referral
    - Always check for valid referral before booking specialist appointments
    - Self-referral services (no GP needed): A&E, sexual health, NHS talking therapies, drug/alcohol services
    - If no referral exists, guide patient to book GP appointment first

    PRESCRIPTION REQUESTS:
    When a patient wants to request a repeat prescription:
    1. Ask for their full name
    2. Ask which medications they need (name and dosage if known)
    3. Use requestPrescription action
    4. Ask if they want home delivery or pharmacy collection
    5. If delivery: ask for full address including postcode
    6. If collection: use findNearbyPharmacies to help them choose, or ask for preferred pharmacy
    7. Use requestPharmacyDelivery to arrange delivery/collection

    FINDING NEARBY HOSPITALS:
    When a patient asks about nearby hospitals, clinics, or NHS facilities:
    1. First ask for their full name if not already provided
    2. Ask for their full address including postcode (e.g., "10 Downing Street, London SW1A 2AA")
    3. Use the findNearbyHospitals action with their name and address
    4. Present the results showing hospital name, distance, and services available

    FINDING NEARBY PHARMACIES:
    When a patient needs to find a pharmacy:
    1. Ask for their address or postcode
    2. Use findNearbyPharmacies action
    3. Show pharmacies with distance, opening hours, and delivery options

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
        "/validate-referral" = {
          post = {
            operationId = "validateReferral"
            description = "Check if patient has a valid GP referral for specialist/hospital appointment. MUST be called before booking specialist appointments."
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      patient_name = { type = "string", description = "Patient full name" }
                      nhs_number   = { type = "string", description = "Patient NHS number (optional)" }
                      specialty    = { type = "string", description = "Specialty being referred to (e.g., cardiology, dermatology)" }
                    }
                    required = ["patient_name"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Referral validation result" } }
          }
        }
        "/request-prescription" = {
          post = {
            operationId = "requestPrescription"
            description = "Request a repeat prescription from GP surgery. Ask patient for medications needed."
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      patient_name        = { type = "string", description = "Patient full name" }
                      nhs_number          = { type = "string", description = "Patient NHS number (optional)" }
                      medications         = { type = "string", description = "Comma-separated list of medications (e.g., 'Metformin 500mg, Lisinopril 10mg')" }
                      gp_surgery          = { type = "string", description = "GP surgery name (optional)" }
                      delivery_preference = { type = "string", description = "'deliver' for home delivery or 'collect' for pharmacy collection" }
                      pharmacy_name       = { type = "string", description = "Preferred pharmacy for collection (optional)" }
                      patient_address     = { type = "string", description = "Full address for home delivery (required if delivery_preference is 'deliver')" }
                    }
                    required = ["patient_name", "medications"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Prescription request submitted" } }
          }
        }
        "/check-prescription-status" = {
          post = {
            operationId = "checkPrescriptionStatus"
            description = "Check the status of a prescription request"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      prescription_id = { type = "string", description = "Prescription reference number" }
                      patient_name    = { type = "string", description = "Patient name (alternative to prescription_id)" }
                    }
                  }
                }
              }
            }
            responses = { "200" = { description = "Prescription status" } }
          }
        }
        "/find-nearby-pharmacies" = {
          post = {
            operationId = "findNearbyPharmacies"
            description = "Find nearby pharmacies for prescription collection. If web search fails, ask patient for their preferred pharmacy name and address."
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      patient_name       = { type = "string", description = "Patient full name" }
                      patient_address    = { type = "string", description = "Patient address" }
                      patient_postcode   = { type = "string", description = "Patient postcode (alternative to full address)" }
                      preferred_pharmacy = { type = "string", description = "Patient's preferred pharmacy name (if search fails or patient has preference)" }
                      pharmacy_address   = { type = "string", description = "Address of preferred pharmacy (if patient provides it)" }
                      max_results        = { type = "integer", description = "Maximum pharmacies to return (default 5)" }
                    }
                    required = ["patient_name"]
                  }
                }
              }
            }
            responses = { "200" = { description = "List of nearby pharmacies" } }
          }
        }
        "/request-pharmacy-delivery" = {
          post = {
            operationId = "requestPharmacyDelivery"
            description = "Arrange prescription delivery to home or collection from pharmacy"
            requestBody = {
              required = true
              content = {
                "application/json" = {
                  schema = {
                    type = "object"
                    properties = {
                      prescription_id    = { type = "string", description = "Prescription reference (optional)" }
                      patient_name       = { type = "string", description = "Patient full name" }
                      delivery_type      = { type = "string", description = "'deliver' for home delivery or 'collect' for pharmacy pickup" }
                      patient_address    = { type = "string", description = "Full delivery address (required for home delivery)" }
                      patient_postcode   = { type = "string", description = "Postcode (alternative to full address)" }
                      preferred_pharmacy = { type = "string", description = "Preferred pharmacy name for collection" }
                    }
                    required = ["patient_name", "delivery_type"]
                  }
                }
              }
            }
            responses = { "200" = { description = "Delivery/collection arrangement confirmed" } }
          }
        }
      }
    })
  }
}

# Note: Web Grounding is enabled via Nova Premier (us.amazon.nova-premier-v1:0).
# The nova_grounding system tool is automatically available for real-time web search.
# Web Grounding IAM permissions are configured in main.tf (bedrock_agent_policy).
