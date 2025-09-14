from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from .models import Student, StudentTag
from .forms import StudentForm, BulkNotificationForm
from core.models import EmailSettings, SMSSettings, EmailLog, SMSLog, NotificationQuota


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'core/students/list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Student.objects.filter(is_active=True).prefetch_related('tags')
        search = self.request.GET.get('search')
        tag_filter = self.request.GET.get('tag')
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(contact_email__icontains=search) |
                Q(guardian_name__icontains=search)
            )
        
        if tag_filter:
            queryset = queryset.filter(tags__id=tag_filter)
        
        return queryset.order_by('last_name', 'first_name').distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_tags'] = StudentTag.objects.filter(is_active=True)
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
def bulk_notification(request):
    """Handle bulk notification sending to students"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
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
    student_ids = cleaned_data.get('student_ids', [])
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
    
    # Send notifications
    email_sent = 0
    sms_sent = 0
    email_failed = 0
    sms_failed = 0
    
    for student in recipients:
        # Send email
        if notification_type in ['email', 'both']:
            contact_email = student.get_contact_email()
            if contact_email:
                try:
                    _send_email_notification(student, contact_email, subject, message, message_type)
                    email_sent += 1
                except Exception as e:
                    email_failed += 1
                    EmailLog.objects.create(
                        recipient_email=contact_email,
                        recipient_type='student',
                        subject=subject,
                        content=message,
                        email_type=message_type,
                        status='failed',
                        error_message=str(e)
                    )
        
        # Send SMS
        if notification_type in ['sms', 'both']:
            contact_phone = student.get_contact_phone()
            if contact_phone:
                try:
                    _send_sms_notification(student, contact_phone, message, message_type)
                    sms_sent += 1
                except Exception as e:
                    sms_failed += 1
                    SMSLog.objects.create(
                        recipient_phone=contact_phone,
                        recipient_type='student',
                        content=message,
                        sms_type=message_type,
                        status='failed',
                        error_message=str(e)
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
    from django.core.mail import EmailMessage
    from core.backends import get_email_backend
    
    # Get active email configuration
    email_config = EmailSettings.get_active_config()
    if not email_config:
        raise Exception('No active email configuration found')
    
    # Create email backend
    backend = get_email_backend()
    if not backend:
        raise Exception('Email backend not available')
    
    # Create and send email
    email_message = EmailMessage(
        subject=subject,
        body=message,
        from_email=f'{email_config.from_name} <{email_config.from_email}>',
        to=[email],
        reply_to=[email_config.reply_to_email or email_config.from_email],
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
        email_backend=email_config.get_email_backend_type_display(),
        sent_at=timezone.now()
    )


def _send_sms_notification(student, phone, message, message_type):
    """Send SMS notification to student"""
    from core.sms_backends import get_sms_backend
    
    # Get active SMS configuration
    sms_config = SMSSettings.get_active_config()
    if not sms_config:
        raise Exception('No active SMS configuration found')
    
    # Get SMS backend
    backend = get_sms_backend()
    if not backend:
        raise Exception('SMS backend not available')
    
    # Send SMS
    message_sid = backend.send_sms(phone, message)
    
    # Log successful SMS
    SMSLog.objects.create(
        recipient_phone=phone,
        recipient_type='student',
        content=message,
        sms_type=message_type,
        status='sent',
        message_sid=message_sid or '',
        backend_type=sms_config.get_sms_backend_type_display(),
        sent_at=timezone.now()
    )


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
