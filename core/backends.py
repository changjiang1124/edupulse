"""
Dynamic Email Backend for EduPulse
Reads email configuration from database at runtime
"""
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class DynamicEmailBackend(EmailBackend):
    """
    Email backend that reads configuration from database
    Falls back to settings.py configuration if no active config found
    """
    
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None, **kwargs):
        
        # Try to get active email configuration from database
        config = self._get_active_config()
        
        if config:
            # Use database configuration
            host = config.smtp_host
            port = config.smtp_port
            username = config.smtp_username
            password = config.smtp_password
            use_tls = config.use_tls
            use_ssl = False
            if port == 465:
                use_ssl = True
                use_tls = False
            
            logger.info(f'Using database email config: {config.get_email_backend_type_display()} ({config.smtp_username})')
        else:
            # Fall back to environment variables or settings.py configuration
            import os
            
            host = host or os.getenv('SMTP_SERVER') or getattr(settings, 'EMAIL_HOST', 'localhost')
            port = port or int(os.getenv('SMTP_PORT', '0')) or getattr(settings, 'EMAIL_PORT', 25)
            username = username or os.getenv('SMTP_USERNAME') or getattr(settings, 'EMAIL_HOST_USER', '')
            password = password or os.getenv('SMTP_PASSWORD') or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            use_tls = use_tls if use_tls is not None else getattr(settings, 'EMAIL_USE_TLS', True)
            use_ssl = use_ssl if use_ssl is not None else getattr(settings, 'EMAIL_USE_SSL', False)
            if port == 465:
                use_ssl = True
                use_tls = False
            
            logger.info(f'Using fallback email configuration from environment variables ({host}:{port}) or settings.py')
        
        # Initialize parent class with determined configuration
        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            fail_silently=fail_silently,
            use_ssl=use_ssl,
            timeout=timeout,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs
        )
    
    def _get_active_config(self):
        """Get active email configuration from database"""
        try:
            from core.models import EmailSettings
            return EmailSettings.get_active_config()
        except Exception as e:
            logger.warning(f'Could not retrieve email configuration from database: {e}')
            return None
    
    def send_messages(self, email_messages):
        """
        Override send_messages to add reply-to headers and log email sending activity
        """
        if not email_messages:
            return 0
        
        # Get configuration for reply-to and logging
        config = self._get_active_config()
        
        # Add reply-to headers to all messages
        self._add_reply_to_headers(email_messages, config)
        
        try:
            sent_count = super().send_messages(email_messages)
            
            # Log successful sends
            if sent_count > 0:
                for message in email_messages[:sent_count]:
                    self._log_email(message, 'sent', config)
                    
                logger.info(f'Successfully sent {sent_count} email(s) via {config.get_email_backend_type_display() if config else "fallback config"}')
            
            return sent_count
            
        except Exception as e:
            # Log failed sends
            for message in email_messages:
                self._log_email(message, 'failed', config, str(e))
                
            logger.error(f'Failed to send emails via {config.get_email_backend_type_display() if config else "fallback config"}: {e}')
            raise e
    
    def _add_reply_to_headers(self, email_messages, config):
        """Add reply-to headers to email messages based on configuration"""
        reply_to_email = None
        
        if config and config.reply_to_email:
            # Use configured reply-to email
            reply_to_email = config.reply_to_email
        elif config and config.from_email:
            # Use from_email as reply-to if no specific reply-to configured
            reply_to_email = config.from_email
        else:
            # Fallback to settings
            import os
            reply_to_email = os.getenv('DEFAULT_REPLY_TO_EMAIL') or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        
        # Add reply-to header to all messages if we have an email to use
        if reply_to_email:
            for message in email_messages:
                # Check if message already has reply_to set
                if not hasattr(message, 'reply_to') or not message.reply_to:
                    message.reply_to = [reply_to_email]
                    logger.debug(f'Added reply-to header: {reply_to_email} to message: {message.subject}')
    
    
    def _log_email(self, message, status, config, error_message=None):
        """Log email sending activity"""
        try:
            from core.models import EmailLog
            
            # Iterate through all recipients to create individual logs
            if not message.to:
                # Log even if no recipient (edge case)
                self._create_single_log(message, 'unknown', 'unknown', status, config, error_message)
                return

            for recipient_email in message.to:
                # Determine recipient type for this specific email
                recipient_type = 'unknown'
                
                # Try to identify recipient type based on specific email
                if recipient_email.endswith('@perthartschool.com.au') or 'admin' in recipient_email:
                    recipient_type = 'staff'
                elif 'enrollment' in message.subject.lower() or 'enrolment' in message.subject.lower():
                    recipient_type = 'student'
                elif 'guardian' in getattr(message, 'body', '').lower() or 'parent' in getattr(message, 'body', '').lower():
                    recipient_type = 'guardian'
                
                self._create_single_log(message, recipient_email, recipient_type, status, config, error_message)
        except Exception as e:
            # Fallback for any top-level errors in logging loop
            logger.warning(f'Failed to log email activity in loop: {e}')

    def _create_single_log(self, message, recipient_email, recipient_type, status, config, error_message=None):
        """Helper to create a single log entry"""
        try:
            from core.models import EmailLog
            
            # Determine email type based on subject
            email_type = 'general'
            subject_lower = message.subject.lower()
            if 'welcome' in subject_lower:
                email_type = 'welcome'
            elif 'enrollment' in subject_lower or 'enrolment' in subject_lower:
                email_type = 'enrollment_confirm'
            elif 'attendance' in subject_lower:
                email_type = 'attendance_notice'
            elif 'reminder' in subject_lower or 'class' in subject_lower:
                email_type = 'course_reminder'
            elif 'test' in subject_lower:
                email_type = 'test'
            
            EmailLog.objects.create(
                recipient_email=recipient_email,
                recipient_type=recipient_type,
                email_type=email_type,
                subject=message.subject[:200],  # Truncate if too long
                content=getattr(message, 'body', '')[:1000],  # Truncate content
                status=status,
                error_message=error_message[:500] if error_message else '',
                email_backend=config.get_email_backend_type_display() if config else 'environment',
                sent_at=timezone.now() if status == 'sent' else None
            )
        except Exception as e:
            # Don't let logging errors break email sending
            logger.warning(f'Failed to create single email log: {e}')