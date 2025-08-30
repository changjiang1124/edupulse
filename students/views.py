from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q

from .models import Student
from .forms import StudentForm


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
    form_class = StudentForm
    template_name = 'core/students/form.html'
    success_url = reverse_lazy('core:student_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Student {form.instance.first_name} {form.instance.last_name} added successfully!')
        return super().form_valid(form)


class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'core/students/detail.html'
    context_object_name = 'student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add enrollments and attendance information
        context['enrollments'] = self.object.enrollments.select_related('course').all()
        context['attendances'] = self.object.attendances.select_related(
            'class_instance__course'
        ).order_by('-attendance_time')[:10]
        return context


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'core/students/form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:student_detail', kwargs={'pk': self.object.pk})
