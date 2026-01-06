"""Tests for Lambda action handlers using moto for AWS mocking.

Uses moto to mock DynamoDB instead of manual patching.
"""

import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def dynamodb_tables(aws_credentials):
    """Create mock DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        
        # Create bookings table
        dynamodb.create_table(
            TableName="nhs-booking-demo-bookings",
            KeySchema=[{"AttributeName": "booking_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "booking_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        # Create sessions table
        dynamodb.create_table(
            TableName="nhs-booking-demo-sessions",
            KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        yield dynamodb


class TestCheckAvailabilityMoto:
    """Tests for check_availability using moto."""
    
    def test_routine_availability(self, dynamodb_tables):
        """Test routine appointment availability."""
        from lambda_actions import check_availability
        
        result = check_availability({
            "appointment_type": "gp",
            "urgency": "routine"
        })
        
        assert "available_slots" in result
        assert len(result["available_slots"]) > 0
        assert result["appointment_type"] == "gp"
        # Routine slots should be 1-2 weeks out
        for slot in result["available_slots"]:
            assert slot["type"] == "routine"
    
    def test_urgent_availability(self, dynamodb_tables):
        """Test urgent appointment availability."""
        from lambda_actions import check_availability
        
        result = check_availability({
            "appointment_type": "gp",
            "urgency": "urgent"
        })
        
        assert "available_slots" in result
        for slot in result["available_slots"]:
            assert slot["type"] == "urgent"
    
    def test_specialist_availability(self, dynamodb_tables):
        """Test specialist appointment availability."""
        from lambda_actions import check_availability
        
        result = check_availability({
            "appointment_type": "specialist",
            "urgency": "routine"
        })
        
        assert "available_slots" in result
        assert result["appointment_type"] == "specialist"


class TestCreateBookingMoto:
    """Tests for create_booking using moto."""
    
    def test_create_booking_saves_to_dynamodb(self, dynamodb_tables):
        """Test booking is saved to DynamoDB."""
        from lambda_actions import create_booking
        
        result = create_booking({
            "patient_name": "John Smith",
            "appointment_type": "gp",
            "date": "2026-01-15",
            "time": "10:00",
            "reason": "Annual checkup"
        })
        
        assert "booking_id" in result
        assert result["status"] == "pending"
        
        # Verify it was saved to DynamoDB
        table = dynamodb_tables.Table("nhs-booking-demo-bookings")
        item = table.get_item(Key={"booking_id": result["booking_id"]})
        
        assert "Item" in item
        assert item["Item"]["patient_name"] == "John Smith"
        assert item["Item"]["appointment_type"] == "gp"
        assert item["Item"]["date"] == "2026-01-15"
    
    def test_booking_id_format(self, dynamodb_tables):
        """Test booking ID follows NHS format."""
        from lambda_actions import create_booking
        
        result = create_booking({"patient_name": "Test Patient"})
        
        booking_id = result["booking_id"]
        assert booking_id.startswith("NHS-")
        parts = booking_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # Random hex
    
    def test_create_multiple_bookings(self, dynamodb_tables):
        """Test creating multiple bookings generates unique IDs."""
        from lambda_actions import create_booking
        
        booking_ids = set()
        for i in range(5):
            result = create_booking({"patient_name": f"Patient {i}"})
            booking_ids.add(result["booking_id"])
        
        assert len(booking_ids) == 5  # All unique


class TestValidateBookingMoto:
    """Tests for validate_booking using moto."""
    
    def test_validate_complete_booking(self, dynamodb_tables):
        """Test validation of complete booking."""
        from lambda_actions import validate_booking
        
        # First create a booking
        table = dynamodb_tables.Table("nhs-booking-demo-bookings")
        table.put_item(Item={
            "booking_id": "NHS-20260115-ABC123",
            "patient_name": "John Smith",
            "date": "2026-01-15",
            "time": "10:00",
            "status": "pending"
        })
        
        result = validate_booking({"booking_id": "NHS-20260115-ABC123"})
        
        assert result["valid"] is True
    
    def test_validate_incomplete_booking(self, dynamodb_tables):
        """Test validation of incomplete booking."""
        from lambda_actions import validate_booking
        
        table = dynamodb_tables.Table("nhs-booking-demo-bookings")
        table.put_item(Item={
            "booking_id": "NHS-20260115-DEF456",
            "patient_name": "",  # Missing
            "date": "2026-01-15",
            "time": ""  # Missing
        })
        
        result = validate_booking({"booking_id": "NHS-20260115-DEF456"})
        
        assert result["valid"] is False
        assert "issues" in result
    
    def test_validate_nonexistent_booking(self, dynamodb_tables):
        """Test validation of non-existent booking."""
        from lambda_actions import validate_booking
        
        result = validate_booking({"booking_id": "NHS-NOTFOUND-000000"})
        
        assert result["valid"] is False
        assert "not found" in result["reason"].lower()


class TestApproveBookingMoto:
    """Tests for approve_booking using moto."""
    
    def test_approve_booking_updates_status(self, dynamodb_tables):
        """Test booking approval updates status in DynamoDB."""
        from lambda_actions import approve_booking
        
        table = dynamodb_tables.Table("nhs-booking-demo-bookings")
        table.put_item(Item={
            "booking_id": "NHS-20260115-GHI789",
            "patient_name": "Jane Doe",
            "date": "2026-01-15",
            "time": "14:00",
            "status": "pending"
        })
        
        result = approve_booking({"booking_id": "NHS-20260115-GHI789"})
        
        assert result["approved"] is True
        
        # Verify status was updated
        item = table.get_item(Key={"booking_id": "NHS-20260115-GHI789"})
        assert item["Item"]["status"] == "approved"


class TestSendConfirmationMoto:
    """Tests for send_confirmation using moto."""
    
    def test_send_confirmation_with_booking(self, dynamodb_tables):
        """Test sending confirmation for existing booking."""
        from lambda_actions import send_confirmation
        
        table = dynamodb_tables.Table("nhs-booking-demo-bookings")
        table.put_item(Item={
            "booking_id": "NHS-20260115-JKL012",
            "patient_name": "Bob Wilson",
            "date": "2026-01-15",
            "time": "09:00"
        })
        
        result = send_confirmation({
            "booking_id": "NHS-20260115-JKL012",
            "email": "bob@example.com",
            "phone": "+447700900000"
        })
        
        assert result["sent"] is True
        assert len(result["sent_to"]) == 2
        assert any("email" in s for s in result["sent_to"])
        assert any("sms" in s for s in result["sent_to"])


class TestFullBookingFlowMoto:
    """Integration tests for complete booking flow using moto."""
    
    def test_complete_booking_flow(self, dynamodb_tables):
        """Test complete booking flow: check -> create -> validate -> approve -> confirm."""
        from lambda_actions import (
            check_availability,
            create_booking,
            validate_booking,
            approve_booking,
            send_confirmation
        )
        
        # Step 1: Check availability
        availability = check_availability({
            "appointment_type": "gp",
            "urgency": "routine"
        })
        assert len(availability["available_slots"]) > 0
        slot = availability["available_slots"][0]
        
        # Step 2: Create booking
        booking = create_booking({
            "patient_name": "Integration Test Patient",
            "appointment_type": "gp",
            "date": slot["date"],
            "time": slot["time"],
            "reason": "Routine checkup"
        })
        assert booking["status"] == "pending"
        booking_id = booking["booking_id"]
        
        # Step 3: Validate booking
        validation = validate_booking({"booking_id": booking_id})
        assert validation["valid"] is True
        
        # Step 4: Approve booking
        approval = approve_booking({"booking_id": booking_id})
        assert approval["approved"] is True
        
        # Step 5: Send confirmation
        confirmation = send_confirmation({
            "booking_id": booking_id,
            "email": "test@example.com"
        })
        assert confirmation["sent"] is True
        
        # Verify final state in DynamoDB
        table = dynamodb_tables.Table("nhs-booking-demo-bookings")
        item = table.get_item(Key={"booking_id": booking_id})
        assert item["Item"]["status"] == "approved"


class TestReferralValidationMoto:
    """Tests for GP referral validation using moto."""
    
    def test_validate_referral_no_referral(self, dynamodb_tables):
        """Test validation when no referral exists."""
        from lambda_actions import validate_referral
        
        result = validate_referral({
            "patient_name": "John Smith",
            "specialty": "cardiology"
        })
        
        assert result["valid"] is False
        assert "guidance" in result
        assert "self_referral_services" in result
    
    def test_validate_referral_missing_patient(self, dynamodb_tables):
        """Test validation with missing patient info."""
        from lambda_actions import validate_referral
        
        result = validate_referral({
            "specialty": "dermatology"
        })
        
        assert result["valid"] is False
        assert "error" in result


class TestPrescriptionRequestMoto:
    """Tests for prescription requests using moto."""
    
    def test_request_prescription_success(self, dynamodb_tables):
        """Test successful prescription request."""
        from lambda_actions import request_prescription
        
        # Create prescriptions table
        dynamodb_tables.create_table(
            TableName="nhs-booking-demo-prescriptions",
            KeySchema=[{"AttributeName": "prescription_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "prescription_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        result = request_prescription({
            "patient_name": "Jane Doe",
            "medications": "Metformin 500mg, Lisinopril 10mg",
            "delivery_preference": "collect",
            "pharmacy_name": "Boots Pharmacy"
        })
        
        assert result["success"] is True
        assert "prescription_id" in result
        assert result["prescription_id"].startswith("RX-")
        assert len(result["medications"]) == 2
        assert result["status"] == "pending_approval"
    
    def test_request_prescription_missing_medications(self, dynamodb_tables):
        """Test prescription request without medications."""
        from lambda_actions import request_prescription
        
        result = request_prescription({
            "patient_name": "John Smith"
        })
        
        assert result["success"] is False
        assert "medications" in str(result.get("required_info", []))
    
    def test_request_prescription_with_delivery(self, dynamodb_tables):
        """Test prescription request with home delivery."""
        from lambda_actions import request_prescription
        
        # Create prescriptions table
        try:
            dynamodb_tables.create_table(
                TableName="nhs-booking-demo-prescriptions",
                KeySchema=[{"AttributeName": "prescription_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "prescription_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
        except Exception:
            pass  # Table may already exist
        
        result = request_prescription({
            "patient_name": "Bob Wilson",
            "medications": "Atorvastatin 20mg",
            "delivery_preference": "deliver",
            "patient_address": "123 High Street, London SE1 1AA"
        })
        
        assert result["success"] is True
        assert "delivery_info" in result
        assert result["delivery_info"]["type"] == "home_delivery"


class TestPharmacyDeliveryMoto:
    """Tests for pharmacy delivery requests using moto."""
    
    def test_request_home_delivery(self, dynamodb_tables):
        """Test requesting home delivery."""
        from lambda_actions import request_pharmacy_delivery
        
        result = request_pharmacy_delivery({
            "patient_name": "Alice Brown",
            "delivery_type": "deliver",
            "patient_address": "456 Park Lane, London W1K 1AA"
        })
        
        assert result["success"] is True
        assert result["delivery_type"] == "home_delivery"
        assert "delivery_id" in result
        assert "estimated_delivery" in result
    
    def test_request_pharmacy_collection(self, dynamodb_tables):
        """Test requesting pharmacy collection."""
        from lambda_actions import request_pharmacy_delivery
        
        result = request_pharmacy_delivery({
            "patient_name": "Charlie Green",
            "delivery_type": "collect",
            "preferred_pharmacy": "Lloyds Pharmacy"
        })
        
        assert result["success"] is True
        assert result["delivery_type"] == "pharmacy_collection"
        assert result["pharmacy"] == "Lloyds Pharmacy"
    
    def test_delivery_missing_address(self, dynamodb_tables):
        """Test home delivery without address."""
        from lambda_actions import request_pharmacy_delivery
        
        result = request_pharmacy_delivery({
            "patient_name": "Dave White",
            "delivery_type": "deliver"
        })
        
        assert result["success"] is False
        assert "address" in result["error"].lower()


class TestFindNearbyPharmaciesMoto:
    """Tests for finding nearby pharmacies."""
    
    def test_find_pharmacies_mock_data(self, dynamodb_tables):
        """Test finding pharmacies returns mock data."""
        from lambda_actions import find_nearby_pharmacies
        
        result = find_nearby_pharmacies({
            "patient_name": "Test Patient",
            "patient_postcode": "SE1 1AA"
        })
        
        assert result["success"] is True
        assert "nearby_pharmacies" in result
        assert len(result["nearby_pharmacies"]) > 0
        
        # Check pharmacy structure
        pharmacy = result["nearby_pharmacies"][0]
        assert "name" in pharmacy
        assert "address" in pharmacy
        assert "distance_km" in pharmacy
    
    def test_find_pharmacies_missing_location(self, dynamodb_tables):
        """Test finding pharmacies without location."""
        from lambda_actions import find_nearby_pharmacies
        
        result = find_nearby_pharmacies({
            "patient_name": "Test Patient"
        })
        
        assert result["success"] is False
        assert "required_info" in result


class TestLambdaHandlerMoto:
    """Tests for Lambda handler routing using moto."""
    
    def test_handler_check_availability(self, dynamodb_tables):
        """Test handler routes check-availability correctly."""
        from lambda_actions import handler
        
        event = {
            "actionGroup": "BookingActions",
            "apiPath": "/check-availability",
            "requestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {"name": "appointment_type", "value": "gp"},
                            {"name": "urgency", "value": "routine"}
                        ]
                    }
                }
            }
        }
        
        result = handler(event, None)
        
        assert result["messageVersion"] == "1.0"
        assert result["response"]["httpStatusCode"] == 200
        
        body = json.loads(result["response"]["responseBody"]["application/json"]["body"])
        assert "available_slots" in body
    
    def test_handler_create_booking(self, dynamodb_tables):
        """Test handler routes create-booking correctly."""
        from lambda_actions import handler
        
        event = {
            "actionGroup": "BookingActions",
            "apiPath": "/create-booking",
            "requestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {"name": "patient_name", "value": "Handler Test"},
                            {"name": "date", "value": "2026-01-20"},
                            {"name": "time", "value": "11:00"}
                        ]
                    }
                }
            }
        }
        
        result = handler(event, None)
        
        body = json.loads(result["response"]["responseBody"]["application/json"]["body"])
        assert "booking_id" in body
        assert body["status"] == "pending"
