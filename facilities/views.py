from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import os
import requests
import json

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
    success_url = reverse_lazy('facilities:facility_list')
    
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
        # Add courses for this facility - with try/except to avoid errors
        try:
            from academics.models import Course
            context['courses'] = Course.objects.filter(facility=self.object, status='published')
        except ImportError:
            context['courses'] = []
        return context


class FacilityUpdateView(AdminRequiredMixin, UpdateView):
    model = Facility
    form_class = FacilityForm
    template_name = 'core/facilities/form.html'
    
    def form_valid(self, form):
        messages.success(self.request, f'Facility "{form.instance.name}" updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('facilities:facility_detail', kwargs={'pk': self.object.pk})


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
    success_url = reverse_lazy('facilities:classroom_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Classroom "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class ClassroomDetailView(AdminRequiredMixin, DetailView):
    model = Classroom
    template_name = 'core/classrooms/detail.html'
    context_object_name = 'classroom'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add courses and classes using this classroom - with try/except to avoid errors
        try:
            from academics.models import Course, Class
            context['courses'] = Course.objects.filter(classroom=self.object, status='published')
            context['classes'] = Class.objects.filter(
                classroom=self.object, is_active=True
            ).select_related('course').order_by('-date')[:10]
        except ImportError:
            context['courses'] = []
            context['classes'] = []
        return context


class ClassroomUpdateView(AdminRequiredMixin, UpdateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'core/classrooms/form.html'
    
    def form_valid(self, form):
        messages.success(self.request, f'Classroom "{form.instance.name}" updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('facilities:classroom_detail', kwargs={'pk': self.object.pk})


@method_decorator(csrf_exempt, name='dispatch')
class AddressGeocodeView(AdminRequiredMixin, View):
    """
    AJAX endpoint for address geocoding using Google Maps API
    """
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            address = data.get('address', '').strip()
            
            if not address:
                return JsonResponse({'error': 'Address is required'}, status=400)
            
            # Get Google Maps API key
            api_key = os.getenv('GOOGLE_MAPS_API_KEY')
            if not api_key:
                return JsonResponse({'error': 'Google Maps API not configured'}, status=500)
            
            # Call Google Geocoding API
            url = 'https://maps.googleapis.com/maps/api/geocode/json'
            params = {
                'address': address,
                'key': api_key,
                'region': 'au',
                'components': 'country:AU'
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                
                return JsonResponse({
                    'success': True,
                    'formatted_address': result['formatted_address'],
                    'latitude': location['lat'],
                    'longitude': location['lng']
                })
            elif data['status'] == 'ZERO_RESULTS':
                return JsonResponse({'error': 'No results found for this address'}, status=404)
            elif data['status'] == 'OVER_QUERY_LIMIT':
                return JsonResponse({'error': 'API quota exceeded. Please try again later.'}, status=429)
            else:
                return JsonResponse({'error': f"Geocoding failed: {data['status']}"}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except requests.RequestException as e:
            return JsonResponse({'error': f'Network error: {str(e)}'}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class ClassroomAPIView(LoginRequiredMixin, View):
    """
    AJAX API view to get classrooms for a specific facility
    """
    def get(self, request, *args, **kwargs):
        facility_id = request.GET.get('facility_id')
        
        if not facility_id:
            return JsonResponse({'error': 'Facility ID is required'}, status=400)
        
        try:
            # Get active classrooms for the specified facility
            classrooms = Classroom.objects.filter(
                facility_id=facility_id,
                is_active=True
            ).order_by('name')
            
            classroom_list = [
                {
                    'id': classroom.id,
                    'name': classroom.name,
                    'capacity': classroom.capacity,
                    'display_name': f"{classroom.name} (Capacity: {classroom.capacity})"
                }
                for classroom in classrooms
            ]
            
            return JsonResponse({
                'success': True,
                'classrooms': classroom_list
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
