"""Lambda handler for Bedrock Agent action groups.

Handles booking, approval, and notification actions.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import boto3

# Initialize clients
dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")
sns = boto3.client("sns")
location = boto3.client("geo-places")

# Optional: For web search fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

BOOKINGS_TABLE = os.environ.get("BOOKINGS_TABLE", "nhs-booking-demo-bookings")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "nhs-booking-demo-sessions")
PRESCRIPTIONS_TABLE = os.environ.get("PRESCRIPTIONS_TABLE", "nhs-booking-demo-prescriptions")
REFERRALS_TABLE = os.environ.get("REFERRALS_TABLE", "nhs-booking-demo-referrals")


def handler(event, context):
    """Main Lambda handler for Bedrock Agent actions."""
    
    print(f"Event: {json.dumps(event)}")
    
    # Extract action details
    action_group = event.get("actionGroup", "")
    api_path = event.get("apiPath", "")
    parameters = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])
    
    # Convert parameters list to dict
    params = {p["name"]: p["value"] for p in parameters}
    
    # Route to appropriate handler
    handlers = {
        # Booking actions
        "/check-availability": check_availability,
        "/create-booking": create_booking,
        # Approval actions
        "/validate-booking": validate_booking,
        "/approve-booking": approve_booking,
        # Notification actions
        "/send-confirmation": send_confirmation,
        "/send-letter": send_letter,
        # Location actions
        "/find-nearby-hospitals": find_nearby_hospitals,
        "/find-nearby-pharmacies": find_nearby_pharmacies,
        # Referral actions
        "/validate-referral": validate_referral,
        "/create-referral": create_referral,
        # Prescription actions
        "/request-prescription": request_prescription,
        "/check-prescription-status": check_prescription_status,
        "/request-pharmacy-delivery": request_pharmacy_delivery,
    }
    
    handler_func = handlers.get(api_path)
    if handler_func:
        result = handler_func(params)
    else:
        result = {"error": f"Unknown action: {api_path}"}
    
    # Format response for Bedrock Agent
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": "POST",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result)
                }
            }
        }
    }


# ============ Booking Actions ============

def check_availability(params):
    """Check available appointment slots."""
    
    appointment_type = params.get("appointment_type", "gp")
    preferred_date = params.get("preferred_date", "")
    urgency = params.get("urgency", "routine")
    
    # Generate mock availability (in production, query real system)
    today = datetime.now()
    slots = []
    
    if urgency == "urgent":
        # Same day or next day for urgent
        for i in range(2):
            date = today + timedelta(days=i)
            slots.append({
                "date": date.strftime("%Y-%m-%d"),
                "time": "09:30" if i == 0 else "14:00",
                "doctor": "Dr. Smith (Duty GP)",
                "type": "urgent"
            })
    else:
        # 1-2 weeks out for routine
        for i in range(7, 14, 2):
            date = today + timedelta(days=i)
            if date.weekday() < 5:  # Weekdays
                slots.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "time": "10:00",
                    "doctor": "Dr. Johnson" if i % 4 == 0 else "Dr. Williams",
                    "type": "routine"
                })
    
    return {
        "available_slots": slots[:3],
        "appointment_type": appointment_type,
        "message": f"Found {len(slots[:3])} available slots for {appointment_type} appointment"
    }


def create_booking(params):
    """Create a new booking."""
    
    booking_id = f"NHS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    booking = {
        "booking_id": booking_id,
        "patient_name": params.get("patient_name", "Unknown"),
        "appointment_type": params.get("appointment_type", "gp"),
        "date": params.get("date", ""),
        "time": params.get("time", ""),
        "reason": params.get("reason", ""),
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    # Save to DynamoDB
    try:
        table = dynamodb.Table(BOOKINGS_TABLE)
        table.put_item(Item=booking)
    except Exception as e:
        print(f"DynamoDB error: {e}")
    
    return {
        "booking_id": booking_id,
        "status": "pending",
        "message": f"Booking {booking_id} created. Awaiting approval."
    }


# ============ Approval Actions ============

def validate_booking(params):
    """Validate a booking request."""
    
    booking_id = params.get("booking_id", "")
    
    # Get booking from DynamoDB
    try:
        table = dynamodb.Table(BOOKINGS_TABLE)
        response = table.get_item(Key={"booking_id": booking_id})
        booking = response.get("Item", {})
    except Exception:
        booking = {}
    
    if not booking:
        return {"valid": False, "reason": "Booking not found"}
    
    # Simple validation rules
    issues = []
    
    if not booking.get("patient_name"):
        issues.append("Patient name required")
    if not booking.get("date"):
        issues.append("Appointment date required")
    if not booking.get("time"):
        issues.append("Appointment time required")
    
    if issues:
        return {
            "valid": False,
            "booking_id": booking_id,
            "issues": issues
        }
    
    return {
        "valid": True,
        "booking_id": booking_id,
        "message": "Booking validated successfully"
    }


def approve_booking(params):
    """Approve a validated booking."""
    
    booking_id = params.get("booking_id", "")
    
    # Update booking status
    try:
        table = dynamodb.Table(BOOKINGS_TABLE)
        table.update_item(
            Key={"booking_id": booking_id},
            UpdateExpression="SET #status = :status, approved_at = :time",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "approved",
                ":time": datetime.now().isoformat()
            }
        )
        
        # Get updated booking
        response = table.get_item(Key={"booking_id": booking_id})
        booking = response.get("Item", {})
        
    except Exception as e:
        print(f"Approval error: {e}")
        return {"approved": False, "error": str(e)}
    
    return {
        "approved": True,
        "booking_id": booking_id,
        "date": booking.get("date", ""),
        "time": booking.get("time", ""),
        "message": f"Booking {booking_id} has been approved and confirmed."
    }


# ============ Notification Actions ============

def send_confirmation(params):
    """Send booking confirmation via email and SMS."""
    
    booking_id = params.get("booking_id", "")
    email = params.get("email", "")
    phone = params.get("phone", "")
    
    # Get booking details
    try:
        table = dynamodb.Table(BOOKINGS_TABLE)
        response = table.get_item(Key={"booking_id": booking_id})
        booking = response.get("Item", {})
    except Exception:
        booking = {}
    
    if not booking:
        return {"sent": False, "error": "Booking not found"}
    
    # Format confirmation message
    message = f"""
NHS Appointment Confirmation

Reference: {booking_id}
Date: {booking.get('date', 'TBC')}
Time: {booking.get('time', 'TBC')}
Type: {booking.get('appointment_type', 'GP').upper()} Appointment

Please arrive 10 minutes early.
To cancel, call the surgery or reply to this message.
    """.strip()
    
    sent_to = []
    
    # Send email (demo - would use SES in production)
    if email:
        print(f"[DEMO] Would send email to {email}")
        sent_to.append(f"email:{email}")
    
    # Send SMS (demo - would use SNS in production)
    if phone:
        print(f"[DEMO] Would send SMS to {phone}")
        sent_to.append(f"sms:{phone}")
    
    return {
        "sent": True,
        "booking_id": booking_id,
        "sent_to": sent_to,
        "message": "Confirmation sent successfully"
    }


def send_letter(params):
    """Send a letter via email."""
    
    booking_id = params.get("booking_id", "")
    letter_type = params.get("letter_type", "confirmation")
    email = params.get("email", "")
    
    # Get booking details
    try:
        table = dynamodb.Table(BOOKINGS_TABLE)
        response = table.get_item(Key={"booking_id": booking_id})
        booking = response.get("Item", {})
    except Exception:
        booking = {}
    
    # Generate letter content based on type
    letters = {
        "confirmation": f"""
Dear {booking.get('patient_name', 'Patient')},

This letter confirms your appointment.

Reference: {booking_id}
Date: {booking.get('date', 'TBC')}
Time: {booking.get('time', 'TBC')}

Please bring any relevant documents or test results.

Yours sincerely,
NHS Patient Booking System
        """,
        "referral": f"""
Dear Colleague,

I am referring {booking.get('patient_name', 'this patient')} for specialist assessment.

Reason: {booking.get('reason', 'As discussed')}

Please arrange an appointment at your earliest convenience.

Yours sincerely,
GP Surgery
        """,
        "follow-up": f"""
Dear {booking.get('patient_name', 'Patient')},

Following your recent appointment, please note the following:

{booking.get('reason', 'Please contact the surgery if you have any questions.')}

Yours sincerely,
NHS Patient Booking System
        """
    }
    
    letter_content = letters.get(letter_type, letters["confirmation"])
    
    print(f"[DEMO] Would send {letter_type} letter to {email}")
    
    return {
        "sent": True,
        "booking_id": booking_id,
        "letter_type": letter_type,
        "message": f"{letter_type.title()} letter sent to {email}"
    }


# ============ Location Actions ============

def find_nearby_hospitals(params):
    """Find nearby hospitals using Amazon Location Service with web search fallback.
    
    Requires patient address to geocode and find nearby NHS facilities.
    Returns hospital name, full address, distance, phone, and services.
    """
    
    patient_name = params.get("patient_name", "")
    patient_address = params.get("patient_address", "")
    max_results = int(params.get("max_results", 5))
    
    if not patient_address:
        return {
            "success": False,
            "error": "Patient address is required to find nearby hospitals",
            "required_info": ["patient_name", "patient_address"]
        }
    
    try:
        # First, geocode the patient's address to get coordinates
        geocode_response = location.geocode(
            QueryText=patient_address,
            MaxResults=1,
            Filter={
                "IncludeCountries": ["GBR"]  # UK only
            }
        )
        
        if not geocode_response.get("ResultItems"):
            return {
                "success": False,
                "error": f"Could not find location for address: {patient_address}",
                "suggestion": "Please provide a more specific UK address including postcode"
            }
        
        # Get coordinates from geocode result
        position = geocode_response["ResultItems"][0]["Position"]
        longitude, latitude = position[0], position[1]
        
        # Search for nearby hospitals
        search_response = location.search_nearby(
            QueryPosition=[longitude, latitude],
            MaxResults=max_results,
            Filter={
                "IncludeCategories": ["hospital", "medical-center", "health-care"]
            }
        )
        
        hospitals = []
        for item in search_response.get("ResultItems", []):
            # Extract full address from response
            addr = item.get("Address", {})
            full_address = addr.get("Label", "")
            if not full_address:
                # Build address from components
                parts = []
                if addr.get("AddressNumber"):
                    parts.append(addr.get("AddressNumber"))
                if addr.get("Street"):
                    parts.append(addr.get("Street"))
                if addr.get("Locality"):
                    parts.append(addr.get("Locality"))
                if addr.get("PostalCode"):
                    parts.append(addr.get("PostalCode"))
                full_address = ", ".join(parts) if parts else "Address not available"
            
            # Extract phone number
            contacts = item.get("Contacts", {})
            phones = contacts.get("Phones", [])
            phone = phones[0].get("Value", "") if phones else ""
            
            hospital = {
                "name": item.get("Title", "Unknown Hospital"),
                "address": full_address,
                "postcode": addr.get("PostalCode", ""),
                "distance_km": round(item.get("Distance", 0) / 1000, 1),
                "phone": phone,
                "services": _get_hospital_services(item.get("Categories", [])),
                "nhs_trust": _extract_nhs_trust(item.get("Title", ""))
            }
            hospitals.append(hospital)
        
        if not hospitals:
            # Fallback to curated NHS hospital data
            return _get_nhs_hospitals_for_area(patient_name, patient_address)
        
        return {
            "success": True,
            "patient_name": patient_name,
            "search_location": patient_address,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "nearby_hospitals": hospitals,
            "message": f"Found {len(hospitals)} NHS facilities near {patient_address}",
            "source": "Amazon Location Service"
        }
        
    except Exception as e:
        # Fallback to curated NHS data
        print(f"Location Service error: {e}")
        return _get_nhs_hospitals_for_area(patient_name, patient_address)


def _get_hospital_services(categories):
    """Map location categories to NHS services."""
    service_map = {
        "hospital": "General Hospital",
        "medical-center": "Medical Centre",
        "health-care": "Healthcare",
        "emergency": "A&E",
        "clinic": "Clinic"
    }
    services = []
    for cat in categories:
        cat_id = cat.get("Id", "").lower() if isinstance(cat, dict) else str(cat).lower()
        if cat_id in service_map:
            services.append(service_map[cat_id])
    return services if services else ["General Healthcare"]


def _extract_nhs_trust(name):
    """Extract NHS Trust name from hospital name."""
    trust_keywords = ["NHS", "Trust", "Foundation"]
    if any(kw in name for kw in trust_keywords):
        return name
    return "NHS"


def _get_nhs_hospitals_for_area(patient_name, patient_address):
    """Return default NHS hospital when Location Service fails."""
    
    # Single default NHS hospital fallback
    default_hospital = {
        "name": "St Thomas' Hospital",
        "address": "Westminster Bridge Road, Lambeth, London SE1 7EH",
        "postcode": "SE1 7EH",
        "distance_km": 2.0,
        "phone": "020 7188 7188",
        "nhs_trust": "Guy's and St Thomas' NHS Foundation Trust",
        "services": ["A&E", "Maternity", "Cancer Care", "Cardiology"]
    }
    
    return {
        "success": True,
        "patient_name": patient_name,
        "search_location": patient_address,
        "nearby_hospitals": [default_hospital],
        "message": "Could not find specific hospitals in your area. Showing default NHS hospital.",
        "source": "NHS Hospital Directory (Default)",
        "note": "For emergencies, call 999. Use NHS 111 to find your nearest hospital."
    }


def _mock_nearby_hospitals(patient_name, patient_address):
    """Legacy function - redirects to new NHS hospital lookup."""
    return _get_nhs_hospitals_for_area(patient_name, patient_address)


# ============ Referral Actions ============

def validate_referral(params):
    """Validate if patient has a GP referral for specialist/hospital booking.
    
    Hospital and specialist appointments typically require a GP referral.
    This checks if a valid referral exists for the patient.
    """
    
    patient_name = params.get("patient_name", "")
    patient_nhs_number = params.get("nhs_number", "")
    specialty = params.get("specialty", "")
    
    if not patient_name and not patient_nhs_number:
        return {
            "valid": False,
            "error": "Patient name or NHS number required",
            "required_info": ["patient_name or nhs_number", "specialty"]
        }
    
    # Check for existing referral in DynamoDB
    try:
        table = dynamodb.Table(REFERRALS_TABLE)
        
        # In production, would query by NHS number or patient name
        # For demo, we'll simulate referral lookup
        if patient_nhs_number:
            response = table.get_item(Key={"referral_id": f"REF-{patient_nhs_number}"})
            referral = response.get("Item")
        else:
            referral = None
            
    except Exception as e:
        print(f"Referral lookup error: {e}")
        referral = None
    
    # Simulate referral validation for demo
    # In production, this would check the NHS Spine or local referral system
    if referral and referral.get("status") == "active":
        return {
            "valid": True,
            "referral_id": referral.get("referral_id"),
            "patient_name": patient_name,
            "specialty": referral.get("specialty"),
            "referring_gp": referral.get("referring_gp"),
            "valid_until": referral.get("valid_until"),
            "message": "Valid GP referral found. You can proceed with specialist booking."
        }
    
    # No referral found - provide guidance
    return {
        "valid": False,
        "patient_name": patient_name,
        "specialty": specialty,
        "reason": "No valid GP referral found for this specialty",
        "guidance": [
            "Most specialist and hospital appointments require a GP referral",
            "Please book a GP appointment first to discuss your condition",
            "Your GP can then refer you to the appropriate specialist",
            "Some services accept self-referral (e.g., sexual health, A&E)"
        ],
        "self_referral_services": [
            "Accident & Emergency (A&E)",
            "Sexual health clinics",
            "NHS talking therapies (IAPT)",
            "Drug and alcohol services"
        ],
        "message": "GP referral required. Please see your GP first or check if self-referral is available."
    }


def create_referral(params):
    """Create a GP referral for specialist appointment.
    
    This would typically be done by the GP, but included for demo completeness.
    """
    
    referral_id = f"REF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    referral = {
        "referral_id": referral_id,
        "patient_name": params.get("patient_name", ""),
        "nhs_number": params.get("nhs_number", ""),
        "specialty": params.get("specialty", ""),
        "referring_gp": params.get("referring_gp", "Dr. Smith"),
        "gp_surgery": params.get("gp_surgery", "Main Street Surgery"),
        "reason": params.get("reason", ""),
        "urgency": params.get("urgency", "routine"),
        "status": "active",
        "valid_until": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "created_at": datetime.now().isoformat()
    }
    
    try:
        table = dynamodb.Table(REFERRALS_TABLE)
        table.put_item(Item=referral)
    except Exception as e:
        print(f"Referral creation error: {e}")
    
    return {
        "success": True,
        "referral_id": referral_id,
        "patient_name": referral["patient_name"],
        "specialty": referral["specialty"],
        "valid_until": referral["valid_until"],
        "message": f"GP referral {referral_id} created. Valid for 90 days. Patient can now book specialist appointment."
    }


# ============ Prescription Actions ============

def request_prescription(params):
    """Request a repeat prescription from GP surgery.
    
    Patients can request repeat prescriptions for ongoing medications.
    """
    
    patient_name = params.get("patient_name", "")
    nhs_number = params.get("nhs_number", "")
    medications = params.get("medications", "")  # Comma-separated list
    gp_surgery = params.get("gp_surgery", "")
    delivery_preference = params.get("delivery_preference", "collect")  # collect or deliver
    pharmacy_name = params.get("pharmacy_name", "")
    patient_address = params.get("patient_address", "")
    
    if not patient_name:
        return {
            "success": False,
            "error": "Patient name is required",
            "required_info": ["patient_name", "medications"]
        }
    
    if not medications:
        return {
            "success": False,
            "error": "Please specify which medications you need",
            "required_info": ["medications"],
            "example": "e.g., 'Metformin 500mg, Lisinopril 10mg'"
        }
    
    prescription_id = f"RX-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Parse medications list
    med_list = [m.strip() for m in medications.split(",")]
    
    prescription = {
        "prescription_id": prescription_id,
        "patient_name": patient_name,
        "nhs_number": nhs_number,
        "medications": med_list,
        "gp_surgery": gp_surgery or "Main Street Surgery",
        "delivery_preference": delivery_preference,
        "pharmacy_name": pharmacy_name,
        "patient_address": patient_address,
        "status": "pending_approval",
        "created_at": datetime.now().isoformat(),
        "estimated_ready": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    }
    
    try:
        table = dynamodb.Table(PRESCRIPTIONS_TABLE)
        table.put_item(Item=prescription)
    except Exception as e:
        print(f"Prescription request error: {e}")
    
    response = {
        "success": True,
        "prescription_id": prescription_id,
        "patient_name": patient_name,
        "medications": med_list,
        "status": "pending_approval",
        "estimated_ready": prescription["estimated_ready"],
        "message": f"Prescription request {prescription_id} submitted. Your GP will review within 48 hours."
    }
    
    if delivery_preference == "deliver" and patient_address:
        response["delivery_info"] = {
            "type": "home_delivery",
            "address": patient_address,
            "pharmacy": pharmacy_name or "To be assigned",
            "note": "Pharmacy will contact you to arrange delivery"
        }
    elif pharmacy_name:
        response["collection_info"] = {
            "type": "pharmacy_collection",
            "pharmacy": pharmacy_name,
            "note": "You will receive SMS when ready for collection"
        }
    
    return response


def check_prescription_status(params):
    """Check the status of a prescription request."""
    
    prescription_id = params.get("prescription_id", "")
    patient_name = params.get("patient_name", "")
    
    if not prescription_id and not patient_name:
        return {
            "success": False,
            "error": "Prescription ID or patient name required"
        }
    
    try:
        table = dynamodb.Table(PRESCRIPTIONS_TABLE)
        if prescription_id:
            response = table.get_item(Key={"prescription_id": prescription_id})
            prescription = response.get("Item")
        else:
            prescription = None
    except Exception as e:
        print(f"Prescription lookup error: {e}")
        prescription = None
    
    if prescription:
        return {
            "success": True,
            "prescription_id": prescription["prescription_id"],
            "patient_name": prescription["patient_name"],
            "medications": prescription["medications"],
            "status": prescription["status"],
            "estimated_ready": prescription.get("estimated_ready"),
            "pharmacy": prescription.get("pharmacy_name", "Not assigned"),
            "delivery_preference": prescription.get("delivery_preference")
        }
    
    # Demo response for unknown prescriptions
    return {
        "success": True,
        "prescription_id": prescription_id or "Unknown",
        "patient_name": patient_name,
        "status": "not_found",
        "message": "No prescription found. Please check the reference number or contact your GP surgery."
    }


def request_pharmacy_delivery(params):
    """Request prescription delivery to home or specify collection pharmacy.
    
    Allows patients to choose between home delivery or pharmacy collection.
    """
    
    prescription_id = params.get("prescription_id", "")
    patient_name = params.get("patient_name", "")
    delivery_type = params.get("delivery_type", "collect")  # "deliver" or "collect"
    patient_address = params.get("patient_address", "")
    patient_postcode = params.get("patient_postcode", "")
    preferred_pharmacy = params.get("preferred_pharmacy", "")
    
    if not patient_name:
        return {
            "success": False,
            "error": "Patient name is required",
            "required_info": ["patient_name", "delivery_type"]
        }
    
    if delivery_type == "deliver" and not patient_address and not patient_postcode:
        return {
            "success": False,
            "error": "Delivery address required for home delivery",
            "required_info": ["patient_address or patient_postcode"],
            "alternative": "Choose 'collect' to pick up from a pharmacy instead"
        }
    
    delivery_id = f"DEL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    if delivery_type == "deliver":
        # Home delivery
        full_address = patient_address or patient_postcode
        
        return {
            "success": True,
            "delivery_id": delivery_id,
            "prescription_id": prescription_id,
            "patient_name": patient_name,
            "delivery_type": "home_delivery",
            "delivery_address": full_address,
            "estimated_delivery": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "delivery_window": "9am - 6pm",
            "tracking": "SMS updates will be sent",
            "message": f"Home delivery arranged to {full_address}. Expected within 3 working days."
        }
    else:
        # Pharmacy collection
        if preferred_pharmacy:
            pharmacy = preferred_pharmacy
        else:
            # Suggest nearest pharmacy based on postcode
            pharmacy = "Boots Pharmacy, High Street" if patient_postcode else "Your nominated pharmacy"
        
        return {
            "success": True,
            "delivery_id": delivery_id,
            "prescription_id": prescription_id,
            "patient_name": patient_name,
            "delivery_type": "pharmacy_collection",
            "pharmacy": pharmacy,
            "ready_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "collection_hours": "Mon-Sat 9am-6pm",
            "message": f"Prescription will be ready for collection at {pharmacy}. You'll receive SMS when ready."
        }


def find_nearby_pharmacies(params):
    """Find nearby pharmacies for prescription collection.
    
    Uses patient address/postcode to find convenient pharmacies via Amazon Location Service.
    If search fails, prompts user to provide pharmacy name and address.
    """
    
    patient_name = params.get("patient_name", "")
    patient_address = params.get("patient_address", "")
    patient_postcode = params.get("patient_postcode", "")
    preferred_pharmacy = params.get("preferred_pharmacy", "")
    pharmacy_address = params.get("pharmacy_address", "")
    max_results = int(params.get("max_results", 5))
    
    search_location = patient_address or patient_postcode
    
    # If user provided specific pharmacy details, use those
    if preferred_pharmacy and pharmacy_address:
        return {
            "success": True,
            "patient_name": patient_name,
            "search_location": search_location or "User provided",
            "nearby_pharmacies": [{
                "name": preferred_pharmacy,
                "address": pharmacy_address,
                "postcode": _extract_postcode_from_address(pharmacy_address),
                "distance_km": 0.0,
                "phone": "Contact pharmacy directly",
                "opening_hours": "Contact pharmacy for hours",
                "delivery_available": True,
                "services": ["NHS Prescriptions", "Repeat Prescriptions"],
                "user_provided": True
            }],
            "message": f"Using your preferred pharmacy: {preferred_pharmacy}",
            "source": "User provided"
        }
    
    # If user provided pharmacy name but no address, use fictitious address
    if preferred_pharmacy and not pharmacy_address:
        return {
            "success": True,
            "patient_name": patient_name,
            "search_location": search_location or "Not provided",
            "nearby_pharmacies": [{
                "name": preferred_pharmacy,
                "address": "Please confirm address with pharmacy",
                "postcode": "",
                "distance_km": 0.0,
                "phone": "Contact pharmacy directly",
                "opening_hours": "Contact pharmacy for hours",
                "delivery_available": True,
                "services": ["NHS Prescriptions", "Repeat Prescriptions"],
                "user_provided": True
            }],
            "message": f"Using your preferred pharmacy: {preferred_pharmacy}. Please confirm the address when collecting.",
            "source": "User provided"
        }
    
    if not search_location:
        return {
            "success": False,
            "error": "Address or postcode required to find nearby pharmacies",
            "required_info": ["patient_address or patient_postcode"],
            "alternative": "Please provide your preferred pharmacy name and address instead"
        }
    
    try:
        # Try Amazon Location Service
        geocode_response = location.geocode(
            QueryText=search_location,
            MaxResults=1,
            Filter={"IncludeCountries": ["GBR"]}
        )
        
        if geocode_response.get("ResultItems"):
            position = geocode_response["ResultItems"][0]["Position"]
            longitude, latitude = position[0], position[1]
            
            search_response = location.search_nearby(
                QueryPosition=[longitude, latitude],
                MaxResults=max_results,
                Filter={"IncludeCategories": ["pharmacy", "drugstore"]}
            )
            
            pharmacies = []
            for item in search_response.get("ResultItems", []):
                # Extract full address
                addr = item.get("Address", {})
                full_address = addr.get("Label", "")
                if not full_address:
                    parts = []
                    if addr.get("AddressNumber"):
                        parts.append(addr.get("AddressNumber"))
                    if addr.get("Street"):
                        parts.append(addr.get("Street"))
                    if addr.get("Locality"):
                        parts.append(addr.get("Locality"))
                    if addr.get("PostalCode"):
                        parts.append(addr.get("PostalCode"))
                    full_address = ", ".join(parts) if parts else "Address not available"
                
                # Extract phone
                contacts = item.get("Contacts", {})
                phones = contacts.get("Phones", [])
                phone = phones[0].get("Value", "") if phones else ""
                
                # Extract opening hours if available
                opening_hours = item.get("OpeningHours", {})
                hours_display = _format_opening_hours(opening_hours)
                
                pharmacies.append({
                    "name": item.get("Title", "Unknown Pharmacy"),
                    "address": full_address,
                    "postcode": addr.get("PostalCode", ""),
                    "distance_km": round(item.get("Distance", 0) / 1000, 1),
                    "phone": phone,
                    "opening_hours": hours_display,
                    "delivery_available": True,
                    "services": ["NHS Prescriptions", "Repeat Prescriptions"]
                })
            
            if pharmacies:
                return {
                    "success": True,
                    "patient_name": patient_name,
                    "search_location": search_location,
                    "nearby_pharmacies": pharmacies,
                    "message": f"Found {len(pharmacies)} pharmacies near {search_location}",
                    "source": "Amazon Location Service"
                }
            
    except Exception as e:
        print(f"Location Service error: {e}")
    
    # Web search failed - prompt user for pharmacy details or use fictitious
    return _prompt_for_pharmacy_or_use_default(patient_name, search_location)


def _prompt_for_pharmacy_or_use_default(patient_name, search_location):
    """When pharmacy search fails, use Lloyds Pharmacy as default."""
    
    return {
        "success": True,
        "patient_name": patient_name,
        "search_location": search_location,
        "search_failed": True,
        "nearby_pharmacies": [{
            "name": "LloydsPharmacy",
            "address": "High Street, London",
            "postcode": "",
            "distance_km": 0.5,
            "phone": "0345 121 8000",
            "opening_hours": "Mon-Sat 9am-6pm",
            "delivery_available": True,
            "services": ["NHS Prescriptions", "Repeat Prescriptions", "Flu Vaccination"],
            "is_default": True
        }],
        "message": "Could not find specific pharmacies in your area. Using LloydsPharmacy as default.",
        "prompt_user": "If you have a preferred pharmacy, please provide the name and address.",
        "required_for_specific": ["preferred_pharmacy", "pharmacy_address"],
        "source": "Default - LloydsPharmacy"
    }


def _extract_postcode_from_address(address):
    """Extract UK postcode from address string."""
    import re
    postcode_pattern = r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2})\b'
    match = re.search(postcode_pattern, address.upper())
    return match.group(1) if match else ""


def _format_opening_hours(opening_hours):
    """Format opening hours from Location Service response."""
    if not opening_hours:
        return "Contact pharmacy for hours"
    
    # Try to extract display string
    display = opening_hours.get("Display", [])
    if display:
        return "; ".join(display[:3])
    
    return "Mon-Sat 9am-6pm (typical)"


def _mock_nearby_pharmacies(patient_name, search_location):
    """Legacy function - redirects to prompt for pharmacy."""
    return _prompt_for_pharmacy_or_use_default(patient_name, search_location)
