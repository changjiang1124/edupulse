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
from core.services.invoice_service import EnrollmentInvoiceService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class to handle all automated notifications
    """
    
    @staticmethod
    def _get_sender():
        from core.models import EmailSettings
        org = OrganisationSettings.get_instance()
        config = EmailSettings.get_active_config()
        from_email = config.from_email if config and getattr(config, 'from_email', None) else settings.DEFAULT_FROM_EMAIL
        reply_to = config.reply_to_email if config and getattr(config, 'reply_to_email', None) else org.reply_to_email
        return from_email, reply_to

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
            price_summary = enrollment.get_price_summary()

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
                'recipient_email': recipient_email,
                'price_summary': price_summary,
            }
            
            # Render email templates
            subject = f"Enrolment Confirmation - {enrollment.course.name}"
            html_content = render_to_string('core/emails/enrollment_confirmation.html', context)
            text_content = render_to_string('core/emails/enrollment_confirmation.txt', context)
            
            # Create and send email
            sender_from, sender_reply = NotificationService._get_sender()
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=sender_from,
                to=[recipient_email],
                reply_to=[sender_reply],
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
            
            # Calculate total fees - use fee_breakdown if provided (includes early bird pricing)
            from decimal import Decimal
            if fee_breakdown:
                course_fee = Decimal(str(fee_breakdown.get('course_fee', 0)))
                registration_fee = Decimal(str(fee_breakdown.get('registration_fee', 0)))
                total_fee = Decimal(str(fee_breakdown.get('total_fee', 0)))
            else:
                # Fallback to enrollment stored values if no breakdown provided
                course_fee = enrollment.course_fee or Decimal('0')
                registration_fee = enrollment.registration_fee or Decimal('0')
                total_fee = course_fee + registration_fee
            
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
            sender_from, sender_reply = NotificationService._get_sender()
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=sender_from,
                to=[recipient_email],
                reply_to=[sender_reply],
            )
            email.attach_alternative(html_content, "text/html")

            # Attach PDF invoice to help parents pay with correct reference
            try:
                invoice_data = EnrollmentInvoiceService.generate_invoice_pdf(
                    enrollment,
                    fee_breakdown={
                        'course_fee': course_fee,
                        'registration_fee': registration_fee,
                        'total_fee': total_fee
                    }
                )
                if invoice_data:
                    email.attach(
                        invoice_data['filename'],
                        invoice_data['content'],
                        invoice_data['mimetype']
                    )
                else:
                    logger.warning("Invoice PDF not generated for enrollment %s", enrollment.id)
            except Exception as invoice_exc:
                logger.error("Failed to attach invoice PDF for enrollment %s: %s", enrollment.id, invoice_exc)

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
            
            org_settings = OrganisationSettings.get_instance()
            site_domain = org_settings.site_domain or Site.objects.get_current().domain

            # Prepare context for welcome email template
            context = {
                'enrollment': enrollment,
                'student': student,
                'course': enrollment.course,
                'recipient_name': recipient_name,
                'site_domain': site_domain,
                'parent_portal_url': f"https://{site_domain}/students/",
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone,
                'facility_address': enrollment.course.facility.address if enrollment.course.facility else 'TBA',
                'recipient_email': recipient_email,
                'current_year': timezone.now().year,
            }
            
            # Render email templates
            subject = f"Welcome to Perth Art School - {enrollment.course.name}"
            html_content = render_to_string('core/emails/welcome.html', context)
            text_content = render_to_string('core/emails/welcome.txt', context)
            
            # Create and send email
            sender_from, sender_reply = NotificationService._get_sender()
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=sender_from,
                to=[recipient_email],
                reply_to=[sender_reply],
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
            sender_from, sender_reply = NotificationService._get_sender()
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=sender_from,
                to=[recipient_email],
                reply_to=[sender_reply],
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
        Enhanced with batch processing for better performance
        """
        from academics.models import Class
        from enrollment.models import Enrollment
        from core.services.batch_email_service import BatchEmailService

        try:
            # Get target date
            target_date = timezone.now().date() + timedelta(days=days_ahead)

            # Get classes happening on target date with enrolled students
            classes = Class.objects.filter(
                date=target_date,
                is_active=True
            ).select_related('course', 'facility', 'classroom', 'teacher')

            if not classes.exists():
                logger.info(f"No classes found for {target_date}")
                return 0

            # Get all enrollments for these classes in a single query to avoid N+1
            class_course_ids = list(classes.values_list('course_id', flat=True))
            enrollments = Enrollment.objects.filter(
                course_id__in=class_course_ids,
                status='confirmed'
            ).select_related('student', 'course').prefetch_related('course__classes')

            # Group enrollments by course for efficient lookup
            enrollments_by_course = {}
            for enrollment in enrollments:
                course_id = enrollment.course.id
                if course_id not in enrollments_by_course:
                    enrollments_by_course[course_id] = []
                enrollments_by_course[course_id].append(enrollment)

            # Cache site and organization settings
            site_domain = Site.objects.get_current().domain
            org_settings = OrganisationSettings.get_instance()

            # Prepare bulk email data
            email_data_list = []

            for class_instance in classes:
                # Get enrollments for this class (already loaded)
                course_enrollments = enrollments_by_course.get(class_instance.course.id, [])

                for enrollment in course_enrollments:
                    student = enrollment.student
                    recipient_email = student.contact_email
                    recipient_name = student.guardian_name if student.guardian_name else student.get_full_name()

                    if not recipient_email:
                        continue

                    # Prepare context for this student/class
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
                        'site_domain': site_domain,
                        'contact_email': org_settings.contact_email,
                        'contact_phone': org_settings.contact_phone
                    }

                    email_data = {
                        'to': recipient_email,
                        'subject': f"Class Reminder - {class_instance.course.name} {'Tomorrow' if days_ahead == 1 else f'in {days_ahead} days'}",
                        'context': context,
                        'template_name': 'core/emails/course_reminder.html'
                    }
                    email_data_list.append(email_data)

            if not email_data_list:
                logger.info(f"No students with email addresses found for classes on {target_date}")
                return 0

            # Send emails in batches
            batch_service = BatchEmailService()
            stats = batch_service.send_bulk_emails(email_data_list)

            logger.info(f"Bulk course reminders completed for {target_date}: {stats}")
            return stats['sent']

        except Exception as e:
            logger.error(f"Error sending bulk course reminders: {str(e)}")
            return 0
    
    @staticmethod
    def send_sms_notification(phone_number: str, message: str, notification_type: str = 'general') -> bool:
        """
        Send SMS notification using configured SMS backend
        """
        try:
            from core.sms_backends import send_sms
            
            success = send_sms(phone_number, message, notification_type)
            
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

    @staticmethod
    def send_new_enrollment_admin_notification(enrollment):
        """
        Send notification email to all organisation admin users when a new enrollment is submitted.
        This helps admins stay informed about incoming enrollments.
        """
        try:
            from accounts.models import Staff
            from django.contrib.sites.models import Site
            
            # Get all organisation admin users with valid email addresses
            admin_users = Staff.objects.filter(
                role='admin',
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            
            if not admin_users.exists():
                logger.warning("No admin users found to notify about enrollment %s", enrollment.id)
                return False
            
            # Prepare email context
            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()
            enrollment_url = f"https://{site.domain}{reverse('enrollment:enrollment_detail', args=[enrollment.id])}"
            
            context = {
                'enrollment': enrollment,
                'student': enrollment.student,
                'course': enrollment.course,
                'enrollment_url': enrollment_url,
                'current_year': timezone.now().year,
            }
            
            # Render email templates
            subject = f"New Enrolment Submitted - {enrollment.student.get_full_name()} for {enrollment.course.name}"
            html_content = render_to_string('core/emails/new_enrollment_admin_notice.html', context)
            text_content = render_to_string('core/emails/new_enrollment_admin_notice.txt', context)
            
            # Create email with all admins as recipients
            admin_emails = list(admin_users.values_list('email', flat=True))
            
            sender_from, sender_reply = NotificationService._get_sender()
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=sender_from,
                to=admin_emails,
                reply_to=[sender_reply],
            )
            email.attach_alternative(html_content, "text/html")
            
            sent = email.send()
            
            if sent:
                logger.info(
                    "Admin notification email sent to %d admins for enrollment %s",
                    len(admin_emails), enrollment.id
                )
                return True
            else:
                logger.error("Failed to send admin notification email for enrollment %s", enrollment.id)
                return False
                
        except Exception as e:
            logger.error("Error sending admin notification email for enrollment %s: %s", enrollment.id, str(e))
            return False

