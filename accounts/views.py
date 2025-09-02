from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q

from .models import Staff
from .forms import StaffForm, StaffCreationForm


class AdminRequiredMixin(UserPassesTestMixin):
    """Admin permission check mixin"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'


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
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )
        return queryset.order_by('last_name', 'first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class StaffCreateView(AdminRequiredMixin, CreateView):
    model = Staff
    form_class = StaffCreationForm
    template_name = 'core/staff/form.html'
    success_url = reverse_lazy('accounts:staff_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Staff member {form.instance.first_name} {form.instance.last_name} created successfully!')
        return super().form_valid(form)


class StaffDetailView(AdminRequiredMixin, DetailView):
    model = Staff
    template_name = 'core/staff/detail.html'
    context_object_name = 'staff'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add teacher-related courses and classes - with try/except to avoid errors
        try:
            # Import here to avoid circular imports
            from academics.models import Course, Class
            context['taught_courses'] = Course.objects.filter(teacher=self.object, status='published')
            context['taught_classes'] = Class.objects.filter(
                course__teacher=self.object
            ).select_related('course').order_by('-date')[:5]
        except ImportError:
            context['taught_courses'] = []
            context['taught_classes'] = []
        return context


class StaffUpdateView(AdminRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = 'core/staff/form.html'
    
    def get_success_url(self):
        return reverse_lazy('accounts:staff_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Staff member {form.instance.first_name} {form.instance.last_name} updated successfully!')
        return super().form_valid(form)
