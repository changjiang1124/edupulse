"""
Notification Service for EduPulse
Handles automated email and SMS notifications for various events
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from core.models import OrganisationSettings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class to handle all automated notifications
    """
    
    @staticmethod
    def send_enrollment_confirmation(enrollment):
        """
        Send enrollment confirmation email to student/guardian
        """
        try:
            # Determine recipient based on student age
            student = enrollment.student
            recipient_email = student.contact_email
            recipient_name = student.guardian_name if student.guardian_name else student.get_full_name()
            
            if not recipient_email:
                logger.warning(f"No email address found for enrollment {enrollment.id}")
                return False
            
            # Prepare context for email template
            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()
            context = {
                'enrollment': enrollment,
                'student': student,
                'course': enrollment.course,
                'recipient_name': recipient_name,
                'total_fee': enrollment.get_total_fee(),
                'outstanding_fee': enrollment.get_outstanding_fee(),
                'is_fully_paid': enrollment.is_fully_paid(),
                'site_domain': site.domain,
                'enrollment_url': f"https://{site.domain}{reverse('enrollment:enrollment_detail', args=[enrollment.id])}",
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone,
            }
            
            # Render email templates
            subject = f"Enrolment Confirmation - {enrollment.course.name}"
            html_content = render_to_string('core/emails/enrollment_confirmation.html', context)
            text_content = render_to_string('core/emails/enrollment_confirmation.txt', context)
            
            # Create and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[org_settings.reply_to_email],
            )
            email.attach_alternative(html_content, "text/html")
            
            sent = email.send()
            
            if sent:
                logger.info(f"Enrollment confirmation email sent to {recipient_email} for enrollment {enrollment.id}")
                return True
            else:
                logger.error(f"Failed to send enrollment confirmation email to {recipient_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending enrollment confirmation email: {str(e)}")
            return False
    
    @staticmethod
    def send_enrollment_pending_email(enrollment, recipient_email=None, fee_breakdown=None):
        """
        Send enrollment pending notification email with payment information
        This is sent immediately when enrollment is submitted
        """
        try:
            student = enrollment.student
            recipient_email = recipient_email or student.contact_email
            recipient_name = student.guardian_name if student.guardian_name else student.get_full_name()
            
            if not recipient_email:
                logger.warning(f"No email address found for pending email - enrollment {enrollment.id}")
                return False
            
            # Prepare context for pending email template
            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()
            context = {
                'enrollment': enrollment,
                'student': student,
                'course': enrollment.course,
                'recipient_name': recipient_name,
                'recipient_email': recipient_email,
                'site_domain': org_settings.site_domain,
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone,
                'bank_account_name': org_settings.bank_account_name,
                'bank_bsb': org_settings.bank_bsb,
                'bank_account_number': org_settings.bank_account_number,
                'fee_breakdown': fee_breakdown or {}
            }
            
            # Calculate total fees
            from decimal import Decimal
            course_fee = enrollment.course.price or Decimal('0')
            registration_fee = Decimal(str(fee_breakdown.get('registration_fee', 0))) if fee_breakdown else Decimal('0')
            total_fee = Decimal(str(fee_breakdown.get('total_fee', 0))) if fee_breakdown else course_fee + registration_fee
            
            context.update({
                'course_fee': course_fee,
                'registration_fee': registration_fee,
                'total_fee': total_fee,
                'has_registration_fee': registration_fee > 0,
                'charge_registration_fee': fee_breakdown.get('charge_registration_fee', True) if fee_breakdown else True,
                'current_year': timezone.now().year
            })
            
            # Render email templates
            subject = f"Enrolment Received - {enrollment.course.name} - Payment Required"
            html_content = render_to_string('core/emails/enrollment_pending.html', context)
            text_content = render_to_string('core/emails/enrollment_pending.txt', context)
            
            # Create and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[org_settings.reply_to_email],
            )
            email.attach_alternative(html_content, "text/html")

            sent = email.send()

            if sent:
                logger.info(f"Enrollment pending email sent to {recipient_email} for enrollment {enrollment.id}")
                return True
            else:
                logger.error(f"Failed to send enrollment pending email to {recipient_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending enrollment pending email: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(enrollment):
        """
        Send welcome email after enrollment confirmation
        """
        try:
            student = enrollment.student
            recipient_email = student.contact_email
            recipient_name = student.guardian_name if student.guardian_name else student.get_full_name()
            
            if not recipient_email:
                logger.warning(f"No email address found for welcome email - enrollment {enrollment.id}")
                return False
            
            # Prepare context for welcome email template
            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()
            context = {
                'enrollment': enrollment,
                'student': student,
                'course': enrollment.course,
                'recipient_name': recipient_name,
                'site_domain': site.domain,
                'parent_portal_url': f"https://{site.domain}/students/",
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone,
                'facility_address': enrollment.course.facility.address if enrollment.course.facility else 'TBA'
            }
            
            # Render email templates
            subject = f"Welcome to Perth Art School - {enrollment.course.name}"
            html_content = render_to_string('core/emails/welcome.html', context)
            text_content = render_to_string('core/emails/welcome.txt', context)
            
            # Create and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[org_settings.reply_to_email],
            )
            email.attach_alternative(html_content, "text/html")

            sent = email.send()

            if sent:
                logger.info(f"Welcome email sent to {recipient_email} for enrollment {enrollment.id}")
                return True
            else:
                logger.error(f"Failed to send welcome email to {recipient_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return False
    
    @staticmethod
    def send_course_reminder(student, class_instance, days_ahead=1):
        """
        Send course reminder to student/guardian
        """
        try:
            recipient_email = student.contact_email
            recipient_name = student.guardian_name if student.guardian_name else student.get_full_name()
            
            if not recipient_email:
                logger.warning(f"No email address found for course reminder - student {student.id}")
                return False
            
            # Prepare context for reminder email template
            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()
            context = {
                'student': student,
                'class': class_instance,
                'course': class_instance.course,
                'recipient_name': recipient_name,
                'days_ahead': days_ahead,
                'class_date': class_instance.date,
                'class_time': class_instance.start_time,
                'facility': class_instance.facility,
                'classroom': class_instance.classroom,
                'teacher': class_instance.teacher,
                'site_domain': site.domain,
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone
            }
            
            # Render email templates
            subject = f"Class Reminder - {class_instance.course.name} Tomorrow" if days_ahead == 1 else f"Class Reminder - {class_instance.course.name}"
            html_content = render_to_string('core/emails/course_reminder.html', context)
            text_content = render_to_string('core/emails/course_reminder.txt', context)
            
            # Create and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[org_settings.reply_to_email],
            )
            email.attach_alternative(html_content, "text/html")

            sent = email.send()

            if sent:
                logger.info(f"Course reminder email sent to {recipient_email} for class {class_instance.id}")
                return True
            else:
                logger.error(f"Failed to send course reminder email to {recipient_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending course reminder email: {str(e)}")
            return False
    
    @staticmethod
    def send_attendance_notice(student, attendance_record):
        """
        Send attendance notice to student/guardian (for absences)
        """
        try:
            if attendance_record.status == 'present':
                # No need to send notice for present status
                return True
                
            recipient_email = student.contact_email
            recipient_name = student.guardian_name if student.guardian_name else student.get_full_name()
            
            if not recipient_email:
                logger.warning(f"No email address found for attendance notice - student {student.id}")
                return False
            
            # Prepare context for attendance notice template
            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()
            context = {
                'student': student,
                'attendance': attendance_record,
                'class': attendance_record.class_instance,
                'course': attendance_record.class_instance.course,
                'recipient_name': recipient_name,
                'status_display': attendance_record.get_status_display(),
                'site_domain': site.domain,
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone
            }
            
            # Render email templates
            subject = f"Attendance Notice - {attendance_record.class_instance.course.name}"
            html_content = render_to_string('core/emails/attendance_notice.html', context)
            text_content = render_to_string('core/emails/attendance_notice.txt', context)
            
            # Create and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                reply_to=[org_settings.reply_to_email],
            )
            email.attach_alternative(html_content, "text/html")

            sent = email.send()

            if sent:
                logger.info(f"Attendance notice email sent to {recipient_email} for attendance {attendance_record.id}")
                return True
            else:
                logger.error(f"Failed to send attendance notice email to {recipient_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending attendance notice email: {str(e)}")
            return False
    
    @staticmethod
    def send_bulk_course_reminders(days_ahead=1):
        """
        Send course reminders for all classes happening in specified days
        """
        from academics.models import Class
        from enrollment.models import Enrollment
        
        try:
            # Get target date
            target_date = timezone.now().date() + timedelta(days=days_ahead)
            
            # Get classes happening on target date
            classes = Class.objects.filter(
                date=target_date,
                is_active=True
            ).select_related('course', 'facility', 'classroom', 'teacher')
            
            sent_count = 0
            
            for class_instance in classes:
                # Get enrolled students for this class
                enrollments = Enrollment.objects.filter(
                    course=class_instance.course,
                    status='confirmed'
                ).select_related('student')
                
                for enrollment in enrollments:
                    if NotificationService.send_course_reminder(enrollment.student, class_instance, days_ahead):
                        sent_count += 1
            
            logger.info(f"Sent {sent_count} course reminder emails for classes on {target_date}")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending bulk course reminders: {str(e)}")
            return 0
    
    @staticmethod
    def send_sms_notification(phone_number: str, message: str, notification_type: str = 'general') -> bool:
        """
        Send SMS notification using configured SMS backend
        """
        try:
            from core.sms_backends import DynamicSMSBackend
            
            sms_backend = DynamicSMSBackend()
            success = sms_backend.send_sms(phone_number, message, notification_type)
            
            if success:
                logger.info(f"SMS notification sent to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send SMS notification to {phone_number}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
            return False
    
    @staticmethod
    def process_enrollment_notifications(enrollment):
        """
        Process notifications for a new enrollment (DEPRECATED)
        This method is kept for backward compatibility but now only sends confirmation
        For new enrollments, use send_enrollment_pending_email instead
        """
        try:
            # Only send confirmation email (no welcome email)
            confirmation_sent = NotificationService.send_enrollment_confirmation(enrollment)
            
            return {
                'confirmation_sent': confirmation_sent,
                'welcome_sent': False  # No longer send welcome email here
            }
            
        except Exception as e:
            logger.error(f"Error processing enrollment notifications: {str(e)}")
            return {
                'confirmation_sent': False,
                'welcome_sent': False
            }