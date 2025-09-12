from django.urls import path
from . import views

app_name = 'facilities'

urlpatterns = [
    # Facility URLs
    path('', views.FacilityListView.as_view(), name='facility_list'),
    path('add/', views.FacilityCreateView.as_view(), name='facility_add'),
    path('<int:pk>/', views.FacilityDetailView.as_view(), name='facility_detail'),
    path('<int:pk>/edit/', views.FacilityUpdateView.as_view(), name='facility_edit'),
    
    # Address geocoding API
    path('api/geocode/', views.AddressGeocodeView.as_view(), name='address_geocode'),
    
    # Classroom API
    path('api/classrooms/', views.ClassroomAPIView.as_view(), name='classroom_api'),
    
    # Classroom URLs
    path('classrooms/', views.ClassroomListView.as_view(), name='classroom_list'),
    path('classrooms/add/', views.ClassroomCreateView.as_view(), name='classroom_add'),
    path('classrooms/<int:pk>/', views.ClassroomDetailView.as_view(), name='classroom_detail'),
    path('classrooms/<int:pk>/edit/', views.ClassroomUpdateView.as_view(), name='classroom_edit'),
]