from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse

from .models import Enrollment, Attendance
from .forms import EnrollmentForm, PublicEnrollmentForm
from students.models import Student
from academics.models import Course


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
            
        # Filter by status if specified
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter options
        context['students'] = Student.objects.all().order_by('first_name', 'last_name')
        context['courses'] = Course.objects.filter(status='published').order_by('name')
        return context


class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'core/enrollments/detail.html'
    context_object_name = 'enrollment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get other enrollments for this student
        context['other_enrollments'] = Enrollment.objects.filter(
            student=self.object.student
        ).exclude(
            pk=self.object.pk
        ).select_related('course')[:5]
        
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'confirm' and self.object.status == 'pending':
            self.object.status = 'confirmed'
            self.object.save()
            messages.success(
                request, 
                f'Enrollment for {self.object.student.get_full_name()} has been confirmed.'
            )
        
        return redirect('enrollment:enrollment_detail', pk=self.object.pk)


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


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    """Create enrollment (staff use)"""
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'core/enrollments/create.html'
    success_url = reverse_lazy('enrollment:enrollment_list')
    
    def form_valid(self, form):
        form.instance.source_channel = 'staff'
        messages.success(self.request, 'Enrollment created successfully.')
        return super().form_valid(form)


class EnrollmentUpdateView(LoginRequiredMixin, UpdateView):
    """Update enrollment (staff use)"""
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'core/enrollments/update.html'
    success_url = reverse_lazy('enrollment:enrollment_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Enrollment updated successfully.')
        return super().form_valid(form)


class EnrollmentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete enrollment (staff use)"""
    model = Enrollment
    template_name = 'core/enrollments/delete.html'
    success_url = reverse_lazy('enrollment:enrollment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Enrollment deleted successfully.')
        return super().delete(request, *args, **kwargs)


class PublicEnrollmentView(TemplateView):
    """Public enrollment page (no login required)"""
    template_name = 'core/enrollments/public_enrollment.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only show published courses that allow online bookings
        context['courses'] = Course.objects.filter(
            status='published', 
            is_online_bookable=True
        ).order_by('name')
        context['form'] = PublicEnrollmentForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = PublicEnrollmentForm(request.POST)
        courses = Course.objects.filter(status='published', is_online_bookable=True).order_by('name')
        
        if form.is_valid():
            # Create or get student
            student_data = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'email': form.cleaned_data['email'],
                'phone': form.cleaned_data['phone'],
                'date_of_birth': form.cleaned_data['date_of_birth'],
                'guardian_name': form.cleaned_data.get('guardian_name', ''),
                'guardian_email': form.cleaned_data.get('guardian_email', ''),
                'guardian_phone': form.cleaned_data.get('guardian_phone', ''),
                'emergency_contact_name': form.cleaned_data.get('emergency_contact_name', ''),
                'emergency_contact_phone': form.cleaned_data.get('emergency_contact_phone', ''),
                'medical_conditions': form.cleaned_data.get('medical_conditions', ''),
                'special_requirements': form.cleaned_data.get('special_requirements', ''),
                'address': form.cleaned_data.get('address', ''),
            }
            
            # Check if student exists by email
            student = None
            if form.cleaned_data['email']:
                try:
                    student = Student.objects.get(email=form.cleaned_data['email'])
                    # Update existing student data
                    for key, value in student_data.items():
                        if value:  # Only update non-empty fields
                            setattr(student, key, value)
                    student.save()
                except Student.DoesNotExist:
                    pass
            
            # Create student if not found
            if not student:
                student = Student.objects.create(**student_data)
            
            # Create enrollment
            course = Course.objects.get(pk=form.cleaned_data['course_id'])
            enrollment_data = {
                'student': student,
                'course': course,
                'status': 'pending',
                'source_channel': 'form',
                'form_data': form.cleaned_data
            }
            
            # Check if enrollment already exists
            existing_enrollment = Enrollment.objects.filter(
                student=student, course=course
            ).first()
            
            if existing_enrollment:
                messages.warning(
                    request, 
                    f'Enrollment already exists for {student.get_full_name()} in {course.name}. Status: {existing_enrollment.get_status_display()}'
                )
                return redirect('public_enrollment_success', enrollment_id=existing_enrollment.pk)
            else:
                enrollment = Enrollment.objects.create(**enrollment_data)
                messages.success(
                    request, 
                    f'Enrollment submitted successfully for {student.get_full_name()} in {course.name}. Reference ID: {enrollment.pk}'
                )
                return redirect('public_enrollment_success', enrollment_id=enrollment.pk)
        
        return render(request, self.template_name, {
            'form': form,
            'courses': courses
        })


class EnrollmentSuccessView(TemplateView):
    """Enrollment success page"""
    template_name = 'core/enrollments/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment_id = self.kwargs.get('enrollment_id')
        if enrollment_id:
            context['enrollment'] = get_object_or_404(Enrollment, pk=enrollment_id)
        return context


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
