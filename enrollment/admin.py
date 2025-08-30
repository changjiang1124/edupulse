from django.contrib import admin
from .models import Enrollment, Attendance


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'source_channel', 'created_at')
    list_filter = ('status', 'source_channel', 'created_at', 'course')
    search_fields = ('student__first_name', 'student__last_name', 'course__name')
    ordering = ('-created_at',)
    
    readonly_fields = ('form_data',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_instance', 'status', 'attendance_time', 'created_at')
    list_filter = ('status', 'attendance_time', 'class_instance__course')
    search_fields = ('student__first_name', 'student__last_name', 'class_instance__course__name')
    ordering = ('-attendance_time',)
