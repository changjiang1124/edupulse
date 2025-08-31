"""
URL configuration for edupulse project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='dashboard'),
    
    # Core application (Dashboard, Clock, etc.)
    path('core/', include('core.urls')),
    
    # Modular applications
    path('accounts/', include('accounts.urls')),
    path('students/', include('students.urls')),
    path('academics/', include('academics.urls')),
    path('facilities/', include('facilities.urls')),
    
    # Public enrollment URLs (accessible at /enroll/)
    path('enroll/', include('enrollment.urls')),
    
    # Staff enrollment management URLs (accessible at /enrollment/)  
    path('enrollment/', include('enrollment.urls', namespace='staff_enrollment')),
    
    # TinyMCE URL
    path('tinymce/', include('tinymce.urls')),
    
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Static file serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
