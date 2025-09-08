from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Clock In/Out - Staff specific functionality
    path('clock/', views.ClockInOutView.as_view(), name='clockinout'),
    path('timesheet/', views.TimesheetView.as_view(), name='timesheet'),
    
    # Teacher Attendance System
    path('attendance/teacher/clock/', views.TeacherClockView.as_view(), name='teacher_clock'),
    path('attendance/teacher/qr/', views.TeacherQRAttendanceView.as_view(), name='teacher_qr_attendance'),
    path('attendance/teacher/verify-location/', views.TeacherLocationVerifyView.as_view(), name='teacher_location_verify'),
    path('attendance/teacher/submit/', views.TeacherClockSubmitView.as_view(), name='teacher_clock_submit'),
    path('attendance/teacher/history/', views.TeacherAttendanceHistoryView.as_view(), name='teacher_attendance_history'),
    
    # Timesheet Export
    path('timesheet/export/', views.TimesheetExportView.as_view(), name='timesheet_export'),
    path('timesheet/monthly/<int:year>/<int:month>/', views.MonthlyTimesheetView.as_view(), name='monthly_timesheet'),
    
    # QR Code Management
    path('qr-codes/', views.QRCodeManagementView.as_view(), name='qr_code_management'),
    path('qr-codes/facility/<int:facility_id>/', views.GenerateFacilityQRCodesView.as_view(), name='generate_facility_qr_codes'),
    
    # TinyMCE Image Upload
    path('tinymce/upload/', views.tinymce_upload_image, name='tinymce_upload'),
    
    # Email configuration URLs
    path('settings/email/', views.email_settings_view, name='email_settings'),
    path('settings/email/test-connection/', views.test_email_connection, name='test_email_connection'),
    path('settings/email/send-test/', views.send_test_email, name='send_test_email'),
    path('settings/email/logs/', views.email_logs_view, name='email_logs'),
    
    # SMS configuration URLs
    path('settings/sms/', views.sms_settings_view, name='sms_settings'),
    path('settings/sms/test-connection/', views.test_sms_connection, name='test_sms_connection'),
    path('settings/sms/send-test/', views.send_test_sms, name='send_test_sms'),
    path('settings/sms/logs/', views.sms_logs_view, name='sms_logs'),
    
    # Organisation settings URLs
    path('settings/organisation/', views.organisation_settings_view, name='organisation_settings'),
    path('settings/organisation/test-gst/', views.test_gst_calculation, name='test_gst_calculation'),
    
    # Notification system URLs
    path('notifications/send/', views.send_notification_view, name='send_notification'),
    path('notifications/quotas/', views.get_notification_quotas, name='get_notification_quotas'),
]