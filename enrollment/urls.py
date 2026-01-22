from django.urls import path
from . import views

app_name = 'enrollment'

urlpatterns = [
    # Staff Enrollment Management (require authentication)
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/export/', views.EnrollmentExportView.as_view(), name='enrollment_export'),
    path('enrollments/create/', views.EnrollmentCreateView.as_view(), name='enrollment_create'),
    path('enrollments/staff/create/', views.StaffEnrollmentCreateView.as_view(), name='staff_enrollment_create'),
    path('enrollments/staff/create/<int:course_id>/', views.StaffEnrollmentCreateView.as_view(), name='staff_enrollment_create_with_course'),
    path('enrollments/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
    path('enrollments/<int:pk>/edit/', views.EnrollmentUpdateView.as_view(), name='enrollment_update'),
    path('enrollments/<int:pk>/transfer/', views.EnrollmentTransferView.as_view(), name='enrollment_transfer'),
    path('enrollments/<int:pk>/delete/', views.EnrollmentDeleteView.as_view(), name='enrollment_delete'),
    path('enrollments/<int:pk>/send-email/', views.SendEnrollmentEmailView.as_view(), name='send_enrollment_email'),
    path('enrollments/<int:pk>/invoice/', views.DownloadEnrollmentInvoiceView.as_view(), name='enrollment_invoice'),
    
    # Student Search API for staff
    path('api/students/search/', views.StudentSearchAPIView.as_view(), name='student_search_api'),

    # Price Adjustment API for early bird deadline handling
    path('api/check-price-adjustment/<int:enrollment_id>/', views.CheckPriceAdjustmentAPIView.as_view(), name='check_price_adjustment_api'),
    path('api/price-adjustment/<int:enrollment_id>/', views.ApplyPriceAdjustmentAPIView.as_view(), name='apply_price_adjustment_api'),
    
    # Bulk Notification
    path('enrollments/bulk-notification/start/', views.bulk_enrollment_notification_start, name='bulk_notification_start'),
    path('enrollments/bulk-notification/execute/<uuid:task_id>/', views.bulk_enrollment_notification_execute, name='bulk_notification_execute'),
    path('enrollments/bulk-notification/progress/<uuid:task_id>/', views.bulk_enrollment_notification_progress, name='bulk_notification_progress'),
    
    # Public Enrollment (no authentication required)
    path('', views.PublicEnrollmentView.as_view(), name='public_enrollment'),
    path('course/<int:course_id>/', views.PublicEnrollmentView.as_view(), name='public_enrollment_with_course'),
    path('success/<int:enrollment_id>/', views.EnrollmentSuccessView.as_view(), name='enrollment_success'),
    
    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/mark/<int:class_id>/', views.AttendanceMarkView.as_view(), name='attendance_mark'),
    path('attendance/update/<int:pk>/', views.AttendanceUpdateView.as_view(), name='attendance_update'),
    path('attendance/search/students/', views.StudentSearchView.as_view(), name='student_search'),
]