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
import core.views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/', core_views.DashboardView.as_view(), name='dashboard_direct'),
    
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
    path('enrollment/', include(('enrollment.urls', 'enrollment'), namespace='staff_enrollment')),
    
    # Django RQ dashboard (queue monitoring)
    path('django-rq/', include('django_rq.urls')),
    
    # TinyMCE URL
    path('tinymce/', include('tinymce.urls')),
    
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password change URLs  
    path('auth/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='auth/password_change.html',
        success_url='/auth/password_change/done/'
    ), name='password_change'),
    path('auth/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='auth/password_change_done.html'
    ), name='password_change_done'),
]

# Static file serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
