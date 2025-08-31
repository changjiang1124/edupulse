from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
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
        queryset = Course.objects.filter(is_active=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
        return queryset.order_by('-created_at')


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
        update_fields = form.cleaned_data.get('class_update_fields', [])
        from_date = form.cleaned_data.get('update_classes_from_date')
        
        if update_existing and update_fields:
            # Get classes to update
            classes_queryset = self.object.classes.filter(is_active=True)
            
            if from_date:
                classes_queryset = classes_queryset.filter(date__gte=from_date)
            
            classes_to_update = classes_queryset.all()
            updated_count = 0
            
            # Update each class with selected fields
            for class_instance in classes_to_update:
                updated = False
                for field in update_fields:
                    if field in ['teacher', 'facility', 'classroom', 'start_time', 'duration_minutes']:
                        new_value = getattr(self.object, field)
                        current_value = getattr(class_instance, field)
                        if current_value != new_value:
                            setattr(class_instance, field, new_value)
                            updated = True
                
                if updated:
                    class_instance.save()
                    updated_count += 1
            
            if updated_count > 0:
                field_names = ', '.join([dict(form.fields['class_update_fields'].choices)[f] for f in update_fields])
                messages.success(
                    self.request,
                    f'Course updated successfully! {updated_count} class(es) updated with new {field_names}.'
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
