"""Lambda handler for Bedrock Agent action groups.

Handles booking, approval, and notification actions.
"""

import json
import os
import uuid
from datetime import datetime, timedelta

import boto3

# Initialize clients
dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")
sns = boto3.client("sns")

BOOKINGS_TABLE = os.environ.get("BOOKINGS_TABLE", "nhs-booking-demo-bookings")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "nhs-booking-demo-sessions")


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
