from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, datetime

from .models import Course, Class
from .forms import CourseForm, CourseUpdateForm, ClassForm, ClassUpdateForm


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'core/courses/list.html'
    context_object_name = 'courses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Course.objects.all()
        
        # Filter by status
        status_filter = self.request.GET.get('status', 'all')
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', 'all')
        context['status_choices'] = Course.STATUS_CHOICES
        return context


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'core/courses/form.html'
    success_url = reverse_lazy('academics:course_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Auto-generate classes based on course schedule
        classes_created = self.object.generate_classes()
        messages.success(
            self.request, 
            f'Course "{self.object.name}" created successfully! {classes_created} class(es) generated.'
        )
        return response


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'core/courses/detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Update computed status fields before displaying
        self.object.update_computed_fields()
        
        # Use the correct related_name 'classes'
        context['classes'] = self.object.classes.filter(is_active=True).order_by('date', 'start_time')
        # Add enrollment information with try/except to avoid errors
        try:
            from enrollment.models import Enrollment
            context['enrollments'] = Enrollment.objects.filter(
                course=self.object
            ).select_related('student').all()
        except ImportError:
            context['enrollments'] = []
        return context


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseUpdateForm
    template_name = 'core/courses/form.html'
    
    def form_valid(self, form):
        # Save course changes
        response = super().form_valid(form)
        # Handle class update logic
        update_existing = form.cleaned_data.get('update_existing_classes', False)
        if update_existing:
            self.object.update_related_classes()
        return response

    def get_success_url(self):
        return reverse('academics:course_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit_mode'] = True
        context['existing_classes'] = self.object.classes.order_by('date', 'start_time')
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Handle class updates if requested
        update_existing = form.cleaned_data.get('update_existing_classes', False)
        selected_classes = form.cleaned_data.get('selected_classes', [])
        
        if update_existing and selected_classes:
            # Get the selected classes to update
            classes_to_update = self.object.classes.filter(
                is_active=True,
                id__in=[int(class_id) for class_id in selected_classes]
            )
            
            updated_count = 0
            
            # Apply all course changes to selected classes
            for class_instance in classes_to_update:
                updated = False
                
                # Update all relevant fields from course
                update_fields = ['teacher', 'start_time', 'duration_minutes', 'facility', 'classroom']
                for field in update_fields:
                    new_value = getattr(self.object, field)
                    current_value = getattr(class_instance, field)
                    if current_value != new_value:
                        setattr(class_instance, field, new_value)
                        updated = True
                
                if updated:
                    class_instance.save()
                    updated_count += 1
            
            # Provide success message
            if updated_count > 0:
                messages.success(
                    self.request,
                    f'Course updated successfully! Course changes applied to {updated_count} selected class(es).'
                )
            else:
                messages.success(self.request, f'Course updated successfully! No classes needed updates.')
        else:
            messages.success(self.request, f'Course updated successfully!')
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('academics:course_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add information about existing classes
        if self.object and self.object.pk:
            context['existing_classes'] = self.object.classes.filter(
                is_active=True,
                date__gte=timezone.now().date()
            ).count()
            context['past_classes'] = self.object.classes.filter(
                is_active=True,
                date__lt=timezone.now().date()
            ).count()
        
        return context


class ClassListView(LoginRequiredMixin, ListView):
    model = Class
    template_name = 'core/classes/list.html'
    context_object_name = 'classes'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Class.objects.select_related(
            'course', 'teacher', 'facility', 'classroom'
        )
        
        # Filter by user role - teachers can only see their classes
        if hasattr(self.request.user, 'role') and self.request.user.role == 'teacher':
            queryset = queryset.filter(course__teacher=self.request.user)
        
        # Filter by active status
        status_filter = self.request.GET.get('status', 'active')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'all':
            pass  # Show all statuses
        
        # Date range filters (simplified - no presets)
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
        else:
            # Default: show upcoming classes if no date filter is applied
            queryset = queryset.filter(date__gte=timezone.now().date())
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass
        
        # Filter by course
        course_id = self.request.GET.get('course')
        if course_id:
            try:
                course_id = int(course_id)
                queryset = queryset.filter(course_id=course_id)
            except (ValueError, TypeError):
                pass
        
        # Filter by teacher
        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            try:
                teacher_id = int(teacher_id)
                queryset = queryset.filter(teacher_id=teacher_id)
            except (ValueError, TypeError):
                pass
        
        # Filter by facility
        facility_id = self.request.GET.get('facility')
        if facility_id:
            try:
                facility_id = int(facility_id)
                queryset = queryset.filter(facility_id=facility_id)
            except (ValueError, TypeError):
                pass
        
        # Filter by classroom
        classroom_id = self.request.GET.get('classroom')
        if classroom_id:
            try:
                classroom_id = int(classroom_id)
                queryset = queryset.filter(classroom_id=classroom_id)
            except (ValueError, TypeError):
                pass
            
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(course__name__icontains=search) |
                Q(teacher__first_name__icontains=search) |
                Q(teacher__last_name__icontains=search) |
                Q(facility__name__icontains=search) |
                Q(classroom__name__icontains=search)
            )
        
        return queryset.order_by('date', 'start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'active')
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_course'] = self.request.GET.get('course', '')
        context['selected_teacher'] = self.request.GET.get('teacher', '')
        context['selected_facility'] = self.request.GET.get('facility', '')
        context['selected_classroom'] = self.request.GET.get('classroom', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['today'] = timezone.now().date()
        
        # Add user role context for template logic
        context['is_teacher'] = hasattr(self.request.user, 'role') and self.request.user.role == 'teacher'
        
        # Get filter options for dropdowns (only if user is admin)
        if not context['is_teacher']:
            context['courses'] = Course.objects.filter(status='published').order_by('name')
            from accounts.models import Staff
            context['teachers'] = Staff.objects.filter(role='teacher', is_active=True).order_by('first_name', 'last_name')
            from facilities.models import Facility, Classroom
            context['facilities'] = Facility.objects.filter(is_active=True).order_by('name')
            context['classrooms'] = Classroom.objects.filter(is_active=True).order_by('name')
        
        return context


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    form_class = ClassForm
    template_name = 'core/classes/form.html'
    success_url = reverse_lazy('academics:class_list')

    def get_initial(self):
        initial = super().get_initial()
        course_id = self.request.GET.get('course')
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                initial['course'] = course.pk
                # Pre-fill facility and classroom from course defaults
                if course.facility:
                    initial['facility'] = course.facility.pk
                if course.classroom:
                    initial['classroom'] = course.classroom.pk
                # Pre-fill other fields from course defaults
                if course.teacher:
                    initial['teacher'] = course.teacher.pk
                initial['start_time'] = course.start_time
                initial['duration_minutes'] = course.duration_minutes
            except Course.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Provide selected_course to template to disable dropdown and render hidden input
        course_id = self.request.GET.get('course')
        selected_course = None
        if course_id:
            selected_course = Course.objects.filter(pk=course_id).first()
        context['selected_course'] = selected_course
        return context

    def form_valid(self, form):
        from django.contrib import messages
        
        # Ensure course is set from GET when dropdown is disabled
        if not form.cleaned_data.get('course'):
            course_id = self.request.GET.get('course')
            if course_id:
                form.instance.course = Course.objects.filter(pk=course_id).first()
        
        # Save the form first
        response = super().form_valid(form)
        
        # Check how many enrollments exist for automatic attendance creation
        course = form.instance.course
        if course:
            confirmed_enrollments = course.enrollments.filter(status='confirmed')
            enrollment_count = confirmed_enrollments.count()
            
            # Add success message based on course type and include attendance info
            if course.repeat_pattern == 'once':
                messages.success(
                    self.request,
                    f'Single session for "{course.name}" has been scheduled successfully. '
                    f'Attendance records automatically created for {enrollment_count} enrolled students.'
                )
            else:
                messages.success(
                    self.request,
                    f'Class for "{course.name}" has been created successfully. '
                    f'Attendance records automatically created for {enrollment_count} enrolled students.'
                )
        else:
            messages.success(
                self.request,
                f'Class has been created successfully.'
            )
        
        return response
    
    def get_success_url(self):
        # Redirect back to course detail if course was pre-selected
        course_id = self.request.GET.get('course')
        if course_id:
            return reverse('academics:course_detail', kwargs={'pk': course_id})
        return super().get_success_url()


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'core/classes/detail.html'
    context_object_name = 'class'
    
    def get_queryset(self):
        """Override to ensure teachers can only access their own classes"""
        queryset = super().get_queryset()
        if hasattr(self.request.user, 'role') and self.request.user.role == 'teacher':
            queryset = queryset.filter(course__teacher=self.request.user)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get students for this class - combining enrolled students and manually added ones
        try:
            from enrollment.models import Enrollment, Attendance
            
            # Get enrolled students from course enrollments
            enrolled_students = []
            enrollments = Enrollment.objects.filter(
                course=self.object.course,
                status='confirmed'
            ).select_related('student')
            
            for enrollment in enrollments:
                # Check if student has attendance record for this class
                attendance = Attendance.objects.filter(
                    student=enrollment.student,
                    class_instance=self.object
                ).first()
                
                enrolled_students.append({
                    'student': enrollment.student,
                    'participation_type': 'enrolled',
                    'attendance_status': attendance.status if attendance else None,
                })
            
            context['class_students'] = enrolled_students
            
            # Get all attendance records for this class
            context['attendances'] = Attendance.objects.filter(
                class_instance=self.object
            ).select_related('student').order_by('attendance_time')
            
            # Calculate attendance statistics
            attendance_counts = {
                'present': context['attendances'].filter(status='present').count(),
                'absent': context['attendances'].filter(status='absent').count(),
                'late': context['attendances'].filter(status='late').count(),
            }
            context['attendance_stats'] = attendance_counts
            
        except ImportError:
            context['class_students'] = []
            context['attendances'] = []
            context['attendance_stats'] = {'present': 0, 'absent': 0, 'late': 0}
        
        # Add user role context for template logic
        context['is_teacher'] = hasattr(self.request.user, 'role') and self.request.user.role == 'teacher'
        
        return context


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = Class
    form_class = ClassUpdateForm
    template_name = 'core/classes/form.html'
    
    def get_success_url(self):
        return reverse_lazy('academics:class_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Check if key fields have changed and warn about impacts
        if self.object.pk:  # Only for updates, not new instances
            original = Class.objects.get(pk=self.object.pk)
            changed_fields = []
            
            # Check critical fields that might affect students/attendance
            critical_fields = ['date', 'start_time', 'teacher', 'classroom']
            for field in critical_fields:
                if getattr(original, field) != form.cleaned_data.get(field):
                    changed_fields.append(field)
            
            if changed_fields:
                field_names = ', '.join(changed_fields)
                messages.warning(
                    self.request, 
                    f'Class {field_names} updated. Please notify enrolled students of any changes.'
                )
        
        messages.success(self.request, f'Class updated successfully!')
        return super().form_valid(form)


class ClassDeleteView(LoginRequiredMixin, DeleteView):
    """Delete class with confirmation and safety checks"""
    model = Class
    template_name = 'core/classes/delete.html'
    
    def get_success_url(self):
        # Return to course detail page after deletion
        return reverse_lazy('academics:course_detail', kwargs={'pk': self.object.course.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get deletion impact information
        try:
            from enrollment.models import Attendance
            attendance_count = Attendance.objects.filter(class_instance=self.object).count()
            context['attendance_count'] = attendance_count
            context['has_attendance'] = attendance_count > 0
        except ImportError:
            context['attendance_count'] = 0
            context['has_attendance'] = False
        
        # Get enrolled students for this course
        enrolled_count = self.object.course.enrollments.filter(status='confirmed').count()
        context['enrolled_students_count'] = enrolled_count
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """Override delete to add safety checks and logging"""
        self.object = self.get_object()
        course_name = self.object.course.name
        class_date = self.object.date
        
        try:
            # Check if user has permission (admin only)
            if not request.user.is_superuser and request.user.role != 'admin':
                messages.error(request, 'Only administrators can delete classes.')
                return redirect('academics:class_detail', pk=self.object.pk)
            
            # Delete related attendance records (CASCADE should handle this, but being explicit)
            from enrollment.models import Attendance
            attendance_deleted = Attendance.objects.filter(class_instance=self.object).count()
            
            # Perform the deletion
            response = super().delete(request, *args, **kwargs)
            
            # Success message with impact information
            message = f'Class on {class_date.strftime("%d %B %Y")} for "{course_name}" has been deleted.'
            if attendance_deleted > 0:
                message += f' {attendance_deleted} attendance record(s) were also removed.'
            
            messages.success(request, message)
            return response
            
        except Exception as e:
            messages.error(request, f'Error deleting class: {str(e)}')
            return redirect('academics:class_detail', pk=self.object.pk)
