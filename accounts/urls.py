from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Profile URL
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Staff URLs
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/add/', views.StaffCreateView.as_view(), name='staff_add'),
    path('staff/<int:pk>/', views.StaffDetailView.as_view(), name='staff_detail'),
    path('staff/<int:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_edit'),
]