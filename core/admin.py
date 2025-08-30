from django.contrib import admin
from .models import ClockInOut, EmailLog, SMSLog


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


# Custom Admin Site Configuration
admin.site.site_header = 'EduPulse Management System'
admin.site.site_title = 'EduPulse Admin'
admin.site.index_title = 'Welcome to EduPulse Admin Portal'
