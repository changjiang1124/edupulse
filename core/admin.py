from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Staff, Facility, Classroom, Student, Course, Class, 
    Enrollment, Attendance, ClockInOut, EmailLog, SMSLog
)


@admin.register(Staff)
class StaffAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active_staff', 'created_at')
    list_filter = ('role', 'is_active_staff', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'role', 'is_active_staff')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'role', 'is_active_staff')
        }),
    )


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'address', 'phone', 'email')
    ordering = ('name',)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'facility', 'capacity', 'is_active', 'created_at')
    list_filter = ('facility', 'is_active', 'created_at')
    search_fields = ('name', 'facility__name')
    ordering = ('facility__name', 'name')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'guardian_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'guardian_name', 'guardian_email')
    ordering = ('last_name', 'first_name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'birth_date', 'email', 'phone', 'address')
        }),
        ('Guardian Information', {
            'fields': ('guardian_name', 'guardian_phone', 'guardian_email')
        }),
        ('Additional Info', {
            'fields': ('reference', 'is_active')
        })
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'course_type', 'teacher', 'price', 'get_period_display', 'vacancy', 'is_bookable', 'is_active')
    list_filter = ('status', 'course_type', 'teacher', 'is_bookable', 'is_active', 'start_date')
    search_fields = ('name', 'description', 'short_description', 'teacher__first_name', 'teacher__last_name')
    ordering = ('-start_date',)
    actions = ['generate_classes_action', 'publish_courses', 'unpublish_courses']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'short_description', 'description', 'price', 'course_type', 'status', 'teacher')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes')
        }),
        ('Capacity & Booking', {
            'fields': ('vacancy', 'is_bookable')
        }),
        ('Location', {
            'fields': ('facility', 'classroom')
        }),
        ('WooCommerce Integration', {
            'fields': ('external_id', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def generate_classes_action(self, request, queryset):
        """Admin action to generate classes for selected courses"""
        total_classes = 0
        for course in queryset:
            classes_created = course.generate_classes()
            total_classes += classes_created
        
        self.message_user(
            request, 
            f"Generated {total_classes} classes for {queryset.count()} courses."
        )
    generate_classes_action.short_description = "Generate classes for selected courses"
    
    def publish_courses(self, request, queryset):
        """Admin action to publish courses"""
        updated = queryset.update(status='published')
        self.message_user(
            request,
            f"{updated} courses were successfully published."
        )
    publish_courses.short_description = "Mark selected courses as published"
    
    def unpublish_courses(self, request, queryset):
        """Admin action to unpublish courses"""
        updated = queryset.update(status='draft')
        self.message_user(
            request,
            f"{updated} courses were marked as draft."
        )
    unpublish_courses.short_description = "Mark selected courses as draft"


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('course', 'date', 'start_time', 'teacher', 'classroom', 'is_active')
    list_filter = ('course', 'teacher', 'facility', 'is_active', 'date')
    search_fields = ('course__name', 'teacher__first_name', 'teacher__last_name')
    ordering = ('-date', 'start_time')


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


@admin.register(ClockInOut)
class ClockInOutAdmin(admin.ModelAdmin):
    list_display = ('staff', 'status', 'timestamp', 'latitude', 'longitude')
    list_filter = ('status', 'timestamp', 'staff')
    search_fields = ('staff__first_name', 'staff__last_name', 'staff__username')
    ordering = ('-timestamp',)
    
    readonly_fields = ('created_at',)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'recipient_type', 'email_type', 'subject', 'status', 'created_at')
    list_filter = ('status', 'email_type', 'recipient_type', 'created_at')
    search_fields = ('recipient_email', 'subject', 'content')
    ordering = ('-created_at',)
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_phone', 'recipient_type', 'sms_type', 'status', 'created_at')
    list_filter = ('status', 'sms_type', 'recipient_type', 'created_at')
    search_fields = ('recipient_phone', 'content')
    ordering = ('-created_at',)
    
    readonly_fields = ('created_at', 'updated_at')


# 自定义 Admin 站点标题
admin.site.site_header = 'EduPulse 管理系统'
admin.site.site_title = 'EduPulse Admin'
admin.site.index_title = '欢迎来到 EduPulse 管理后台'
