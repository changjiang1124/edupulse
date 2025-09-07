from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date

from .models import Course, Class
from .forms import CourseForm, CourseUpdateForm, ClassForm


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
        
        # Add information about existing classes (counts)
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
        queryset = Class.objects.select_related('course', 'teacher', 'facility', 'classroom').filter(is_active=True)
        
        # Filter by date range (show upcoming classes by default)
        date_filter = self.request.GET.get('filter', 'upcoming')
        if date_filter == 'upcoming':
            queryset = queryset.filter(date__gte=timezone.now().date())
        elif date_filter == 'past':
            queryset = queryset.filter(date__lt=timezone.now().date())
            
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(course__name__icontains=search) |
                Q(teacher__first_name__icontains=search) |
                Q(teacher__last_name__icontains=search)
            )
        
        return queryset.order_by('date', 'start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.request.GET.get('filter', 'upcoming')
        context['search_query'] = self.request.GET.get('search', '')
        context['today'] = timezone.now().date()
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
        # Ensure course is set from GET when dropdown is disabled
        if not form.cleaned_data.get('course'):
            course_id = self.request.GET.get('course')
            if course_id:
                form.instance.course = Course.objects.filter(pk=course_id).first()
        return super().form_valid(form)


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'core/classes/detail.html'
    context_object_name = 'class'
    
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
        
        return context


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = Class
    form_class = ClassForm
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
