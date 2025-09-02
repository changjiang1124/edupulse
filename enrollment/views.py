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
        
        # Get course_id from URL if present
        course_id = self.kwargs.get('course_id')
        selected_course = None
        
        # Only show published courses that allow online bookings
        courses = Course.objects.filter(
            status='published', 
            is_online_bookable=True
        ).order_by('name')
        context['courses'] = courses
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = courses.get(pk=course_id)
                context['selected_course'] = selected_course
            except Course.DoesNotExist:
                # If course doesn't exist or isn't bookable, redirect to main enrollment
                from django.shortcuts import redirect
                return redirect('enrollment:public_enrollment')
        
        # Initialize form with selected course if available
        initial_data = {}
        if selected_course:
            initial_data['course_id'] = selected_course.pk
            
        context['form'] = PublicEnrollmentForm(initial=initial_data)
        return context
    
    def post(self, request, *args, **kwargs):
        form = PublicEnrollmentForm(request.POST)
        
        # Get course_id from URL if present
        course_id = self.kwargs.get('course_id')
        selected_course = None
        
        courses = Course.objects.filter(status='published', is_online_bookable=True).order_by('name')
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = courses.get(pk=course_id)
            except Course.DoesNotExist:
                from django.shortcuts import redirect
                return redirect('enrollment:public_enrollment')
        
        if form.is_valid():
            # Calculate age to determine contact information mapping
            date_of_birth = form.cleaned_data['date_of_birth']
            age = form.get_student_age() or form.cleaned_data.get('calculated_age')
            
            # Determine contact information mapping based on age
            if age and age < 18:
                # Student is under 18 - contact info is guardian's
                guardian_email = form.cleaned_data['email']
                guardian_phone = form.cleaned_data['phone']
                student_email = ''  # No separate student email for under 18
                student_phone = ''  # No separate student phone for under 18
            else:
                # Student is 18+ - contact info is student's
                guardian_email = ''  # No guardian email for 18+
                guardian_phone = ''  # No guardian phone for 18+
                student_email = form.cleaned_data['email']
                student_phone = form.cleaned_data['phone']
            
            # Create student data with proper contact mapping
            student_data = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'birth_date': form.cleaned_data['date_of_birth'],
                'address': form.cleaned_data.get('address', ''),
                
                # Contact information (mapped based on age)
                'email': student_email,
                'phone': student_phone,
                
                # Guardian information (only for under 18)
                'guardian_name': form.cleaned_data.get('guardian_name', ''),
                'guardian_email': guardian_email,
                'guardian_phone': guardian_phone,
                
                # Emergency contact
                'emergency_contact_name': form.cleaned_data.get('emergency_contact_name', ''),
                'emergency_contact_phone': form.cleaned_data.get('emergency_contact_phone', ''),
                
                # Medical information
                'medical_conditions': form.cleaned_data.get('medical_conditions', ''),
                'special_requirements': form.cleaned_data.get('special_requirements', ''),
            }
            
            # Determine primary contact email for student lookup and notifications
            primary_contact_email = guardian_email if age and age < 18 else student_email
            
            # Check if student exists by primary contact email
            student = None
            if primary_contact_email:
                try:
                    # For under 18: look up by guardian email
                    # For 18+: look up by student email
                    if age and age < 18:
                        student = Student.objects.get(guardian_email=primary_contact_email)
                    else:
                        student = Student.objects.get(email=primary_contact_email)
                    
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
            
            # Store contact information metadata for notifications
            contact_info = {
                'primary_email': primary_contact_email,
                'primary_phone': guardian_phone if age and age < 18 else student_phone,
                'contact_type': 'guardian' if age and age < 18 else 'student',
                'student_age': age
            }
            
            # Create enrollment with enhanced form data including contact info
            course = Course.objects.get(pk=form.cleaned_data['course_id'])
            
            # Enhanced form data with contact metadata
            enhanced_form_data = dict(form.cleaned_data)
            enhanced_form_data.update(contact_info)
            
            enrollment_data = {
                'student': student,
                'course': course,
                'status': 'pending',
                'source_channel': 'form',
                'form_data': enhanced_form_data
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
                return redirect('enrollment:enrollment_success', enrollment_id=existing_enrollment.pk)
            else:
                enrollment = Enrollment.objects.create(**enrollment_data)
                messages.success(
                    request, 
                    f'Enrollment submitted successfully for {student.get_full_name()} in {course.name}. Reference ID: {enrollment.pk}'
                )
                return redirect('enrollment:enrollment_success', enrollment_id=enrollment.pk)
        
        # Form validation failed - prepare context for re-rendering
        context = {
            'form': form,
            'courses': courses
        }
        
        # Add selected course context if applicable
        if selected_course:
            context['selected_course'] = selected_course
            
        return render(request, self.template_name, context)


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
