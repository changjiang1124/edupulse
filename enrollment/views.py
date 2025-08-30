from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone

from .models import Enrollment, Attendance
from .forms import EnrollmentForm


class EnrollmentListView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'core/enrollments/list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Enrollment.objects.select_related('student', 'course').all()
        
        # Filter by student if specified
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        # Filter by course if specified
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        return queryset.order_by('-created_at')


class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'core/enrollments/detail.html'
    context_object_name = 'enrollment'


class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'core/attendance/list.html'
    context_object_name = 'attendances'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Attendance.objects.select_related(
            'student', 'class_instance__course'
        ).all()
        
        # Filter by student if specified
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        return queryset.order_by('-attendance_time')


class AttendanceMarkView(LoginRequiredMixin, TemplateView):
    template_name = 'core/attendance/mark.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        if class_id:
            from academics.models import Class
            class_instance = get_object_or_404(Class, pk=class_id)
            context['class_instance'] = class_instance
            
            # Get enrolled students for this course
            enrolled_students = class_instance.course.enrollments.filter(
                status='confirmed'
            ).select_related('student')
            context['enrolled_students'] = enrolled_students
            
            # Get existing attendance records
            existing_attendance = {
                att.student.id: att for att in 
                class_instance.attendances.select_related('student').all()
            }
            context['existing_attendance'] = existing_attendance
            
        return context
