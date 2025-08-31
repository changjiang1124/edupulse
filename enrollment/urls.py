from django.urls import path
from . import views

app_name = 'enrollment'

urlpatterns = [
    # Staff Enrollment Management (require authentication)
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/create/', views.EnrollmentCreateView.as_view(), name='enrollment_create'),
    path('enrollments/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
    path('enrollments/<int:pk>/edit/', views.EnrollmentUpdateView.as_view(), name='enrollment_update'),
    path('enrollments/<int:pk>/delete/', views.EnrollmentDeleteView.as_view(), name='enrollment_delete'),
    
    # Public Enrollment (no authentication required)
    path('', views.PublicEnrollmentView.as_view(), name='public_enrollment'),
    path('course/<int:course_id>/', views.PublicEnrollmentView.as_view(), name='public_enrollment_with_course'),
    path('success/<int:enrollment_id>/', views.EnrollmentSuccessView.as_view(), name='enrollment_success'),
    
    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/mark/<int:class_id>/', views.AttendanceMarkView.as_view(), name='attendance_mark'),
]