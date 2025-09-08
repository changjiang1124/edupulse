from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView, ListView
from django.views import View
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, date, timedelta
import os
import uuid
import json
from decimal import Decimal, InvalidOperation
from django.conf import settings

from accounts.models import Staff
from students.models import Student
from academics.models import Course, Class
from facilities.models import Facility, Classroom
from enrollment.models import Enrollment, Attendance
from .models import ClockInOut, EmailSettings, SMSSettings, EmailLog, SMSLog, NotificationQuota, TeacherAttendance, OrganisationSettings
from .forms import EmailSettingsForm, TestEmailForm, SMSSettingsForm, TestSMSForm, NotificationForm, BulkNotificationForm
from .utils.gps_utils import (
    verify_teacher_location, 
    get_today_classes_for_teacher_at_facility,
    get_client_ip, 
    get_user_agent
)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view"""
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context.update({
            'total_students': Student.objects.filter(is_active=True).count(),
            'total_courses': Course.objects.filter(status='published').count(),
            'total_staff': Staff.objects.filter(is_active_staff=True).count(),
            'pending_enrollments': Enrollment.objects.filter(status='pending').count(),
            
            # Upcoming classes
            'upcoming_classes': Class.objects.filter(
                date__gte=timezone.now().date(),
                is_active=True
            ).order_by('date', 'start_time')[:5],
            
            # Recent enrollments
            'recent_enrollments': Enrollment.objects.select_related(
                'student', 'course'
            ).order_by('-created_at')[:5],
        })
        
        return context


class ClockInOutView(LoginRequiredMixin, TemplateView):
    template_name = 'core/clock/clockinout.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get today's clock records for the current user
        today = timezone.now().date()
        context['today_records'] = ClockInOut.objects.filter(
            staff=self.request.user,
            timestamp__date=today
        ).order_by('timestamp')
        
        # Check if user is currently clocked in
        last_record = ClockInOut.objects.filter(
            staff=self.request.user
        ).order_by('-timestamp').first()
        
        context['is_clocked_in'] = (
            last_record and last_record.status == 'clock_in' and 
            last_record.timestamp.date() == today
        )
        
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if action in ['clock_in', 'clock_out']:
            ClockInOut.objects.create(
                staff=request.user,
                status=action,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None
            )
            
            action_text = 'clocked in' if action == 'clock_in' else 'clocked out'
            messages.success(request, f'Successfully {action_text}!')
        
        return redirect('core:clockinout')


class TimesheetView(LoginRequiredMixin, TemplateView):
    template_name = 'core/clock/timesheet.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range from request or default to current week
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if not start_date or not end_date:
            # Default to current week
            today = timezone.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = start_of_week.strftime('%Y-%m-%d')
            end_date = end_of_week.strftime('%Y-%m-%d')
        
        # Convert string dates back to date objects
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get clock records for the date range
        records = ClockInOut.objects.filter(
            staff=self.request.user,
            timestamp__date__range=[start_date_obj, end_date_obj]
        ).order_by('timestamp')
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'records': records,
        })
        
        return context


@csrf_exempt
@require_http_methods(["POST"])
def tinymce_upload_image(request):
    """Handle TinyMCE image uploads"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        file = request.FILES['file']
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            return JsonResponse({'error': 'File must be an image'}, status=400)
        
        # Validate file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File size must be less than 5MB'}, status=400)
        
        # Generate unique filename
        file_ext = os.path.splitext(file.name)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'images')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, unique_filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Return the URL for TinyMCE
        file_url = f"/media/uploads/images/{unique_filename}"
        
        return JsonResponse({
            'location': request.build_absolute_uri(file_url)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Email Configuration Views

@login_required
def email_settings_view(request):
    """Email configuration management view"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        messages.error(request, 'Only administrators can access email settings.')
        return redirect('dashboard')
    
    # Get or create email settings instance
    email_settings = EmailSettings.get_active_config()
    if not email_settings:
        email_settings = EmailSettings()
    
    if request.method == 'POST':
        form = EmailSettingsForm(request.POST, instance=email_settings)
        if form.is_valid():
            email_settings = form.save(commit=False)
            email_settings.updated_by = request.user
            email_settings.save()
            
            messages.success(request, f'Email settings updated successfully. Configuration: {email_settings.get_email_backend_type_display()}')
            return redirect('core:email_settings')
    else:
        form = EmailSettingsForm(instance=email_settings)
    
    # Get recent email logs for statistics
    recent_logs = EmailLog.objects.all().order_by('-sent_at')[:10]
    
    # Get statistics
    stats = {
        'total_sent': EmailLog.objects.filter(status='sent').count(),
        'total_failed': EmailLog.objects.filter(status='failed').count(),
        'recent_count': EmailLog.objects.filter(
            sent_at__gte=timezone.now() - timedelta(days=7)
        ).count()
    }
    
    context = {
        'form': form,
        'email_settings': email_settings,
        'recent_logs': recent_logs,
        'stats': stats,
        'page_title': 'Email Configuration'
    }
    
    return render(request, 'core/settings/email.html', context)


@require_http_methods(['POST'])
@login_required
def test_email_connection(request):
    """AJAX view to test email connection"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        config_id = request.POST.get('config_id')
        if config_id:
            config = get_object_or_404(EmailSettings, pk=config_id)
        else:
            config = EmailSettings.get_active_config()
            if not config:
                return JsonResponse({'error': 'No email configuration found'}, status=400)
        
        success = config.test_connection()
        
        return JsonResponse({
            'success': success,
            'status': config.test_status,
            'message': config.test_message,
            'last_test': config.last_test_date.isoformat() if config.last_test_date else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(['POST'])
@login_required
def send_test_email(request):
    """AJAX view to send test email"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        recipient_email = request.POST.get('recipient_email')
        if not recipient_email:
            return JsonResponse({'error': 'Recipient email is required'}, status=400)
        
        config = EmailSettings.get_active_config()
        if not config:
            return JsonResponse({'error': 'No active email configuration found'}, status=400)
        
        # Send test email
        config.send_test_email(recipient_email)
        
        return JsonResponse({
            'success': True,
            'message': f'Test email sent successfully to {recipient_email}',
            'config_type': config.get_email_backend_type_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def email_logs_view(request):
    """View for email sending logs"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        messages.error(request, 'Only administrators can access email logs.')
        return redirect('dashboard')
    
    # Filter parameters
    status_filter = request.GET.get('status', '')
    email_type_filter = request.GET.get('email_type', '')
    recipient_type_filter = request.GET.get('recipient_type', '')
    
    # Base queryset
    logs = EmailLog.objects.all()
    
    # Apply filters
    if status_filter:
        logs = logs.filter(status=status_filter)
    if email_type_filter:
        logs = logs.filter(email_type=email_type_filter)
    if recipient_type_filter:
        logs = logs.filter(recipient_type=recipient_type_filter)
    
    logs = logs.order_by('-sent_at')[:100]  # Limit to recent 100 entries
    
    # Get filter choices for dropdown
    filter_choices = {
        'statuses': EmailLog.STATUS_CHOICES,
        'email_types': EmailLog.TYPE_CHOICES,
        'recipient_types': ['staff', 'student', 'guardian', 'unknown']
    }
    
    context = {
        'logs': logs,
        'filter_choices': filter_choices,
        'current_filters': {
            'status': status_filter,
            'email_type': email_type_filter,
            'recipient_type': recipient_type_filter
        },
        'page_title': 'Email Logs'
    }
    
    return render(request, 'core/settings/email_logs.html', context)


# SMS Configuration Views

@login_required
def sms_settings_view(request):
    """SMS configuration management view"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        messages.error(request, 'Only administrators can access SMS settings.')
        return redirect('dashboard')
    
    # Get or create SMS settings instance
    sms_settings = SMSSettings.get_active_config()
    if not sms_settings:
        sms_settings = SMSSettings()
    
    if request.method == 'POST':
        form = SMSSettingsForm(request.POST, instance=sms_settings)
        if form.is_valid():
            sms_settings = form.save(commit=False)
            sms_settings.updated_by = request.user
            sms_settings.save()
            
            messages.success(request, f'SMS settings updated successfully. Configuration: {sms_settings.get_sms_backend_type_display()}')
            return redirect('core:sms_settings')
    else:
        form = SMSSettingsForm(instance=sms_settings)
    
    # Get recent SMS logs for statistics
    recent_logs = SMSLog.objects.all().order_by('-sent_at')[:10]
    
    # Get statistics
    stats = {
        'total_sent': SMSLog.objects.filter(status='sent').count(),
        'total_failed': SMSLog.objects.filter(status='failed').count(),
        'recent_count': SMSLog.objects.filter(
            sent_at__gte=timezone.now() - timedelta(days=7)
        ).count()
    }
    
    context = {
        'form': form,
        'sms_settings': sms_settings,
        'recent_logs': recent_logs,
        'stats': stats,
        'page_title': 'SMS Configuration'
    }
    
    return render(request, 'core/settings/sms.html', context)


@require_http_methods(['POST'])
@login_required
def test_sms_connection(request):
    """AJAX view to test SMS connection"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        config_id = request.POST.get('config_id')
        if config_id:
            config = get_object_or_404(SMSSettings, pk=config_id)
        else:
            config = SMSSettings.get_active_config()
            if not config:
                return JsonResponse({'error': 'No SMS configuration found'}, status=400)
        
        success = config.test_connection()
        
        return JsonResponse({
            'success': success,
            'status': config.test_status,
            'message': config.test_message,
            'last_test': config.last_test_date.isoformat() if config.last_test_date else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(['POST'])
@login_required
def send_test_sms(request):
    """AJAX view to send test SMS"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        recipient_phone = request.POST.get('recipient_phone')
        if not recipient_phone:
            return JsonResponse({'error': 'Recipient phone number is required'}, status=400)
        
        config = SMSSettings.get_active_config()
        if not config:
            return JsonResponse({'error': 'No active SMS configuration found'}, status=400)
        
        # Send test SMS
        config.send_test_sms(recipient_phone)
        
        return JsonResponse({
            'success': True,
            'message': f'Test SMS sent successfully to {recipient_phone}',
            'config_type': config.get_sms_backend_type_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def sms_logs_view(request):
    """View for SMS sending logs"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        messages.error(request, 'Only administrators can access SMS logs.')
        return redirect('dashboard')
    
    # Filter parameters
    status_filter = request.GET.get('status', '')
    sms_type_filter = request.GET.get('sms_type', '')
    recipient_type_filter = request.GET.get('recipient_type', '')
    
    # Base queryset
    logs = SMSLog.objects.all()
    
    # Apply filters
    if status_filter:
        logs = logs.filter(status=status_filter)
    if sms_type_filter:
        logs = logs.filter(sms_type=sms_type_filter)
    if recipient_type_filter:
        logs = logs.filter(recipient_type=recipient_type_filter)
    
    logs = logs.order_by('-sent_at')[:100]  # Limit to recent 100 entries
    
    # Get filter choices for dropdown
    filter_choices = {
        'statuses': SMSLog.STATUS_CHOICES,
        'sms_types': SMSLog.TYPE_CHOICES,
        'recipient_types': ['staff', 'student', 'guardian', 'unknown']
    }
    
    context = {
        'logs': logs,
        'filter_choices': filter_choices,
        'current_filters': {
            'status': status_filter,
            'sms_type': sms_type_filter,
            'recipient_type': recipient_type_filter
        },
        'page_title': 'SMS Logs'
    }
    
    return render(request, 'core/settings/sms_logs.html', context)


# Notification System Views

@login_required
@require_http_methods(["POST"])
def send_notification_view(request):
    """AJAX view to send notifications to students"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    form = NotificationForm(request.POST)
    if not form.is_valid():
        return JsonResponse({
            'success': False, 
            'errors': form.errors
        }, status=400)
    
    try:
        student_ids = form.cleaned_data['student_id_list']
        notification_type = form.cleaned_data['notification_type'] 
        message_type = form.cleaned_data['message_type']
        subject = form.cleaned_data.get('subject', '')
        message = form.cleaned_data['message']
        
        # Get students with contact info
        students = Student.objects.filter(id__in=student_ids)
        if not students:
            return JsonResponse({'success': False, 'error': 'No valid students found'})
        
        results = {'email_sent': 0, 'sms_sent': 0, 'errors': []}
        
        # Check quotas before sending
        if notification_type in ['email', 'both']:
            email_quota = NotificationQuota.get_current_quota('email')
            if not NotificationQuota.check_quota_available('email', students.count()):
                return JsonResponse({
                    'success': False, 
                    'error': f'Email quota exceeded. Available: {email_quota.remaining_quota}, Required: {students.count()}'
                })
        
        if notification_type in ['sms', 'both']:
            sms_quota = NotificationQuota.get_current_quota('sms')
            if not NotificationQuota.check_quota_available('sms', students.count()):
                return JsonResponse({
                    'success': False, 
                    'error': f'SMS quota exceeded. Available: {sms_quota.remaining_quota}, Required: {students.count()}'
                })
        
        # Process each student
        for student in students:
            # Get smart contact info from enrollments
            contact_info = _get_student_contact_info(student)
            
            if notification_type in ['email', 'both'] and contact_info['email']:
                try:
                    _send_email_notification(
                        recipient_email=contact_info['email'],
                        recipient_name=contact_info['name'],
                        subject=subject,
                        message=message,
                        message_type=message_type,
                        recipient_type=contact_info['type']
                    )
                    results['email_sent'] += 1
                except Exception as e:
                    results['errors'].append(f'Email to {contact_info["name"]}: {str(e)}')
            
            if notification_type in ['sms', 'both'] and contact_info['phone']:
                try:
                    _send_sms_notification(
                        recipient_phone=contact_info['phone'],
                        recipient_name=contact_info['name'],
                        message=message,
                        message_type=message_type,
                        recipient_type=contact_info['type']
                    )
                    results['sms_sent'] += 1
                except Exception as e:
                    results['errors'].append(f'SMS to {contact_info["name"]}: {str(e)}')
        
        # Consume quotas
        if results['email_sent'] > 0:
            NotificationQuota.consume_quota('email', results['email_sent'])
        if results['sms_sent'] > 0:
            NotificationQuota.consume_quota('sms', results['sms_sent'])
        
        return JsonResponse({
            'success': True,
            'results': results,
            'message': f"Sent {results['email_sent']} emails and {results['sms_sent']} SMS messages"
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _get_student_contact_info(student):
    """Get intelligent contact information for a student based on enrollment data"""
    from enrollment.models import Enrollment
    
    # Try to get contact info from latest enrollment
    latest_enrollment = Enrollment.objects.filter(student=student).order_by('-created_at').first()
    
    if latest_enrollment and latest_enrollment.form_data:
        form_data = latest_enrollment.form_data
        contact_info = form_data.get('contact_info', {})
        
        if contact_info:
            return {
                'name': contact_info.get('primary_contact_name', f'{student.first_name} {student.last_name}'),
                'email': contact_info.get('primary_email', ''),
                'phone': contact_info.get('primary_phone', ''),
                'type': contact_info.get('contact_type', 'student')
            }
    
    # Fallback to student model data
    return {
        'name': f'{student.first_name} {student.last_name}',
        'email': student.get_contact_email() or '',
        'phone': student.get_contact_phone() or '',
        'type': 'guardian' if student.guardian_email or student.guardian_phone else 'student'
    }


def _send_email_notification(recipient_email, recipient_name, subject, message, message_type, recipient_type):
    """Send email notification using the configured email backend"""
    from django.core.mail import EmailMessage
    
    email = EmailMessage(
        subject=subject,
        body=f"Dear {recipient_name},\n\n{message}\n\nBest regards,\nPerth Art School",
        from_email=None,  # Will use configured from_email
        to=[recipient_email]
    )
    
    email.send()


def _send_sms_notification(recipient_phone, recipient_name, message, message_type, recipient_type):
    """Send SMS notification using the configured SMS backend"""
    from core.sms_backends import send_sms
    
    # Format message for SMS
    sms_message = f"Hi {recipient_name}, {message} - Perth Art School"
    
    # Truncate if too long
    if len(sms_message) > 160:
        sms_message = sms_message[:157] + "..."
    
    send_sms(recipient_phone, sms_message, message_type)


@login_required
def get_notification_quotas(request):
    """AJAX endpoint to get current notification quotas"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    email_quota = NotificationQuota.get_current_quota('email')
    sms_quota = NotificationQuota.get_current_quota('sms')
    
    return JsonResponse({
        'success': True,
        'quotas': {
            'email': {
                'used': email_quota.used_count,
                'limit': email_quota.monthly_limit,
                'remaining': email_quota.remaining_quota,
                'percentage': email_quota.usage_percentage
            },
            'sms': {
                'used': sms_quota.used_count,
                'limit': sms_quota.monthly_limit,
                'remaining': sms_quota.remaining_quota,
                'percentage': sms_quota.usage_percentage
            }
        }
    })


# Teacher Attendance Views

class TeacherClockView(LoginRequiredMixin, TemplateView):
    """
    Main teacher clock in/out page
    """
    template_name = 'core/teacher_attendance/clock.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ensure user is a teacher
        if not (self.request.user.is_authenticated and 
                hasattr(self.request.user, 'role') and 
                self.request.user.role == 'teacher'):
            context['error'] = 'Access denied. Teachers only.'
            return context
        
        context['teacher'] = self.request.user
        context['google_maps_api_key'] = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        context['today'] = timezone.now().date()
        
        # Get recent attendance records for this teacher
        recent_records = TeacherAttendance.objects.filter(
            teacher=self.request.user
        ).select_related('facility').prefetch_related('classes')[:5]
        context['recent_records'] = recent_records
        
        return context


class TeacherLocationVerifyView(LoginRequiredMixin, View):
    """
    AJAX endpoint to verify teacher's GPS location and get available classes
    """
    
    def post(self, request):
        if not (request.user.is_authenticated and 
                hasattr(request.user, 'role') and 
                request.user.role == 'teacher'):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. Teachers only.'
            }, status=403)
        
        try:
            data = json.loads(request.body)
            lat = float(data.get('latitude'))
            lon = float(data.get('longitude'))
        except (json.JSONDecodeError, TypeError, ValueError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid location data provided.'
            }, status=400)
        
        # Verify location
        location_result = verify_teacher_location(lat, lon)
        
        if not location_result['valid']:
            return JsonResponse({
                'success': False,
                'error': location_result['error'],
                'location_verified': False
            })
        
        facility = location_result['facility']
        
        # Get today's classes for this teacher at this facility
        today_classes = get_today_classes_for_teacher_at_facility(
            teacher=request.user,
            facility=facility
        )
        
        # Prepare class data for frontend
        classes_data = []
        for cls in today_classes:
            classes_data.append({
                'id': cls.id,
                'course_name': cls.course.name,
                'start_time': cls.start_time.strftime('%H:%M'),
                'duration': cls.duration_minutes,
                'classroom': cls.classroom.name if cls.classroom else 'TBA'
            })
        
        return JsonResponse({
            'success': True,
            'location_verified': True,
            'facility': {
                'id': facility.id,
                'name': facility.name,
                'address': facility.address
            },
            'distance': round(location_result['distance'], 1),
            'classes': classes_data,
            'has_classes': len(classes_data) > 0
        })


class TeacherClockSubmitView(LoginRequiredMixin, View):
    """
    Handle teacher clock in/out submission
    """
    
    def post(self, request):
        if not (request.user.is_authenticated and 
                hasattr(request.user, 'role') and 
                request.user.role == 'teacher'):
            return JsonResponse({
                'success': False,
                'error': 'Access denied. Teachers only.'
            }, status=403)
        
        try:
            data = json.loads(request.body)
            
            # Extract and validate required fields
            clock_type = data.get('clock_type')
            if clock_type not in ['clock_in', 'clock_out']:
                raise ValueError('Invalid clock type')
            
            lat = Decimal(str(data.get('latitude')))
            lon = Decimal(str(data.get('longitude')))
            facility_id = int(data.get('facility_id'))
            selected_class_ids = data.get('class_ids', [])
            notes = data.get('notes', '').strip()
            
        except (json.JSONDecodeError, TypeError, ValueError, InvalidOperation) as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid data provided: {str(e)}'
            }, status=400)
        
        # Re-verify location (security measure)
        location_result = verify_teacher_location(float(lat), float(lon))
        
        if not location_result['valid']:
            return JsonResponse({
                'success': False,
                'error': f"Location verification failed: {location_result['error']}"
            })
        
        facility = location_result['facility']
        
        if facility.id != facility_id:
            return JsonResponse({
                'success': False,
                'error': 'Facility mismatch. Please refresh and try again.'
            })
        
        # Create attendance record
        try:
            attendance = TeacherAttendance.objects.create(
                teacher=request.user,
                clock_type=clock_type,
                facility=facility,
                latitude=lat,
                longitude=lon,
                distance_from_facility=location_result['distance'],
                location_verified=True,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                notes=notes
            )
            
            # Add selected classes
            if selected_class_ids:
                selected_classes = Class.objects.filter(
                    id__in=selected_class_ids,
                    teacher=request.user,
                    date=timezone.now().date(),
                    facility=facility,
                    is_active=True
                )
                attendance.classes.set(selected_classes)
            
            # Success message
            action_text = 'clocked in' if clock_type == 'clock_in' else 'clocked out'
            class_count = len(selected_class_ids) if selected_class_ids else 0
            class_text = f' for {class_count} class(es)' if class_count > 0 else ''
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully {action_text} at {facility.name}{class_text}.',
                'attendance_id': attendance.id,
                'timestamp': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to record attendance: {str(e)}'
            }, status=500)


class TeacherAttendanceHistoryView(LoginRequiredMixin, ListView):
    """
    Display teacher's attendance history
    """
    model = TeacherAttendance
    template_name = 'core/teacher_attendance/history.html'
    context_object_name = 'attendance_records'
    paginate_by = 20
    
    def get_queryset(self):
        if not (self.request.user.is_authenticated and 
                hasattr(self.request.user, 'role') and 
                self.request.user.role == 'teacher'):
            return TeacherAttendance.objects.none()
        
        queryset = TeacherAttendance.objects.filter(
            teacher=self.request.user
        ).select_related('facility').prefetch_related('classes__course')
        
        # Filter by date range if provided
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        return queryset.order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['teacher'] = self.request.user
        return context


# QR Code Teacher Attendance Views

class TeacherQRAttendanceView(LoginRequiredMixin, View):
    """
    Teacher QR Code Attendance View - Handles QR code scanning and attendance
    """
    template_name = 'core/teacher_attendance/qr_attendance.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure only teachers can access this view
        if not hasattr(request.user, 'role') or request.user.role != 'teacher':
            messages.error(request, 'Access denied. This page is for teachers only.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """Display QR code attendance interface"""
        data_param = request.GET.get('data')
        
        context = {
            'current_time': timezone.now(),
            'qr_data_param': data_param
        }
        
        # If QR code data is provided, validate it
        if data_param:
            from core.services import QRCodeService
            validation_result = QRCodeService.validate_qr_code(data_param)
            
            context.update({
                'qr_validation': validation_result,
                'facility': validation_result.get('facility'),
                'class_instance': validation_result.get('class_instance')
            })
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle QR code attendance submission"""
        from core.services import QRCodeService
        from core.utils.gps_utils import verify_teacher_location
        from core.models import TeacherAttendance
        from academics.models import Class
        
        # Get form data
        data_param = request.POST.get('qr_data')
        clock_type = request.POST.get('clock_type', 'clock_in')
        selected_classes = request.POST.getlist('classes')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if not data_param:
            return JsonResponse({
                'success': False,
                'message': 'QR code data is required'
            })
        
        # Validate QR code
        validation_result = QRCodeService.validate_qr_code(data_param)
        
        if not validation_result['valid']:
            return JsonResponse({
                'success': False,
                'message': validation_result.get('error', 'Invalid QR code')
            })
        
        facility = validation_result['facility']
        
        # Verify GPS location if provided
        if latitude and longitude:
            try:
                lat_float = float(latitude)
                lon_float = float(longitude)
                
                location_result = verify_teacher_location(lat_float, lon_float)
                
                if not location_result['valid']:
                    return JsonResponse({
                        'success': False,
                        'message': location_result.get('error', 'Location verification failed')
                    })
                    
                # Ensure GPS location matches facility from QR code
                if location_result['facility'].id != facility.id:
                    return JsonResponse({
                        'success': False,
                        'message': f'GPS location does not match QR code facility. You are at {location_result["facility"].name} but QR code is for {facility.name}'
                    })
                    
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid GPS coordinates'
                })
        else:
            # No GPS provided, use facility coordinates from QR code
            lat_float = float(facility.latitude) if facility.latitude else 0
            lon_float = float(facility.longitude) if facility.longitude else 0
        
        # Create attendance record
        try:
            attendance = TeacherAttendance.objects.create(
                teacher=request.user,
                facility=facility,
                clock_type=clock_type,
                latitude=lat_float,
                longitude=lon_float,
                location_verified=True,
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                notes=f'QR Code attendance for {facility.name}'
            )
            
            # Add selected classes if any
            if selected_classes:
                classes = Class.objects.filter(
                    id__in=selected_classes,
                    facility=facility,
                    is_active=True
                )
                attendance.classes.set(classes)
            
            # Invalidate the QR token to prevent reuse
            QRCodeService.invalidate_qr_token(validation_result['token'])
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully clocked {clock_type.replace("_", " ")} at {facility.name}',
                'attendance_id': attendance.id,
                'timestamp': attendance.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error recording attendance: {str(e)}'
            })


class QRCodeManagementView(LoginRequiredMixin, TemplateView):
    """
    QR Code Management View for administrators
    """
    template_name = 'core/qr_codes/management.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure only administrators can access this view
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            messages.error(request, 'Access denied. This page is for administrators only.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from facilities.models import Facility
        
        # Get all active facilities
        context['facilities'] = Facility.objects.filter(is_active=True).order_by('name')
        
        return context


class GenerateFacilityQRCodesView(LoginRequiredMixin, View):
    """
    Generate QR codes for a specific facility
    """
    template_name = 'core/qr_codes/facility_qr_codes.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure only administrators can access this view
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            messages.error(request, 'Access denied. This page is for administrators only.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, facility_id):
        """Display QR codes for facility"""
        from facilities.models import Facility
        from core.services import QRCodeService
        
        facility = get_object_or_404(Facility, id=facility_id, is_active=True)
        
        # Get days ahead parameter
        days_ahead = int(request.GET.get('days_ahead', 7))
        
        # Generate QR codes for facility
        qr_result = QRCodeService.generate_facility_qr_codes(facility, days_ahead=days_ahead)
        
        context = {
            'facility': facility,
            'qr_result': qr_result,
            'days_ahead': days_ahead
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, facility_id):
        """Handle AJAX request for generating QR codes"""
        from facilities.models import Facility
        from core.services import QRCodeService
        
        facility = get_object_or_404(Facility, id=facility_id, is_active=True)
        days_ahead = int(request.POST.get('days_ahead', 7))
        
        qr_result = QRCodeService.generate_facility_qr_codes(facility, days_ahead=days_ahead)
        
        if qr_result['success']:
            return JsonResponse({
                'success': True,
                'qr_codes': qr_result['qr_codes'],
                'total_generated': qr_result['total_generated']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': qr_result['error']
            })


# Timesheet Export Views

class TimesheetExportView(LoginRequiredMixin, TemplateView):
    """
    Timesheet Export Interface for administrators and teachers
    """
    template_name = 'core/timesheet/export.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from accounts.models import Staff
        from datetime import date, timedelta
        
        # Get all teachers for selection
        context['teachers'] = Staff.objects.filter(
            role='teacher', 
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # Set default date range (last month)
        today = date.today()
        context['default_end_date'] = today.strftime('%Y-%m-%d')
        context['default_start_date'] = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Current user context
        context['is_admin'] = hasattr(self.request.user, 'role') and self.request.user.role == 'admin'
        context['current_teacher'] = self.request.user if hasattr(self.request.user, 'role') and self.request.user.role == 'teacher' else None
        
        return context
    
    def post(self, request):
        """Handle timesheet export requests"""
        from core.services import TimesheetExportService
        from accounts.models import Staff
        from datetime import datetime
        
        # Get form data
        teacher_id = request.POST.get('teacher_id')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        export_format = request.POST.get('format', 'excel')
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            messages.error(request, 'Invalid date format')
            return redirect('core:timesheet_export')
        
        # Get teacher if specified
        teacher = None
        if teacher_id:
            try:
                teacher = Staff.objects.get(id=teacher_id, role='teacher')
                
                # Check permissions - teachers can only export their own data
                if (hasattr(request.user, 'role') and 
                    request.user.role == 'teacher' and 
                    request.user.id != teacher.id):
                    messages.error(request, 'You can only export your own timesheet')
                    return redirect('core:timesheet_export')
                    
            except Staff.DoesNotExist:
                messages.error(request, 'Teacher not found')
                return redirect('core:timesheet_export')
        else:
            # If no teacher specified and user is a teacher, use current user
            if hasattr(request.user, 'role') and request.user.role == 'teacher':
                teacher = request.user
        
        # Generate export
        try:
            if export_format == 'excel':
                return TimesheetExportService.export_teacher_timesheet(
                    teacher=teacher,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                messages.error(request, 'Unsupported export format')
                return redirect('core:timesheet_export')
                
        except Exception as e:
            logger.error(f"Timesheet export error: {str(e)}")
            messages.error(request, f'Export failed: {str(e)}')
            return redirect('core:timesheet_export')


class MonthlyTimesheetView(LoginRequiredMixin, View):
    """
    Monthly timesheet summary export
    """
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure only administrators can access monthly summary
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            messages.error(request, 'Access denied. This feature is for administrators only.')
            return redirect('core:timesheet_export')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, year, month):
        """Generate and download monthly summary"""
        from core.services import TimesheetExportService
        
        try:
            return TimesheetExportService.generate_monthly_summary(year, month)
        except Exception as e:
            logger.error(f"Monthly timesheet export error: {str(e)}")
            messages.error(request, f'Monthly export failed: {str(e)}')
            return redirect('core:timesheet_export')


# Organisation Settings Views

@login_required
def organisation_settings_view(request):
    """Organisation settings management view"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        messages.error(request, 'Only administrators can access organisation settings.')
        return redirect('core:dashboard')
    
    # Get or create organisation settings instance
    org_settings = OrganisationSettings.get_instance()
    
    if request.method == 'POST':
        # Handle form submission
        organisation_name = request.POST.get('organisation_name')
        abn_number = request.POST.get('abn_number')
        contact_email = request.POST.get('contact_email')
        contact_phone = request.POST.get('contact_phone')
        prices_include_gst = request.POST.get('prices_include_gst') == 'on'
        gst_rate = request.POST.get('gst_rate')
        show_gst_breakdown = request.POST.get('show_gst_breakdown') == 'on'
        gst_label = request.POST.get('gst_label')
        
        try:
            # Update organisation settings
            org_settings.organisation_name = organisation_name
            org_settings.abn_number = abn_number
            org_settings.contact_email = contact_email
            org_settings.contact_phone = contact_phone
            org_settings.prices_include_gst = prices_include_gst
            org_settings.gst_rate = Decimal(gst_rate)
            org_settings.show_gst_breakdown = show_gst_breakdown
            org_settings.gst_label = gst_label
            org_settings.updated_by = request.user
            org_settings.save()
            
            messages.success(request, 'Organisation settings updated successfully.')
            return redirect('core:organisation_settings')
            
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Invalid GST rate: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    context = {
        'org_settings': org_settings,
        'page_title': 'Organisation Settings'
    }
    
    return render(request, 'core/settings/organisation.html', context)


@require_http_methods(['POST'])
@login_required
def test_gst_calculation(request):
    """AJAX view to test GST calculation with current settings"""
    
    # Check if user is admin
    if not request.user.is_superuser and request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        test_price = Decimal(request.POST.get('test_price', '100.00'))
        prices_include_gst = request.POST.get('prices_include_gst') == 'true'
        gst_rate = Decimal(request.POST.get('gst_rate', '0.10'))
        
        # Calculate GST breakdown
        if prices_include_gst:
            # Price includes GST - extract GST amount
            price_inc_gst = test_price
            gst_amount = price_inc_gst / (1 + gst_rate) * gst_rate
            price_ex_gst = price_inc_gst - gst_amount
        else:
            # Price excludes GST - calculate GST amount
            price_ex_gst = test_price
            gst_amount = price_ex_gst * gst_rate
            price_inc_gst = price_ex_gst + gst_amount
        
        # Round to 2 decimal places
        price_ex_gst = price_ex_gst.quantize(Decimal('0.01'))
        gst_amount = gst_amount.quantize(Decimal('0.01'))
        price_inc_gst = price_inc_gst.quantize(Decimal('0.01'))
        
        return JsonResponse({
            'success': True,
            'breakdown': {
                'input_price': float(test_price),
                'price_ex_gst': float(price_ex_gst),
                'gst_amount': float(gst_amount),
                'price_inc_gst': float(price_inc_gst),
                'gst_rate_percentage': float(gst_rate * 100),
                'includes_gst': prices_include_gst
            }
        })
        
    except (ValueError, InvalidOperation) as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)