"""
Batch Email Service for EduPulse
Handles bulk email sending with improved performance and reliability
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from core.models import EmailLog, NotificationQuota
import smtplib
from socket import timeout as socket_timeout

logger = logging.getLogger(__name__)


class BatchEmailService:
    """
    Enhanced email service for batch operations with improved performance and reliability
    """

    def __init__(self, batch_size: int = None, batch_delay: float = None, progress_callback=None):
        self.batch_size = batch_size or getattr(settings, 'BULK_EMAIL_BATCH_SIZE', 20)
        self.batch_delay = batch_delay or getattr(settings, 'BULK_EMAIL_BATCH_DELAY', 0.5)
        self.progress_callback = progress_callback
        self.connection = None
        self.stats = {
            'sent': 0,
            'failed': 0,
            'batches': 0,
            'retries': 0
        }

    def _get_email_connection(self, force_new=False):
        """Get optimized email connection with timeout settings"""
        if force_new or not self.connection:
            # Create new connection with timeout
            timeout = getattr(settings, 'EMAIL_TIMEOUT', 60)
            self.connection = get_connection(
                fail_silently=False,
                timeout=timeout
            )
        return self.connection

    def _is_connection_valid(self, connection):
        """Check if SMTP connection is still valid"""
        try:
            # Try to get connection status - this will fail if connection is closed
            if hasattr(connection, 'connection') and connection.connection:
                # Send a simple NOOP command to test connection
                connection.connection.noop()
                return True
        except:
            pass
        return False

    def _send_batch(self, emails: List[EmailMultiAlternatives]) -> Tuple[int, int]:
        """
        Send a batch of emails using a single SMTP connection with retry logic
        Returns (sent_count, failed_count)
        """
        if not emails:
            return 0, 0

        sent_count = 0
        failed_count = 0
        max_retries = 2

        for retry_count in range(max_retries):
            connection = None
            batch_failed_emails = []

            try:
                # Get connection, force new on retry
                connection = self._get_email_connection(force_new=(retry_count > 0))

                # Validate connection before using
                if not self._is_connection_valid(connection):
                    connection = self._get_email_connection(force_new=True)

                connection.open()

                # Send emails that haven't been sent yet
                emails_to_send = emails if retry_count == 0 else batch_failed_emails
                batch_failed_emails = []

                for email in emails_to_send:
                    try:
                        # Send individual email
                        result = connection.send_messages([email])
                        if result > 0:
                            sent_count += 1
                            if not getattr(settings, 'EMAIL_LOG_VIA_BACKEND_ONLY', True):
                                self._log_email_success(email)
                            # Consume quota immediately for successful sends
                            try:
                                NotificationQuota.consume_quota('email', 1)
                            except Exception as quota_error:
                                logger.warning(f"Failed to consume email quota: {quota_error}")
                        else:
                            batch_failed_emails.append(email)
                            logger.warning(f"Email send returned 0 for {email.to[0] if email.to else 'unknown'}")

                    except (smtplib.SMTPException, socket_timeout) as e:
                        batch_failed_emails.append(email)
                        logger.warning(f"SMTP error sending to {email.to[0] if email.to else 'unknown'}: {e}")
                    except Exception as e:
                        batch_failed_emails.append(email)
                        logger.error(f"Unexpected error sending to {email.to[0] if email.to else 'unknown'}: {e}")

                # If all emails sent successfully, break retry loop
                if not batch_failed_emails:
                    break

            except Exception as e:
                logger.error(f"Batch connection error (attempt {retry_count + 1}): {e}")
                # On connection error, all emails in this attempt are considered failed
                batch_failed_emails = emails if retry_count == 0 else batch_failed_emails

            finally:
                if connection:
                    try:
                        connection.close()
                    except:
                        pass
                self.connection = None  # Force new connection next time

        # Log any remaining failed emails
        failed_count = len(batch_failed_emails)
        if not getattr(settings, 'EMAIL_LOG_VIA_BACKEND_ONLY', True):
            for email in batch_failed_emails:
                self._log_email_failure(email, f"Failed after {max_retries} attempts")

        return sent_count, failed_count

    def _log_email_success(self, email: EmailMultiAlternatives):
        """Log successful email sending"""
        try:
            EmailLog.objects.create(
                recipient_email=email.to[0] if email.to else 'unknown',
                recipient_type='student',
                subject=email.subject,
                content=email.body,
                email_type='bulk',
                status='sent',
                sent_at=timezone.now()
            )
        except Exception as e:
            logger.warning(f"Failed to log email success: {e}")

    def _log_email_failure(self, email: EmailMultiAlternatives, error_message: str):
        """Log failed email sending"""
        try:
            EmailLog.objects.create(
                recipient_email=email.to[0] if email.to else 'unknown',
                recipient_type='student',
                subject=email.subject,
                content=email.body,
                email_type='bulk',
                status='failed',
                error_message=error_message,
                sent_at=timezone.now()
            )
        except Exception as e:
            logger.warning(f"Failed to log email failure: {e}")

    def send_bulk_emails(self, email_data_list: List[Dict[str, Any]],
                        template_name: str = None,
                        subject_prefix: str = "") -> Dict[str, int]:
        """
        Send bulk emails with batching and error handling

        Args:
            email_data_list: List of dicts containing email data
                Each dict should have: 'to', 'subject', 'context', 'template_name' (optional)
            template_name: Default template name if not specified in email data
            subject_prefix: Prefix to add to all subjects

        Returns:
            Dict with statistics: {'sent': int, 'failed': int, 'batches': int}
        """
        if not email_data_list:
            return {'sent': 0, 'failed': 0, 'batches': 0}

        # Check quota availability
        if not NotificationQuota.check_quota_available('email', len(email_data_list)):
            logger.error(f"Email quota exceeded. Cannot send {len(email_data_list)} emails.")
            raise ValueError(f"Email quota exceeded. Cannot send {len(email_data_list)} emails.")

        logger.info(f"Starting bulk email sending: {len(email_data_list)} emails in batches of {self.batch_size}")

        # Reset stats
        self.stats = {'sent': 0, 'failed': 0, 'batches': 0, 'retries': 0}
        total_emails = len(email_data_list)
        total_batches = (total_emails + self.batch_size - 1) // self.batch_size

        # Initial progress callback
        if self.progress_callback:
            self.progress_callback(0, total_emails, self.stats, 'starting')

        # Process emails in batches
        for i in range(0, len(email_data_list), self.batch_size):
            batch_data = email_data_list[i:i + self.batch_size]
            batch_emails = []

            # Prepare batch emails
            for email_data in batch_data:
                try:
                    email = self._prepare_email(email_data, template_name, subject_prefix)
                    if email:
                        batch_emails.append(email)
                except Exception as e:
                    logger.error(f"Failed to prepare email: {e}")
                    self.stats['failed'] += 1

            # Send batch
            if batch_emails:
                batch_sent, batch_failed = self._send_batch(batch_emails)
                self.stats['sent'] += batch_sent
                self.stats['failed'] += batch_failed
                self.stats['batches'] += 1

                logger.info(f"Batch {self.stats['batches']}: sent {batch_sent}, failed {batch_failed}")

                # Progress callback after each batch
                if self.progress_callback:
                    progress_percentage = int((self.stats['sent'] + self.stats['failed']) / total_emails * 100)
                    self.progress_callback(
                        self.stats['sent'] + self.stats['failed'],
                        total_emails,
                        self.stats.copy(),
                        'sending',
                        progress_percentage,
                        self.stats['batches'],
                        total_batches
                    )

                # Optional delay between batches (can be set to 0 for no delay)
                # NOTE: This still blocks the request. For true async, use django-rq or Celery
                if i + self.batch_size < len(email_data_list) and self.batch_delay > 0:
                    time.sleep(self.batch_delay)

        # Final progress callback
        if self.progress_callback:
            self.progress_callback(
                total_emails,
                total_emails,
                self.stats.copy(),
                'completed',
                100,
                total_batches,
                total_batches
            )

        # Quota is already consumed per successful email in _send_batch
        logger.info(f"Bulk email completed: {self.stats}")
        return self.stats

    def _prepare_email(self, email_data: Dict[str, Any],
                      default_template: str = None,
                      subject_prefix: str = "") -> Optional[EmailMultiAlternatives]:
        """
        Prepare individual email from data

        Args:
            email_data: Dict with 'to', 'subject', 'context', 'template_name' (optional)
            default_template: Template to use if not specified in email_data
            subject_prefix: Prefix for subject line

        Returns:
            EmailMultiAlternatives object or None if failed
        """
        try:
            to_email = email_data.get('to')
            subject = email_data.get('subject', 'Notification')
            context = email_data.get('context', {})
            template_name = email_data.get('template_name', default_template)

            if not to_email:
                logger.warning("No recipient email provided")
                return None

            if not template_name:
                logger.warning("No template name provided")
                return None

            # Add subject prefix
            full_subject = f"{subject_prefix}{subject}" if subject_prefix else subject

            # Render email content
            try:
                html_content = render_to_string(template_name, context)
                # Try to render text version
                text_template = template_name.replace('.html', '.txt')
                try:
                    text_content = render_to_string(text_template, context)
                except:
                    # Fallback to HTML content stripped of tags
                    import re
                    text_content = re.sub(r'<[^>]+>', '', html_content)
            except Exception as e:
                logger.error(f"Failed to render email template {template_name}: {e}")
                return None

            # Resolve sender using EmailSettings/OrganisationSettings priority
            try:
                from core.models import EmailSettings, OrganisationSettings
                config = EmailSettings.get_active_config()
                org = OrganisationSettings.get_instance()
                sender_from = config.from_email if config and getattr(config, 'from_email', None) else settings.DEFAULT_FROM_EMAIL
                sender_reply = config.reply_to_email if config and getattr(config, 'reply_to_email', None) else org.reply_to_email
            except Exception:
                sender_from = settings.DEFAULT_FROM_EMAIL
                sender_reply = getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)

            # Create email
            email = EmailMultiAlternatives(
                subject=full_subject,
                body=text_content,
                from_email=sender_from,
                to=[to_email] if isinstance(to_email, str) else to_email,
                reply_to=[sender_reply]
            )
            email.attach_alternative(html_content, "text/html")

            return email

        except Exception as e:
            logger.error(f"Failed to prepare email: {e}")
            return None

    def send_templated_bulk_emails(self, recipients: List[Dict[str, Any]],
                                  template_name: str,
                                  subject: str,
                                  common_context: Dict[str, Any] = None) -> Dict[str, int]:
        """
        Send templated bulk emails to multiple recipients

        Args:
            recipients: List of dicts with recipient info
                Each dict should have: 'email', 'name', and any additional context
            template_name: Email template name
            subject: Email subject
            common_context: Context data common to all emails

        Returns:
            Dict with statistics
        """
        common_context = common_context or {}
        email_data_list = []

        for recipient in recipients:
            recipient_email = recipient.get('email')
            if not recipient_email:
                continue

            # Merge recipient-specific context with common context
            context = {**common_context, **recipient}

            email_data = {
                'to': recipient_email,
                'subject': subject,
                'context': context,
                'template_name': template_name
            }
            email_data_list.append(email_data)

        return self.send_bulk_emails(email_data_list)

    def close_connection(self):
        """Close email connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            self.connection = None

    def get_stats(self) -> Dict[str, int]:
        """Get current sending statistics"""
        return self.stats.copy()