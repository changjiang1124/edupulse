from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from datetime import timedelta
import logging

from .models import Student, StudentTag, StudentLevel
from .forms import StudentForm, BulkNotificationForm
from core.models import EmailSettings, SMSSettings, EmailLog, SMSLog, NotificationQuota
from core.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

def _user_is_admin(user):
    return user.is_superuser or getattr(user, 'role', None) == 'admin'


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'core/students/list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Student.objects.filter(is_active=True).prefetch_related('tags').select_related('level')
        search = self.request.GET.get('search')

        # Support multiple tag filtering
        tag_filters = self.request.GET.getlist('tags')  # Changed from 'tag' to 'tags' and getlist

        # Support level filtering
        level_filter = self.request.GET.get('level')

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(contact_email__icontains=search) |
                Q(guardian_name__icontains=search)
            )

        # Multi-tag filtering with OR logic (students having ANY of the selected tags)
        if tag_filters:
            # Convert string IDs to integers and filter out empty values
            tag_ids = [int(tag_id) for tag_id in tag_filters if tag_id.strip()]
            if tag_ids:
                queryset = queryset.filter(tags__id__in=tag_ids)

        # Level filtering
        if level_filter:
            if level_filter == 'none':
                # Filter for students with no level assigned
                queryset = queryset.filter(level__isnull=True)
            else:
                try:
                    level_id = int(level_filter)
                    queryset = queryset.filter(level_id=level_id)
                except ValueError:
                    pass  # Invalid level filter, ignore

        return queryset.order_by('-created_at').distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_tags'] = StudentTag.objects.filter(is_active=True)
        context['student_levels'] = StudentLevel.objects.filter(is_active=True).order_by('order', 'name')

        # Pass selected tags for maintaining filter state
        selected_tag_ids = self.request.GET.getlist('tags')
        context['selected_tag_ids'] = [int(tag_id) for tag_id in selected_tag_ids if tag_id.strip()]

        # Pass selected level for maintaining filter state
        context['selected_level'] = self.request.GET.get('level', '')

        return context


class StudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/students/form.html'
    success_url = reverse_lazy('students:student_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Student {form.instance.first_name} {form.instance.last_name} added successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Add error messages for debugging
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field}: {error}')
        
        # Also check for non-field errors
        for error in form.non_field_errors():
            messages.error(self.request, f'Form error: {error}')
            
        return super().form_invalid(form)


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'core/students/detail.html'
    context_object_name = 'student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add enrollments and attendance information - with try/except to avoid errors
        try:
            from enrollment.models import Enrollment, Attendance
            context['enrollments'] = Enrollment.objects.filter(
                student=self.object
            ).select_related('course').all()
            context['attendances'] = Attendance.objects.filter(
                student=self.object
            ).select_related('class_instance__course').order_by('-attendance_time')[:10]
        except ImportError:
            context['enrollments'] = []
            context['attendances'] = []
        return context


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/students/form.html'
    
    def get_success_url(self):
        return reverse_lazy('students:student_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Student {form.instance.first_name} {form.instance.last_name} updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Add error messages for debugging
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field}: {error}')
        
        # Also check for non-field errors
        for error in form.non_field_errors():
            messages.error(self.request, f'Form error: {error}')
            
        return super().form_invalid(form)


@login_required
def bulk_notification_start(request):
    """Start bulk notification sending and return task ID for progress tracking"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    if not _user_is_admin(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    from core.services.bulk_notification_progress import BulkNotificationProgress

    form = BulkNotificationForm(request.POST)

    if not form.is_valid():
        errors = {}
        for field, field_errors in form.errors.items():
            errors[field] = field_errors
        return JsonResponse({'error': 'Form validation failed', 'details': errors}, status=400)

    # Get cleaned data
    cleaned_data = form.cleaned_data
    notification_type = cleaned_data['notification_type']
    send_to = cleaned_data['send_to']
    student_ids = cleaned_data.get('student_id_list', [])
    selected_tags = cleaned_data.get('selected_tags', [])

    # Determine recipient students (same logic as before)
    recipients = []

    if send_to == 'selected':
        if student_ids:
            recipients = Student.objects.filter(id__in=student_ids, is_active=True)
    elif send_to == 'all_active':
        recipients = Student.objects.filter(is_active=True)
    elif send_to == 'by_tag':
        if selected_tags:
            recipients = Student.objects.filter(tags__in=selected_tags, is_active=True).distinct()
    elif send_to == 'pending_enrollments':
        try:
            from enrollment.models import Enrollment
            pending_enrollment_ids = Enrollment.objects.filter(
                status='pending'
            ).values_list('student_id', flat=True).distinct()
            recipients = Student.objects.filter(id__in=pending_enrollment_ids, is_active=True)
        except ImportError:
            recipients = []
    elif send_to == 'recent_enrollments':
        try:
            from enrollment.models import Enrollment
            recent_date = timezone.now() - timedelta(days=30)
            recent_enrollment_ids = Enrollment.objects.filter(
                created_at__gte=recent_date
            ).values_list('student_id', flat=True).distinct()
            recipients = Student.objects.filter(id__in=recent_enrollment_ids, is_active=True)
        except ImportError:
            recipients = []

    if not recipients:
        return JsonResponse({'error': 'No students found matching the selected criteria'}, status=400)

    # Check notification quotas
    email_quota_ok = True
    sms_quota_ok = True

    if notification_type in ['email', 'both']:
        email_quota_ok = NotificationQuota.check_quota_available('email', len(recipients))
        if not email_quota_ok:
            return JsonResponse({
                'error': f'Email quota exceeded. Cannot send {len(recipients)} emails.'
            }, status=400)

    if notification_type in ['sms', 'both']:
        sms_quota_ok = NotificationQuota.check_quota_available('sms', len(recipients))
        if not sms_quota_ok:
            return JsonResponse({
                'error': f'SMS quota exceeded. Cannot send {len(recipients)} SMS messages.'
            }, status=400)

    # Create progress tracking task
    task_id = BulkNotificationProgress.create_task(len(recipients), notification_type)

    # Store task data in session for the actual execution
    request.session[f'bulk_task_{task_id}'] = {
        'notification_type': notification_type,
        'message_type': cleaned_data['message_type'],
        'subject': cleaned_data.get('subject', ''),
        'message': cleaned_data['message'],
        'recipient_ids': [r.id for r in recipients],
        'total_recipients': len(recipients)
    }

    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'total_recipients': len(recipients),
        'notification_type': notification_type
    })


@login_required
def bulk_notification_execute(request, task_id):
    """Execute the actual bulk notification sending with progress tracking"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    if not _user_is_admin(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    from core.services.bulk_notification_progress import BulkNotificationProgress, create_progress_callback
    from core.services.batch_email_service import BatchEmailService

    # Get task data from session
    task_data = request.session.get(f'bulk_task_{task_id}')
    if not task_data:
        BulkNotificationProgress.mark_failed(task_id, 'Task data not found')
        return JsonResponse({'error': 'Task data not found'}, status=404)

    try:
        # Get recipients
        recipient_ids = task_data['recipient_ids']
        recipients = Student.objects.filter(id__in=recipient_ids, is_active=True)

        notification_type = task_data['notification_type']
        message_type = task_data['message_type']
        subject = task_data['subject']
        message = task_data['message']

        # Create progress callback
        progress_callback = create_progress_callback(task_id)

        # Send notifications using batch service for emails
        email_sent = 0
        sms_sent = 0
        email_failed = 0
        sms_failed = 0

        # Prepare bulk email data if email notifications are needed
        if notification_type in ['email', 'both']:
            email_data_list = []
            for student in recipients:
                contact_email = student.get_contact_email()
                if contact_email:
                    context = {
                        'student': student,
                        'recipient_name': student.guardian_name if student.guardian_name else student.get_full_name(),
                        'message': message,
                        'message_type': message_type,
                        'site_domain': 'edupulse.perthartschool.com.au',  # TODO: Make configurable
                    }

                    email_data = {
                        'to': contact_email,
                        'subject': subject,
                        'context': context,
                        'template_name': 'core/emails/bulk_notification.html'
                    }
                    email_data_list.append(email_data)

            if email_data_list:
                try:
                    batch_service = BatchEmailService(progress_callback=progress_callback)
                    stats = batch_service.send_bulk_emails(email_data_list)
                    email_sent = stats['sent']
                    email_failed = stats['failed']

                    logger.info(f"Bulk email notification completed: sent {email_sent}, failed {email_failed}")
                except Exception as e:
                    logger.error(f"Bulk email notification error: {e}")
                    # Do not abort the whole task; record failures and continue with SMS
                    email_failed = len(email_data_list)
                    email_sent = 0

        # Send SMS notifications (individual processing as before)
        if notification_type in ['sms', 'both']:
            for student in recipients:
                phone = student.get_contact_phone()
                if phone:
                    try:
                        success = NotificationService.send_sms_notification(phone, message, 'bulk')
                        if success:
                            sms_sent += 1
                            SMSLog.objects.create(
                                recipient_phone=phone,
                                recipient_type='student',
                                content=message,
                                sms_type='bulk',
                                status='sent',
                                sent_at=timezone.now()
                            )
                        else:
                            sms_failed += 1
                            SMSLog.objects.create(
                                recipient_phone=phone,
                                recipient_type='student',
                                content=message,
                                sms_type='bulk',
                                status='failed',
                                error_message='SMS sending failed',
                                sent_at=timezone.now()
                            )
                    except Exception as e:
                        sms_failed += 1
                        SMSLog.objects.create(
                            recipient_phone=phone,
                            recipient_type='student',
                            content=message,
                            sms_type='bulk',
                            status='failed',
                            error_message=str(e),
                            sent_at=timezone.now()
                        )

        # Update quotas
        if sms_sent > 0:
            NotificationQuota.consume_quota('sms', sms_sent)

        # Mark task as completed
        final_stats = {
            'sent': email_sent + sms_sent,
            'failed': email_failed + sms_failed,
            'email_sent': email_sent,
            'email_failed': email_failed,
            'sms_sent': sms_sent,
            'sms_failed': sms_failed
        }

        BulkNotificationProgress.mark_completed(task_id, final_stats)

        # Clean up session data
        if f'bulk_task_{task_id}' in request.session:
            del request.session[f'bulk_task_{task_id}']

        return JsonResponse({
            'success': True,
            'stats': final_stats
        })

    except Exception as e:
        logger.error(f"Bulk notification execution error: {e}")
        BulkNotificationProgress.mark_failed(task_id, str(e))
        return JsonResponse({'error': f'Execution failed: {e}'}, status=500)


@login_required
def bulk_notification_progress(request, task_id):
    """Get progress status for a bulk notification task"""
    if not _user_is_admin(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    from core.services.bulk_notification_progress import BulkNotificationProgress

    progress_data = BulkNotificationProgress.get_progress(task_id)

    if not progress_data:
        return JsonResponse({'error': 'Task not found'}, status=404)

    return JsonResponse(progress_data)


@login_required
def bulk_notification(request):
    """Handle bulk notification sending to students"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('students:student_list')
    if not _user_is_admin(request.user):
        messages.error(request, 'Only administrators can send notifications.')
        return redirect('students:student_list')
    
    form = BulkNotificationForm(request.POST)
    
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        return redirect('students:student_list')
    
    # Get cleaned data
    cleaned_data = form.cleaned_data
    notification_type = cleaned_data['notification_type']
    message_type = cleaned_data['message_type']
    subject = cleaned_data.get('subject', '')
    message = cleaned_data['message']
    send_to = cleaned_data['send_to']
    student_ids = cleaned_data.get('student_id_list', [])
    selected_tags = cleaned_data.get('selected_tags', [])
    
    # Determine recipient students
    recipients = []
    
    if send_to == 'selected':
        if student_ids:
            recipients = Student.objects.filter(id__in=student_ids, is_active=True)
    elif send_to == 'all_active':
        recipients = Student.objects.filter(is_active=True)
    elif send_to == 'by_tag':
        if selected_tags:
            recipients = Student.objects.filter(tags__in=selected_tags, is_active=True).distinct()
    elif send_to == 'pending_enrollments':
        try:
            from enrollment.models import Enrollment
            pending_enrollment_ids = Enrollment.objects.filter(
                status='pending'
            ).values_list('student_id', flat=True).distinct()
            recipients = Student.objects.filter(id__in=pending_enrollment_ids, is_active=True)
        except ImportError:
            recipients = []
    elif send_to == 'recent_enrollments':
        try:
            from enrollment.models import Enrollment
            recent_date = timezone.now() - timedelta(days=30)
            recent_enrollment_ids = Enrollment.objects.filter(
                created_at__gte=recent_date
            ).values_list('student_id', flat=True).distinct()
            recipients = Student.objects.filter(id__in=recent_enrollment_ids, is_active=True)
        except ImportError:
            recipients = []
    
    if not recipients:
        messages.warning(request, 'No students found matching the selected criteria.')
        return redirect('students:student_list')
    
    # Check notification quotas
    email_quota_ok = True
    sms_quota_ok = True
    
    if notification_type in ['email', 'both']:
        email_quota_ok = NotificationQuota.check_quota_available('email', len(recipients))
        if not email_quota_ok:
            messages.error(request, f'Email quota exceeded. Cannot send {len(recipients)} emails.')
    
    if notification_type in ['sms', 'both']:
        sms_quota_ok = NotificationQuota.check_quota_available('sms', len(recipients))
        if not sms_quota_ok:
            messages.error(request, f'SMS quota exceeded. Cannot send {len(recipients)} SMS messages.')
    
    if not email_quota_ok or not sms_quota_ok:
        return redirect('students:student_list')
    
    # Send notifications using batch service for emails
    email_sent = 0
    sms_sent = 0
    email_failed = 0
    sms_failed = 0

    # Prepare bulk email data if email notifications are needed
    if notification_type in ['email', 'both']:
        from core.services.batch_email_service import BatchEmailService

        email_data_list = []
        for student in recipients:
            contact_email = student.get_contact_email()
            if contact_email:
                context = {
                    'student': student,
                    'recipient_name': student.guardian_name if student.guardian_name else student.get_full_name(),
                    'message': message,
                    'message_type': message_type,
                    'site_domain': 'edupulse.perthartschool.com.au',  # TODO: Make configurable
                }

                email_data = {
                    'to': contact_email,
                    'subject': subject,
                    'context': context,
                    'template_name': 'core/emails/bulk_notification.html'  # Create this template
                }
                email_data_list.append(email_data)

        if email_data_list:
            try:
                batch_service = BatchEmailService()
                stats = batch_service.send_bulk_emails(email_data_list)
                email_sent = stats['sent']
                email_failed = stats['failed']

                logger.info(f"Bulk email notification completed: sent {email_sent}, failed {email_failed}")
            except Exception as e:
                logger.error(f"Bulk email notification error: {e}")
                email_failed = len(email_data_list)

    # Send SMS notifications (individual processing as before)
    if notification_type in ['sms', 'both']:
        for student in recipients:
            # Send SMS
            if student.guardian_phone or student.phone:
                phone = student.guardian_phone or student.phone
                try:
                    success = NotificationService.send_sms_notification(phone, message, 'bulk')
                    if success:
                        sms_sent += 1
                        SMSLog.objects.create(
                            recipient_phone=phone,
                            recipient_type='student',
                            content=message,
                            sms_type='bulk',
                            status='sent',
                            sent_at=timezone.now()
                        )
                    else:
                        sms_failed += 1
                        SMSLog.objects.create(
                            recipient_phone=phone,
                            recipient_type='student',
                            content=message,
                            sms_type='bulk',
                            status='failed',
                            error_message='SMS sending failed',
                            sent_at=timezone.now()
                        )
                except Exception as e:
                    sms_failed += 1
                    SMSLog.objects.create(
                        recipient_phone=phone,
                        recipient_type='student',
                        content=message,
                        sms_type='bulk',
                        status='failed',
                        error_message=str(e),
                        sent_at=timezone.now()
                    )
    
    # Update quotas
    if email_sent > 0:
        NotificationQuota.consume_quota('email', email_sent)
    if sms_sent > 0:
        NotificationQuota.consume_quota('sms', sms_sent)
    
    # Show success message
    success_parts = []
    if email_sent > 0:
        success_parts.append(f'{email_sent} emails sent')
    if sms_sent > 0:
        success_parts.append(f'{sms_sent} SMS messages sent')
    
    if success_parts:
        messages.success(request, f'Notifications sent successfully: {", ".join(success_parts)}')
    
    # Show failure messages if any
    if email_failed > 0:
        messages.warning(request, f'{email_failed} emails failed to send')
    if sms_failed > 0:
        messages.warning(request, f'{sms_failed} SMS messages failed to send')
    
    return redirect('students:student_list')


def _send_email_notification(student, email, subject, message, message_type):
    """Send email notification to student"""
    from django.core.mail import EmailMessage, get_connection
    
    # Get active email configuration
    email_config = EmailSettings.get_active_config()

    # Get organisation settings for default reply-to
    from core.models import OrganisationSettings
    org_settings = OrganisationSettings.get_instance()
    default_reply_to = org_settings.reply_to_email

    if email_config:
        from_name = email_config.from_name
        from_email_address = email_config.from_email
        reply_to_email = email_config.reply_to_email or default_reply_to
        backend_label = email_config.get_email_backend_type_display()
    else:
        from django.conf import settings
        from_name = getattr(settings, 'DEFAULT_FROM_NAME', 'EduPulse Notifications')
        from_email_address = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
        if not from_email_address:
            raise Exception('No active email configuration found and DEFAULT_FROM_EMAIL is not set')
        reply_to_email = default_reply_to
        backend_label = 'environment'
    
    # Create email backend connection using configured backend
    backend = get_connection()
    
    # Create and send email
    email_message = EmailMessage(
        subject=subject,
        body=message,
        from_email=f'{from_name} <{from_email_address}>' if from_name else from_email_address,
        to=[email],
        reply_to=[reply_to_email] if reply_to_email else None,
        connection=backend
    )
    
    email_message.send()
    
    # Log successful email
    EmailLog.objects.create(
        recipient_email=email,
        recipient_type='student',
        subject=subject,
        content=message,
        email_type=message_type,
        status='sent',
        email_backend=backend_label,
        sent_at=timezone.now()
    )


def _send_sms_notification(student, phone, message, message_type):
    """Send SMS notification to student"""
    from core.sms_backends import send_sms
    
    # Get active SMS configuration
    sms_config = SMSSettings.get_active_config()
    if not sms_config:
        raise Exception('No active SMS configuration found')
    
    # Send SMS using the send_sms function
    try:
        send_sms(phone, message, message_type)
        
        # Log successful SMS
        SMSLog.objects.create(
            recipient_phone=phone,
            recipient_type='student',
            content=message,
            sms_type=message_type,
            status='sent',
            message_sid='',  # send_sms doesn't return message_sid directly
            backend_type=sms_config.get_sms_backend_type_display(),
            sent_at=timezone.now()
        )
    except Exception as e:
        # Log failed SMS
        SMSLog.objects.create(
            recipient_phone=phone,
            recipient_type='student',
            content=message,
            sms_type=message_type,
            status='failed',
            error_message=str(e),
            backend_type=sms_config.get_sms_backend_type_display() if sms_config else 'unknown'
        )
        raise e


class StudentSearchView(LoginRequiredMixin, View):
    """AJAX endpoint for student search"""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'students': []})
        
        # Search students
        students = Student.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(contact_email__icontains=query),
            is_active=True
        ).order_by('last_name', 'first_name')[:10]
        
        # Format results
        results = []
        for student in students:
            results.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.contact_email or '',
                'full_name': f"{student.first_name} {student.last_name}"
            })
        
        return JsonResponse({'students': results})


@login_required
@csrf_protect
@require_POST
def bulk_tag_operation(request):
    """Handle bulk tag operations (add/remove tags from multiple students)"""
    try:
        # Get data from request
        student_ids = request.POST.get('student_ids', '').strip()
        operation = request.POST.get('operation', '')  # 'add' or 'remove'

        # Support both tag IDs and tag names
        tag_ids = request.POST.get('tag_ids', '').strip()
        tag_names = request.POST.get('tag_names', '').strip()

        if not student_ids or not operation or (not tag_ids and not tag_names):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            }, status=400)

        # Parse student IDs
        try:
            student_id_list = [int(id.strip()) for id in student_ids.split(',') if id.strip()]
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid student IDs format'
            }, status=400)

        # Validate operation
        if operation not in ['add', 'remove']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid operation. Must be "add" or "remove"'
            }, status=400)

        # Get students
        students = Student.objects.filter(id__in=student_id_list, is_active=True)
        if not students.exists():
            return JsonResponse({
                'success': False,
                'error': 'No valid students found'
            }, status=404)

        # Process tags - support both IDs and names
        tags = []
        created_tags = []

        # Handle tag IDs (existing functionality)
        if tag_ids:
            try:
                tag_id_list = [int(id.strip()) for id in tag_ids.split(',') if id.strip()]
                existing_tags = StudentTag.objects.filter(id__in=tag_id_list, is_active=True)
                tags.extend(existing_tags)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid tag IDs format'
                }, status=400)

        # Handle tag names (new functionality)
        if tag_names:
            tag_name_list = [name.strip() for name in tag_names.split(',') if name.strip()]
            for tag_name in tag_name_list:
                if operation == 'add':
                    # For add operation, create tags if they don't exist
                    tag, created = StudentTag.get_or_create_by_name(tag_name)
                    if tag:
                        tags.append(tag)
                        if created:
                            created_tags.append(tag)
                else:
                    # For remove operation, only use existing tags
                    try:
                        existing_tag = StudentTag.objects.get(
                            name=tag_name.lower().strip(),
                            is_active=True
                        )
                        tags.append(existing_tag)
                    except StudentTag.DoesNotExist:
                        # Ignore non-existent tags for remove operation
                        continue

        if not tags:
            error_msg = 'No valid tags found'
            if operation == 'remove':
                error_msg += ' (tags must exist to be removed)'
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=404)

        # Perform bulk operation
        success_count = 0
        for student in students:
            if operation == 'add':
                # Add tags to student
                student.tags.add(*tags)
            else:  # remove
                # Remove tags from student
                student.tags.remove(*tags)
            success_count += 1

            # Log activity for each student
            tag_names_str = ', '.join([tag.name for tag in tags])
            activity_title = f'Tags {"added" if operation == "add" else "removed"}: {tag_names_str}'
            from .models import StudentActivity
            StudentActivity.create_activity(
                student=student,
                activity_type='other',
                title=activity_title,
                description=f'Bulk tag operation performed by staff',
                performed_by=request.user
            )

        # Prepare response message
        message = f'Successfully {operation}ed tags for {success_count} students'
        if created_tags and operation == 'add':
            created_names = [tag.name for tag in created_tags]
            message += f'. Created new tags: {", ".join(created_names)}'

        return JsonResponse({
            'success': True,
            'message': message,
            'students_updated': success_count,
            'operation': operation,
            'tag_count': len(tags),
            'created_tags': [{'id': tag.id, 'name': tag.name, 'colour': tag.colour} for tag in created_tags]
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
@csrf_protect
@require_POST
def student_tag_management(request, student_id):
    """Handle individual student tag management (add/remove single tag)
    
    Supports both tag_id (for existing tags) and tag_name (for creating new tags).
    """
    try:
        student = get_object_or_404(Student, id=student_id, is_active=True)
        operation = request.POST.get('operation', '')  # 'add' or 'remove'
        tag_id = request.POST.get('tag_id', '').strip()
        tag_name = request.POST.get('tag_name', '').strip()

        # Validate operation
        if operation not in ['add', 'remove']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid operation. Must be "add" or "remove"'
            }, status=400)

        # Must have either tag_id or tag_name
        if not tag_id and not tag_name:
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters: tag_id or tag_name'
            }, status=400)

        # Get or create tag
        tag = None
        created = False

        if tag_id:
            # Get existing tag by ID
            try:
                tag_id_int = int(tag_id)
                tag = get_object_or_404(StudentTag, id=tag_id_int, is_active=True)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid tag ID format'
                }, status=400)
        elif tag_name:
            if operation == 'add':
                # For add operation, create tag if it doesn't exist
                tag, created = StudentTag.get_or_create_by_name(tag_name)
                if not tag:
                    return JsonResponse({
                        'success': False,
                        'error': 'Failed to create tag. Please check the tag name format.'
                    }, status=400)
            else:
                # For remove operation, only use existing tags
                try:
                    tag = StudentTag.objects.get(
                        name=tag_name.lower().strip(),
                        is_active=True
                    )
                except StudentTag.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': f'Tag "{tag_name}" does not exist'
                    }, status=404)

        # Perform operation
        if operation == 'add':
            if student.tags.filter(id=tag.id).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Student already has tag "{tag.name}"'
                })
            student.tags.add(tag)
            if created:
                message = f'Tag "{tag.name}" created and added successfully'
            else:
                message = f'Tag "{tag.name}" added successfully'
        else:  # remove
            if not student.tags.filter(id=tag.id).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Student does not have tag "{tag.name}"'
                })
            student.tags.remove(tag)
            message = f'Tag "{tag.name}" removed successfully'

        # Log activity
        from .models import StudentActivity
        StudentActivity.create_activity(
            student=student,
            activity_type='other',
            title=f'Tag {operation}ed: {tag.name}',
            description=f'Tag management performed by staff',
            performed_by=request.user
        )

        # Return updated tag list
        current_tags = list(student.tags.values('id', 'name', 'colour'))

        return JsonResponse({
            'success': True,
            'message': message,
            'operation': operation,
            'created': created,
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'colour': tag.colour
            },
            'current_tags': current_tags
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def get_available_tags(request):
    """Get all available tags for tag selection interface"""
    try:
        tags = StudentTag.objects.filter(is_active=True).order_by('name')
        tag_data = [
            {
                'id': tag.id,
                'name': tag.name,
                'colour': tag.colour,
                'student_count': tag.students.filter(is_active=True).count()
            }
            for tag in tags
        ]

        return JsonResponse({
            'success': True,
            'tags': tag_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def search_tags(request):
    """Search tags for autocomplete functionality"""
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 10)), 50)  # Max 50 results

        if len(query) < 2:
            return JsonResponse({
                'success': True,
                'tags': []
            })

        # Search for tags using the model's search method
        tags = StudentTag.search_tags(query, limit)

        tag_data = [
            {
                'id': tag.id,
                'name': tag.name,
                'colour': tag.colour,
                'student_count': tag.students.filter(is_active=True).count()
            }
            for tag in tags
        ]

        return JsonResponse({
            'success': True,
            'tags': tag_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def suggest_tag_name(request):
    """Suggest tag names for text input autocomplete"""
    try:
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 5)), 20)  # Max 20 suggestions

        if len(query) < 1:
            return JsonResponse({
                'success': True,
                'suggestions': []
            })

        # Search for existing tag names
        tags = StudentTag.search_tags(query, limit)

        suggestions = [
            {
                'name': tag.name,
                'exists': True,
                'colour': tag.colour,
                'student_count': tag.students.filter(is_active=True).count()
            }
            for tag in tags
        ]

        # If the query doesn't exactly match any existing tag, suggest creating it
        query_lower = query.lower().strip()
        existing_names = {tag.name for tag in tags}

        if query_lower not in existing_names and query_lower:
            suggestions.insert(0, {
                'name': query_lower,
                'exists': False,
                'colour': StudentTag.generate_random_color(),
                'student_count': 0
            })

        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)
