"""Tests for Lambda action handlers."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestCheckAvailability:
    """Tests for check_availability action."""
    
    def test_routine_availability(self):
        """Test routine appointment availability."""
        from lambda_actions import check_availability
        
        result = check_availability({
            "appointment_type": "gp",
            "urgency": "routine"
        })
        
        assert "available_slots" in result
        assert len(result["available_slots"]) > 0
        assert result["appointment_type"] == "gp"
    
    def test_urgent_availability(self):
        """Test urgent appointment availability."""
        from lambda_actions import check_availability
        
        result = check_availability({
            "appointment_type": "gp",
            "urgency": "urgent"
        })
        
        assert "available_slots" in result
        # Urgent should have slots within 2 days
        for slot in result["available_slots"]:
            assert slot["type"] == "urgent"


class TestCreateBooking:
    """Tests for create_booking action."""
    
    @patch("lambda_actions.dynamodb")
    def test_create_booking_success(self, mock_dynamodb):
        """Test successful booking creation."""
        from lambda_actions import create_booking
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        result = create_booking({
            "patient_name": "John Smith",
            "appointment_type": "gp",
            "date": "2025-01-15",
            "time": "10:00",
            "reason": "Headache"
        })
        
        assert "booking_id" in result
        assert result["booking_id"].startswith("NHS-")
        assert result["status"] == "pending"
    
    def test_booking_id_format(self):
        """Test booking ID format."""
        from lambda_actions import create_booking
        
        with patch("lambda_actions.dynamodb"):
            result = create_booking({"patient_name": "Test"})
            
            # Format: NHS-YYYYMMDD-XXXXXX
            booking_id = result["booking_id"]
            assert booking_id.startswith("NHS-")
            parts = booking_id.split("-")
            assert len(parts) == 3
            assert len(parts[1]) == 8  # Date
            assert len(parts[2]) == 6  # Random hex


class TestValidateBooking:
    """Tests for validate_booking action."""
    
    @patch("lambda_actions.dynamodb")
    def test_validate_complete_booking(self, mock_dynamodb):
        """Test validation of complete booking."""
        from lambda_actions import validate_booking
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "booking_id": "NHS-123",
                "patient_name": "John Smith",
                "date": "2025-01-15",
                "time": "10:00"
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        result = validate_booking({"booking_id": "NHS-123"})
        
        assert result["valid"] is True
    
    @patch("lambda_actions.dynamodb")
    def test_validate_incomplete_booking(self, mock_dynamodb):
        """Test validation of incomplete booking."""
        from lambda_actions import validate_booking
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "booking_id": "NHS-123",
                "patient_name": "",  # Missing
                "date": "2025-01-15",
                "time": ""  # Missing
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        result = validate_booking({"booking_id": "NHS-123"})
        
        assert result["valid"] is False
        assert "issues" in result
    
    @patch("lambda_actions.dynamodb")
    def test_validate_nonexistent_booking(self, mock_dynamodb):
        """Test validation of non-existent booking."""
        from lambda_actions import validate_booking
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        mock_dynamodb.Table.return_value = mock_table
        
        result = validate_booking({"booking_id": "NHS-NOTFOUND"})
        
        assert result["valid"] is False
        assert "not found" in result["reason"].lower()


class TestApproveBooking:
    """Tests for approve_booking action."""
    
    @patch("lambda_actions.dynamodb")
    def test_approve_booking_success(self, mock_dynamodb):
        """Test successful booking approval."""
        from lambda_actions import approve_booking
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "booking_id": "NHS-123",
                "date": "2025-01-15",
                "time": "10:00",
                "status": "approved"
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        result = approve_booking({"booking_id": "NHS-123"})
        
        assert result["approved"] is True
        assert result["booking_id"] == "NHS-123"


class TestSendConfirmation:
    """Tests for send_confirmation action."""
    
    @patch("lambda_actions.dynamodb")
    def test_send_confirmation(self, mock_dynamodb):
        """Test sending confirmation."""
        from lambda_actions import send_confirmation
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "booking_id": "NHS-123",
                "date": "2025-01-15",
                "time": "10:00"
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        result = send_confirmation({
            "booking_id": "NHS-123",
            "email": "test@example.com",
            "phone": "+447700900000"
        })
        
        assert result["sent"] is True
        assert len(result["sent_to"]) == 2


class TestSendLetter:
    """Tests for send_letter action."""
    
    @patch("lambda_actions.dynamodb")
    def test_send_confirmation_letter(self, mock_dynamodb):
        """Test sending confirmation letter."""
        from lambda_actions import send_letter
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "booking_id": "NHS-123",
                "patient_name": "John Smith"
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        result = send_letter({
            "booking_id": "NHS-123",
            "letter_type": "confirmation",
            "email": "test@example.com"
        })
        
        assert result["sent"] is True
        assert result["letter_type"] == "confirmation"


class TestLambdaHandler:
    """Tests for main Lambda handler."""
    
    @patch("lambda_actions.dynamodb")
    def test_handler_routing(self, mock_dynamodb):
        """Test handler routes to correct action."""
        from lambda_actions import handler
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        event = {
            "actionGroup": "BookingAgent",
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
