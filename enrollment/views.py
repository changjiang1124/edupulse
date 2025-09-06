from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView, View
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
        from core.services import NotificationService
        
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'confirm' and self.object.status == 'pending':
            self.object.status = 'confirmed'
            self.object.save()
            
            # Create student activity record for enrollment confirmation
            from students.models import StudentActivity
            StudentActivity.create_activity(
                student=self.object.student,
                activity_type='enrollment_confirmed',
                title=f'Enrollment confirmed for {self.object.course.name}',
                description=f'Enrollment status changed from pending to confirmed by staff member.',
                enrollment=self.object,
                course=self.object.course,
                performed_by=request.user if hasattr(request.user, 'staff') else None,
                metadata={
                    'previous_status': 'pending',
                    'new_status': 'confirmed',
                    'confirmed_at': timezone.now().isoformat()
                }
            )
            
            # Send welcome email upon confirmation
            try:
                welcome_sent = NotificationService.send_welcome_email(self.object)
                if welcome_sent:
                    # Record welcome email activity
                    StudentActivity.create_activity(
                        student=self.object.student,
                        activity_type='email_sent',
                        title='Welcome email sent',
                        description=f'Welcome email sent to {self.object.student.get_contact_email()} after enrollment confirmation',
                        enrollment=self.object,
                        course=self.object.course,
                        performed_by=request.user if hasattr(request.user, 'staff') else None,
                        metadata={
                            'email_type': 'welcome',
                            'recipient': self.object.student.get_contact_email(),
                            'triggered_by': 'enrollment_confirmation'
                        }
                    )
                    messages.success(
                        request, 
                        f'Enrollment for {self.object.student.get_full_name()} has been confirmed and welcome email sent.'
                    )
                else:
                    messages.success(
                        request, 
                        f'Enrollment for {self.object.student.get_full_name()} has been confirmed, but welcome email could not be sent.'
                    )
            except Exception as e:
                messages.success(
                    request, 
                    f'Enrollment for {self.object.student.get_full_name()} has been confirmed, but notification error: {str(e)}'
                )
        
        return redirect('enrollment:enrollment_detail', pk=self.object.pk)


class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'core/attendance/list.html'
    context_object_name = 'attendance_records'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Attendance.objects.select_related(
            'student', 'class_instance__course'
        ).all()
        
        # Filter by course if specified
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(class_instance__course_id=course_id)
        
        # Filter by date range if specified
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(class_instance__date__gte=date_from)
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(class_instance__date__lte=date_to)
            
        # Filter by student if specified
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        return queryset.order_by('-class_instance__date', '-attendance_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        from academics.models import Course, Class
        context['courses'] = Course.objects.filter(status='published').order_by('name')
        
        # Get upcoming classes for attendance marking
        from django.utils import timezone
        today = timezone.now().date()
        next_week = today + timezone.timedelta(days=7)
        
        context['upcoming_classes'] = Class.objects.filter(
            date__gte=today,
            date__lte=next_week,
            is_active=True
        ).select_related('course').order_by('date', 'start_time')[:12]
        
        return context


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
            from students.services import StudentMatchingService, EnrollmentFeeCalculator
            from core.services import NotificationService
            
            # Get course
            course = Course.objects.get(pk=form.cleaned_data['course_id'])
            
            # Create enrollment first for reference
            enrollment = Enrollment.objects.create(
                course=course,
                status='pending',
                source_channel='website',
                original_form_data=form.cleaned_data
            )
            
            # Use student matching service to create or find student
            student, was_created = StudentMatchingService.create_or_update_student(
                form.cleaned_data, enrollment
            )
            
            # Calculate and set enrollment fees
            fees = EnrollmentFeeCalculator.update_enrollment_fees(
                enrollment, course, enrollment.is_new_student
            )
            
            # Check if enrollment already exists for this course
            existing_enrollment = Enrollment.objects.filter(
                student=student, 
                course=course
            ).exclude(pk=enrollment.pk).first()
            
            if existing_enrollment:
                # Delete the temp enrollment we just created
                enrollment.delete()
                
                messages.warning(
                    request, 
                    f'Enrollment already exists for {student.get_full_name()} in {course.name}. Status: {existing_enrollment.get_status_display()}'
                )
                return redirect('enrollment:enrollment_success', enrollment_id=existing_enrollment.pk)
            else:
                # Create student activity record for enrollment creation
                from students.models import StudentActivity
                StudentActivity.create_activity(
                    student=student,
                    activity_type='enrollment_created',
                    title=f'Enrolled in {course.name}',
                    description=f'Student enrolled in course "{course.name}" via website form. Status: pending.',
                    enrollment=enrollment,
                    course=course,
                    metadata={
                        'source_channel': 'website',
                        'form_data_stored': True,
                        'fees_calculated': True,
                        'is_new_student': was_created,
                        'total_fee': str(fees.get('total_fee', 0))
                    }
                )
                
                # Process enrollment notifications
                try:
                    notification_results = NotificationService.process_enrollment_notifications(enrollment)
                    if notification_results['confirmation_sent']:
                        messages.success(request, 'Enrollment confirmation email sent.')
                        # Record email sent activity
                        StudentActivity.create_activity(
                            student=student,
                            activity_type='email_sent',
                            title='Enrollment confirmation email sent',
                            description=f'Confirmation email sent to {student.get_contact_email()}',
                            enrollment=enrollment,
                            course=course,
                            metadata={
                                'email_type': 'enrollment_confirmation',
                                'recipient': student.get_contact_email()
                            }
                        )
                    else:
                        messages.warning(request, 'Enrollment created but confirmation email could not be sent.')
                except Exception as e:
                    messages.warning(request, f'Enrollment created but notification error: {str(e)}')
                
                success_message = f'Enrollment submitted successfully for {student.get_full_name()} in {course.name}.'
                if was_created:
                    success_message += ' New student profile created.'
                else:
                    success_message += ' Existing student record updated.'
                
                if fees['has_registration_fee']:
                    success_message += f' Total fee: ${fees["total_fee"]} (includes ${fees["registration_fee"]} registration fee).'
                else:
                    success_message += f' Course fee: ${fees["course_fee"]}.'
                
                messages.success(request, success_message)
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


class AttendanceMarkView(LoginRequiredMixin, View):
    """Enhanced attendance marking view with batch processing"""
    template_name = 'core/attendance/mark.html'
    
    def get_context_data(self, class_instance, form=None):
        """Prepare context for both GET and POST requests"""
        context = {
            'class_instance': class_instance,
            'course': class_instance.course,
        }
        
        # Get enrolled students for this course
        enrolled_students = class_instance.course.enrollments.filter(
            status='confirmed'
        ).select_related('student')
        context['enrolled_students'] = enrolled_students
        
        # Get existing attendance records
        existing_attendance = class_instance.attendances.select_related('student').all()
        context['existing_attendance'] = existing_attendance
        
        # Also provide as dict for quick lookup
        existing_attendance_dict = {
            att.student.id: att for att in existing_attendance
        }
        context['existing_attendance_dict'] = existing_attendance_dict
        
        # Add form to context
        if form is None:
            from .forms import BulkAttendanceForm
            form = BulkAttendanceForm(class_instance=class_instance)
        context['form'] = form
        
        # Add student field data for easier template rendering
        context['student_fields'] = form.get_student_fields() if hasattr(form, 'get_student_fields') else []
        
        return context
    
    def get(self, request, class_id):
        """Display attendance marking form"""
        from academics.models import Class
        class_instance = get_object_or_404(Class, pk=class_id)
        
        context = self.get_context_data(class_instance)
        return render(request, self.template_name, context)
    
    def post(self, request, class_id):
        """Process bulk attendance form submission"""
        from academics.models import Class
        from .forms import BulkAttendanceForm
        
        class_instance = get_object_or_404(Class, pk=class_id)
        form = BulkAttendanceForm(request.POST, class_instance=class_instance)
        
        if form.is_valid():
            try:
                created_count, updated_count = form.save_attendance(class_instance)
                
                success_msg = f'Attendance updated successfully! '
                if created_count:
                    success_msg += f'{created_count} new records created. '
                if updated_count:
                    success_msg += f'{updated_count} existing records updated.'
                
                messages.success(request, success_msg)
                return redirect('enrollment:attendance_mark', class_id=class_id)
                
            except Exception as e:
                messages.error(request, f'Error saving attendance: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
        
        context = self.get_context_data(class_instance, form)
        return render(request, self.template_name, context)


class StudentSearchView(LoginRequiredMixin, View):
    """AJAX student search endpoint"""
    
    def get(self, request):
        """Handle AJAX student search requests"""
        from django.http import JsonResponse
        from .forms import StudentSearchForm
        
        form = StudentSearchForm(request.GET)
        
        if form.is_valid():
            results = form.search_students()
            return JsonResponse({
                'success': True,
                'results': results,
                'count': len(results)
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)


class AttendanceUpdateView(LoginRequiredMixin, UpdateView):
    """Update individual attendance record"""
    model = Attendance
    template_name = 'core/attendance/update.html'
    fields = ['status', 'attendance_time']
    
    def get_success_url(self):
        return reverse('enrollment:attendance_mark', 
                      kwargs={'class_id': self.object.class_instance.id})
    
    def form_valid(self, form):
        messages.success(self.request, 
                        f'Attendance updated for {self.object.student.get_full_name()}')
        return super().form_valid(form)
