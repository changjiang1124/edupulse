from django.urls import path
from . import views

app_name = 'enrollment'

urlpatterns = [
    # Enrollment URLs
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
    
    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/mark/<int:class_id>/', views.AttendanceMarkView.as_view(), name='attendance_mark'),
]