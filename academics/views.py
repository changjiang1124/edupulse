from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date

from .models import Course, Class
from .forms import CourseForm, ClassForm


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
    success_url = reverse_lazy('core:course_list')
    
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
        context['classes'] = self.object.classes.filter(is_active=True).order_by('date', 'start_time')
        context['enrollments'] = self.object.enrollments.select_related('student').all()
        return context


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'core/courses/form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Regenerate classes if schedule changes
        if any(field in form.changed_data for field in ['start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes']):
            classes_created = self.object.generate_classes()
            messages.success(
                self.request, 
                f'Course "{self.object.name}" updated successfully! {classes_created} class(es) regenerated.'
            )
        else:
            messages.success(self.request, f'Course "{self.object.name}" updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('core:course_detail', kwargs={'pk': self.object.pk})


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
        return context


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    form_class = ClassForm
    template_name = 'core/classes/form.html'
    success_url = reverse_lazy('core:class_list')


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'core/classes/detail.html'
    context_object_name = 'class'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get attendance records for this class
        context['attendances'] = self.object.attendances.select_related('student').all()
        # Get enrolled students for this course
        context['enrolled_students'] = self.object.course.enrollments.filter(
            status='confirmed'
        ).select_related('student')
        return context
