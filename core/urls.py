from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Staff Management
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/add/', views.StaffCreateView.as_view(), name='staff_add'),
    path('staff/<int:pk>/', views.StaffDetailView.as_view(), name='staff_detail'),
    path('staff/<int:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_edit'),
    
    # Student Management
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/add/', views.StudentCreateView.as_view(), name='student_add'),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    
    # Course Management
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    
    # Class Management
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassCreateView.as_view(), name='class_add'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    
    # Facility Management
    path('facilities/', views.FacilityListView.as_view(), name='facility_list'),
    path('facilities/add/', views.FacilityCreateView.as_view(), name='facility_add'),
    path('facilities/<int:pk>/', views.FacilityDetailView.as_view(), name='facility_detail'),
    
    # Classroom Management
    path('classrooms/', views.ClassroomListView.as_view(), name='classroom_list'),
    path('classrooms/add/', views.ClassroomCreateView.as_view(), name='classroom_add'),
    path('classrooms/<int:pk>/', views.ClassroomDetailView.as_view(), name='classroom_detail'),
    path('classrooms/<int:pk>/edit/', views.ClassroomUpdateView.as_view(), name='classroom_edit'),
    
    # Enrollment Management
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
    
    # Attendance Management
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/mark/', views.AttendanceMarkView.as_view(), name='attendance_mark'),
    
    # Clock In/Out
    path('clock/', views.ClockInOutView.as_view(), name='clock_inout'),
    path('timesheet/', views.TimesheetView.as_view(), name='timesheet'),
    
    # TinyMCE Image Upload
    path('tinymce/upload/', views.tinymce_upload_image, name='tinymce_upload'),
]