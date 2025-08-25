from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, date, timedelta

from .models import (
    Staff, Student, Course, Class, Facility, Classroom,
    Enrollment, Attendance, ClockInOut, EmailLog, SMSLog
)


class AdminRequiredMixin(UserPassesTestMixin):
    """管理员权限检查混入类"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'


class DashboardView(LoginRequiredMixin, TemplateView):
    """仪表盘视图"""
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 统计数据
        context.update({
            'total_students': Student.objects.filter(is_active=True).count(),
            'total_courses': Course.objects.filter(is_active=True).count(),
            'total_staff': Staff.objects.filter(is_active_staff=True).count(),
            'pending_enrollments': Enrollment.objects.filter(status='pending').count(),
            
            # 近期班级
            'upcoming_classes': Class.objects.filter(
                date__gte=timezone.now().date(),
                is_active=True
            ).order_by('date', 'start_time')[:5],
            
            # 最新报名
            'recent_enrollments': Enrollment.objects.select_related(
                'student', 'course'
            ).order_by('-created_at')[:5],
        })
        
        return context


# Staff Management Views
class StaffListView(AdminRequiredMixin, ListView):
    model = Staff
    template_name = 'core/staff/list.html'
    context_object_name = 'staff_list'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Staff.objects.filter(is_active_staff=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset.order_by('last_name', 'first_name')


class StaffCreateView(AdminRequiredMixin, CreateView):
    model = Staff
    template_name = 'core/staff/form.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role']
    success_url = reverse_lazy('core:staff_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'员工 {form.instance.first_name} {form.instance.last_name} 创建成功！')
        return super().form_valid(form)


class StaffDetailView(AdminRequiredMixin, DetailView):
    model = Staff
    template_name = 'core/staff/detail.html'
    context_object_name = 'staff'


class StaffUpdateView(AdminRequiredMixin, UpdateView):
    model = Staff
    template_name = 'core/staff/form.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'role', 'is_active_staff']
    
    def get_success_url(self):
        return reverse_lazy('core:staff_detail', kwargs={'pk': self.object.pk})


# Student Management Views
class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'core/students/list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Student.objects.filter(is_active=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(guardian_name__icontains=search)
            )
        return queryset.order_by('last_name', 'first_name')


class StudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    template_name = 'core/students/form.html'
    fields = [
        'first_name', 'last_name', 'birth_date', 'email', 'phone', 'address',
        'guardian_name', 'guardian_phone', 'guardian_email', 'reference'
    ]
    success_url = reverse_lazy('core:student_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'学生 {form.instance.first_name} {form.instance.last_name} 添加成功！')
        return super().form_valid(form)


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'core/students/detail.html'
    context_object_name = 'student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enrollments'] = self.object.enrollments.select_related('course').all()
        context['attendances'] = self.object.attendances.select_related(
            'class_instance__course'
        ).order_by('-attendance_time')[:10]
        return context


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    template_name = 'core/students/form.html'
    fields = [
        'first_name', 'last_name', 'birth_date', 'email', 'phone', 'address',
        'guardian_name', 'guardian_phone', 'guardian_email', 'reference', 'is_active'
    ]
    
    def get_success_url(self):
        return reverse_lazy('core:student_detail', kwargs={'pk': self.object.pk})


# Course Management Views
class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'core/courses/list.html'
    context_object_name = 'courses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_active=True).select_related('teacher', 'facility')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset.order_by('-start_date')


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    template_name = 'core/courses/form.html'
    fields = [
        'name', 'short_description', 'description', 'price', 'course_type', 'status', 'teacher',
        'start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes',
        'vacancy', 'facility', 'classroom'
    ]
    success_url = reverse_lazy('core:course_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Course "{form.instance.name}" created successfully!')
        response = super().form_valid(form)
        
        # Auto-generate classes if requested
        if self.request.POST.get('generate_classes'):
            classes_created = self.object.generate_classes()
            messages.success(self.request, f'{classes_created} classes generated for this course.')
        
        return response


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'core/courses/detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = self.object.classes.filter(is_active=True).order_by('date', 'start_time')
        context['enrollments'] = self.object.enrollments.select_related('student').all()
        return context


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    template_name = 'core/courses/form.html'
    fields = [
        'name', 'short_description', 'description', 'price', 'course_type', 'status', 'teacher',
        'start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes',
        'vacancy', 'facility', 'classroom', 'is_bookable', 'is_active'
    ]
    
    def get_success_url(self):
        return reverse_lazy('core:course_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Course "{form.instance.name}" updated successfully!')
        response = super().form_valid(form)
        
        # Regenerate classes if requested
        if self.request.POST.get('regenerate_classes'):
            classes_created = self.object.generate_classes()
            messages.success(self.request, f'{classes_created} classes regenerated for this course.')
        
        return response


# Class Management Views
class ClassListView(LoginRequiredMixin, ListView):
    model = Class
    template_name = 'core/classes/list.html'
    context_object_name = 'classes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Class.objects.select_related(
            'course', 'teacher', 'facility', 'classroom'
        ).filter(is_active=True)
        
        # 日期过滤
        date_filter = self.request.GET.get('date')
        if date_filter == 'today':
            queryset = queryset.filter(date=timezone.now().date())
        elif date_filter == 'week':
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            queryset = queryset.filter(date__range=[week_start, week_end])
        
        return queryset.order_by('date', 'start_time')


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    template_name = 'core/classes/form.html'
    fields = [
        'course', 'date', 'start_time', 'duration_minutes',
        'teacher', 'facility', 'classroom'
    ]
    success_url = reverse_lazy('core:class_list')


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'core/classes/detail.html'
    context_object_name = 'class_instance'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attendances'] = self.object.attendances.select_related('student').all()
        return context


# Facility Management Views
class FacilityListView(AdminRequiredMixin, ListView):
    model = Facility
    template_name = 'core/facilities/list.html'
    context_object_name = 'facilities'


class FacilityCreateView(AdminRequiredMixin, CreateView):
    model = Facility
    template_name = 'core/facilities/form.html'
    fields = ['name', 'address', 'phone', 'email']
    success_url = reverse_lazy('core:facility_list')


class FacilityDetailView(AdminRequiredMixin, DetailView):
    model = Facility
    template_name = 'core/facilities/detail.html'
    context_object_name = 'facility'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classrooms'] = self.object.classrooms.filter(is_active=True)
        return context


# Enrollment Management Views
class EnrollmentListView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'core/enrollments/list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Enrollment.objects.select_related('student', 'course')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-created_at')


class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'core/enrollments/detail.html'
    context_object_name = 'enrollment'


# Attendance Management Views
class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'core/attendance/list.html'
    context_object_name = 'attendances'
    paginate_by = 50


class AttendanceMarkView(LoginRequiredMixin, TemplateView):
    template_name = 'core/attendance/mark.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today_classes = Class.objects.filter(
            date=timezone.now().date(),
            is_active=True
        ).select_related('course').order_by('start_time')
        context['today_classes'] = today_classes
        return context


# Clock In/Out Views
class ClockInOutView(LoginRequiredMixin, TemplateView):
    template_name = 'core/clock/clock.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 获取今日最后一次打卡记录
        today = timezone.now().date()
        last_record = ClockInOut.objects.filter(
            staff=self.request.user,
            timestamp__date=today
        ).order_by('-timestamp').first()
        
        context['last_record'] = last_record
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        ClockInOut.objects.create(
            staff=request.user,
            status='clock_in' if action == 'in' else 'clock_out',
            latitude=latitude,
            longitude=longitude
        )
        
        action_text = '上班' if action == 'in' else '下班'
        messages.success(request, f'{action_text}打卡成功！')
        return redirect('core:clock_inout')


class TimesheetView(LoginRequiredMixin, TemplateView):
    template_name = 'core/clock/timesheet.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取本月打卡记录
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        if self.request.user.role == 'admin':
            records = ClockInOut.objects.filter(
                timestamp__date__gte=month_start
            ).select_related('staff').order_by('-timestamp')
        else:
            records = ClockInOut.objects.filter(
                staff=self.request.user,
                timestamp__date__gte=month_start
            ).order_by('-timestamp')
        
        context['records'] = records
        return context
