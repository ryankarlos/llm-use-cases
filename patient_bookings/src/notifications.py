"""Simple notification utilities for email and SMS - demo only."""

import os
from datetime import datetime

import boto3


class NotificationService:
    """Send notifications via SES (email) and SNS (SMS)."""
    
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "eu-west-2")
        self.ses = boto3.client("ses", region_name=self.region)
        self.sns = boto3.client("sns", region_name=self.region)
        self.sender_email = os.environ.get("SES_SENDER_EMAIL", "")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str = None
    ) -> bool:
        """Send email via SES.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            
        Returns:
            True if sent successfully
        """
        if not self.sender_email:
            print(f"[DEMO] Would send email to {to_email}: {subject}")
            return True
        
        try:
            message = {
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}}
            }
            if html_body:
                message["Body"]["Html"] = {"Data": html_body}
            
            self.ses.send_email(
                Source=self.sender_email,
                Destination={"ToAddresses": [to_email]},
                Message=message
            )
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via SNS.
        
        Args:
            phone_number: Phone number (E.164 format)
            message: SMS message
            
        Returns:
            True if sent successfully
        """
        try:
            self.sns.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {
                        "DataType": "String",
                        "StringValue": "NHS"
                    }
                }
            )
            return True
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    def send_booking_confirmation(
        self,
        email: str,
        phone: str,
        booking_ref: str,
        appointment_date: str,
        appointment_time: str,
        doctor: str,
        location: str
    ):
        """Send booking confirmation via email and SMS."""
        
        # Email
        subject = f"NHS Appointment Confirmation - {booking_ref}"
        body = f"""
Dear Patient,

Your appointment has been confirmed.

Reference: {booking_ref}
Date: {appointment_date}
Time: {appointment_time}
Doctor: {doctor}
Location: {location}

Please arrive 10 minutes early.

To cancel or reschedule, reply to this email or call the surgery.

NHS Patient Booking System
        """.strip()
        
        self.send_email(email, subject, body)
        
        # SMS
        sms = f"NHS Appt confirmed: {appointment_date} {appointment_time} with {doctor}. Ref: {booking_ref}"
        if phone:
            self.send_sms(phone, sms)
    
    def send_letter(
        self,
        email: str,
        letter_type: str,
        content: str,
        booking_ref: str = None
    ):
        """Send a letter via email (PDF would be attached in production)."""
        
        subject = f"NHS {letter_type} - {booking_ref or datetime.now().strftime('%Y%m%d')}"
        body = f"""
Dear Patient,

Please find your {letter_type} below.

---
{content}
---

If you have any questions, please contact your GP surgery.

NHS Patient Booking System
        """.strip()
        
        self.send_email(email, subject, body)
