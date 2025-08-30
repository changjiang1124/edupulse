from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Clock In/Out - Staff specific functionality
    path('clock/', views.ClockInOutView.as_view(), name='clockinout'),
    path('timesheet/', views.TimesheetView.as_view(), name='timesheet'),
    
    # TinyMCE Image Upload
    path('tinymce/upload/', views.tinymce_upload_image, name='tinymce_upload'),
]