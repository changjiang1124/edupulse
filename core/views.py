from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, date, timedelta
import os
import uuid
from django.conf import settings

from accounts.models import Staff
from students.models import Student
from academics.models import Course, Class
from facilities.models import Facility, Classroom
from enrollment.models import Enrollment, Attendance
from .models import ClockInOut, EmailLog, SMSLog


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view"""
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context.update({
            'total_students': Student.objects.filter(is_active=True).count(),
            'total_courses': Course.objects.filter(is_active=True).count(),
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