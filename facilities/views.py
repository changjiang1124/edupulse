from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Count, Q

from .models import Facility, Classroom
from .forms import FacilityForm, ClassroomForm


class AdminRequiredMixin(UserPassesTestMixin):
    """Admin permission check mixin"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'


class FacilityListView(AdminRequiredMixin, ListView):
    model = Facility
    template_name = 'core/facilities/list.html'
    context_object_name = 'facilities'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Facility.objects.annotate(
            classroom_count=Count('classrooms', filter=Q(classrooms__is_active=True))
        ).filter(is_active=True)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class FacilityCreateView(AdminRequiredMixin, CreateView):
    model = Facility
    form_class = FacilityForm
    template_name = 'core/facilities/form.html'
    success_url = reverse_lazy('core:facility_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Facility "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class FacilityDetailView(AdminRequiredMixin, DetailView):
    model = Facility
    template_name = 'core/facilities/detail.html'
    context_object_name = 'facility'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add classrooms and courses for this facility
        context['classrooms'] = self.object.classrooms.filter(is_active=True)
        context['courses'] = self.object.course_set.filter(is_active=True)
        return context


class FacilityUpdateView(AdminRequiredMixin, UpdateView):
    model = Facility
    form_class = FacilityForm
    template_name = 'core/facilities/form.html'
    
    def form_valid(self, form):
        messages.success(self.request, f'Facility "{form.instance.name}" updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('core:facility_detail', kwargs={'pk': self.object.pk})


class ClassroomListView(AdminRequiredMixin, ListView):
    model = Classroom
    template_name = 'core/classrooms/list.html'
    context_object_name = 'classrooms'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Classroom.objects.select_related('facility').filter(is_active=True)
        
        # Filter by facility if specified
        facility_id = self.request.GET.get('facility')
        if facility_id:
            queryset = queryset.filter(facility_id=facility_id)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(facility__name__icontains=search)
            )
        return queryset.order_by('facility__name', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['facilities'] = Facility.objects.filter(is_active=True).order_by('name')
        context['selected_facility'] = self.request.GET.get('facility', '')
        return context


class ClassroomCreateView(AdminRequiredMixin, CreateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'core/classrooms/form.html'
    success_url = reverse_lazy('core:classroom_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Classroom "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ClassroomDetailView(AdminRequiredMixin, DetailView):
    model = Classroom
    template_name = 'core/classrooms/detail.html'
    context_object_name = 'classroom'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add courses and classes using this classroom
        context['courses'] = self.object.course_set.filter(is_active=True)
        context['classes'] = self.object.class_set.filter(is_active=True).select_related('course').order_by('-date')[:10]
        return context


class ClassroomUpdateView(AdminRequiredMixin, UpdateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'core/classrooms/form.html'
    
    def form_valid(self, form):
        messages.success(self.request, f'Classroom "{form.instance.name}" updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('core:classroom_detail', kwargs={'pk': self.object.pk})
