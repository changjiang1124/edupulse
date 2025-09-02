"""
Dynamic SMS Backend for EduPulse
Reads SMS configuration from database at runtime with environment variable fallback
"""
from django.conf import settings
from django.utils import timezone
import logging
import os

logger = logging.getLogger(__name__)


class DynamicSMSBackend:
    """
    SMS backend that reads configuration from database
    Falls back to environment variables or settings.py configuration if no active config found
    """
    
    def __init__(self):
        self.config = None
        self.client = None
        self._initialize_config()
    
    def _initialize_config(self):
        """Initialize SMS configuration from database or environment variables"""
        # Try to get active SMS configuration from database
        self.config = self._get_active_config()
        
        if self.config:
            # Use database configuration
            self.account_sid = self.config.account_sid
            self.auth_token = self.config.auth_token
            self.from_number = self.config.from_number
            self.sender_name = self.config.sender_name
            self.backend_type = self.config.sms_backend_type
            
            logger.info(f'Using database SMS config: {self.config.get_sms_backend_type_display()} ({self.config.from_number})')
        else:
            # Fall back to environment variables or settings.py configuration
            self.account_sid = os.getenv('TWILIO_ACCOUNT_SID') or getattr(settings, 'TWILIO_ACCOUNT_SID', '')
            self.auth_token = os.getenv('TWILIO_AUTH_TOKEN') or getattr(settings, 'TWILIO_AUTH_TOKEN', '')
            self.from_number = os.getenv('TWILIO_FROM_NUMBER') or getattr(settings, 'TWILIO_FROM_NUMBER', '')
            self.sender_name = 'PerthArt'  # Default sender name
            self.backend_type = 'twilio'
            
            logger.info(f'Using fallback SMS configuration from environment variables or settings.py ({self.from_number})')
        
        # Initialize Twilio client if we have valid configuration
        if self.backend_type == 'twilio' and self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info('Twilio client initialized successfully')
            except ImportError:
                logger.error('Twilio library not installed. Please install: pip install twilio')
                self.client = None
            except Exception as e:
                logger.error(f'Failed to initialize Twilio client: {e}')
                self.client = None
        else:
            logger.warning('SMS configuration incomplete - SMS functionality disabled')
    
    def _get_active_config(self):
        """Get active SMS configuration from database"""
        try:
            from core.models import SMSSettings
            return SMSSettings.get_active_config()
        except Exception as e:
            logger.warning(f'Could not retrieve SMS configuration from database: {e}')
            return None
    
    def send_messages(self, sms_messages):
        """
        Send SMS messages
        
        Args:
            sms_messages: List of dictionaries with keys: 'to', 'body', 'type' (optional)
        
        Returns:
            int: Number of successfully sent messages
        """
        if not sms_messages:
            return 0
        
        if not self.client:
            logger.error('SMS client not initialized - cannot send messages')
            return 0
        
        sent_count = 0
        
        for message in sms_messages:
            try:
                # Extract message details
                recipient_phone = message.get('to')
                message_body = message.get('body', '')
                sms_type = message.get('type', 'general')
                
                if not recipient_phone or not message_body:
                    logger.warning(f'Skipping message with missing recipient ({recipient_phone}) or body')
                    continue
                
                # Send via Twilio
                twilio_message = self.client.messages.create(
                    body=message_body,
                    from_=self.from_number,
                    to=recipient_phone
                )
                
                # Log successful send
                self._log_sms(message, 'sent', twilio_message.sid)
                sent_count += 1
                
                logger.info(f'SMS sent successfully to {recipient_phone}. SID: {twilio_message.sid}')
                
            except Exception as e:
                # Log failed send
                self._log_sms(message, 'failed', None, str(e))
                logger.error(f'Failed to send SMS to {recipient_phone}: {e}')
        
        if sent_count > 0:
            backend_name = self.config.get_sms_backend_type_display() if self.config else 'environment'
            logger.info(f'Successfully sent {sent_count} SMS message(s) via {backend_name}')
        
        return sent_count
    
    def send_single_message(self, to, body, sms_type='general'):
        """
        Send a single SMS message
        
        Args:
            to (str): Recipient phone number in E.164 format
            body (str): Message content
            sms_type (str): Type of SMS for logging purposes
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        messages = [{'to': to, 'body': body, 'type': sms_type}]
        return self.send_messages(messages) == 1
    
    def _log_sms(self, message, status, message_sid=None, error_message=None):
        """Log SMS sending activity"""
        try:
            from core.models import SMSLog
            
            # Extract message details
            recipient_phone = message.get('to', 'unknown')
            message_body = message.get('body', '')
            sms_type = message.get('type', 'general')
            
            # Determine recipient type based on message content or phone patterns
            recipient_type = 'unknown'
            if any(keyword in message_body.lower() for keyword in ['staff', 'teacher', 'admin']):
                recipient_type = 'staff'
            elif any(keyword in message_body.lower() for keyword in ['student', 'class', 'course']):
                recipient_type = 'student'
            elif any(keyword in message_body.lower() for keyword in ['guardian', 'parent', 'family']):
                recipient_type = 'guardian'
            
            # Create log entry
            SMSLog.objects.create(
                recipient_phone=recipient_phone,
                recipient_type=recipient_type,
                content=message_body[:500],  # Truncate if too long
                sms_type=sms_type,
                status=status,
                error_message=error_message[:500] if error_message else '',
                message_sid=message_sid or '',
                backend_type=self.config.get_sms_backend_type_display() if self.config else 'environment',
                sent_at=timezone.now() if status == 'sent' else None
            )
            
        except Exception as e:
            # Don't let logging errors break SMS sending
            logger.warning(f'Failed to log SMS activity: {e}')
    
    def is_configured(self):
        """Check if SMS backend is properly configured"""
        return (self.client is not None and 
                bool(self.account_sid) and 
                bool(self.auth_token) and 
                bool(self.from_number))
    
    def get_configuration_info(self):
        """Get information about current configuration"""
        return {
            'backend_type': self.backend_type,
            'from_number': self.from_number,
            'sender_name': self.sender_name,
            'is_configured': self.is_configured(),
            'source': 'database' if self.config else 'environment'
        }


class SMSMessage:
    """
    Simple SMS message class for easier message creation
    """
    
    def __init__(self, to, body, sms_type='general'):
        self.to = to
        self.body = body
        self.sms_type = sms_type
    
    def to_dict(self):
        """Convert to dictionary format expected by backend"""
        return {
            'to': self.to,
            'body': self.body,
            'type': self.sms_type
        }


def send_sms(to, body, sms_type='general'):
    """
    Convenience function to send a single SMS
    
    Args:
        to (str): Recipient phone number in E.164 format
        body (str): Message content
        sms_type (str): Type of SMS for logging purposes
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    backend = DynamicSMSBackend()
    return backend.send_single_message(to, body, sms_type)


def send_bulk_sms(messages):
    """
    Convenience function to send multiple SMS messages
    
    Args:
        messages: List of SMSMessage objects or dictionaries
    
    Returns:
        int: Number of successfully sent messages
    """
    backend = DynamicSMSBackend()
    
    # Convert SMSMessage objects to dictionaries if needed
    message_dicts = []
    for msg in messages:
        if isinstance(msg, SMSMessage):
            message_dicts.append(msg.to_dict())
        elif isinstance(msg, dict):
            message_dicts.append(msg)
        else:
            logger.warning(f'Invalid message type: {type(msg)}')
    
    return backend.send_messages(message_dicts)