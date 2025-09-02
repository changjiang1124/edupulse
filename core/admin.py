from django.contrib import admin
from .models import ClockInOut, EmailSettings, SMSSettings, EmailLog, SMSLog, NotificationQuota


@admin.register(EmailSettings)
class EmailSettingsAdmin(admin.ModelAdmin):
    list_display = ('email_backend_type', 'smtp_username', 'from_email', 'is_active', 'test_status', 'updated_at')
    list_filter = ('email_backend_type', 'is_active', 'test_status', 'created_at')
    search_fields = ('smtp_username', 'from_email')
    ordering = ('-updated_at',)
    
    readonly_fields = ('last_test_date', 'test_status', 'test_message', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Service Configuration', {
            'fields': ('email_backend_type', 'is_active')
        }),
        ('SMTP Settings', {
            'fields': ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'use_tls')
        }),
        ('Sender Information', {
            'fields': ('from_email', 'from_name', 'reply_to_email')
        }),
        ('Test Results', {
            'fields': ('last_test_date', 'test_status', 'test_message'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(SMSSettings)
class SMSSettingsAdmin(admin.ModelAdmin):
    list_display = ('sms_backend_type', 'from_number', 'sender_name', 'is_active', 'test_status', 'updated_at')
    list_filter = ('sms_backend_type', 'is_active', 'test_status', 'created_at')
    search_fields = ('from_number', 'sender_name', 'account_sid')
    ordering = ('-updated_at',)
    
    readonly_fields = ('last_test_date', 'test_status', 'test_message', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Service Configuration', {
            'fields': ('sms_backend_type', 'is_active')
        }),
        ('Twilio Settings', {
            'fields': ('account_sid', 'auth_token', 'from_number'),
            'description': 'Configuration for Twilio SMS service'
        }),
        ('Custom SMS Gateway', {
            'fields': ('api_url', 'api_key'),
            'classes': ('collapse',),
            'description': 'For future custom SMS gateway integration'
        }),
        ('Sender Information', {
            'fields': ('sender_name',)
        }),
        ('Test Results', {
            'fields': ('last_test_date', 'test_status', 'test_message'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )


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


@admin.register(NotificationQuota)
class NotificationQuotaAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'year', 'month', 'used_count', 'monthly_limit', 'usage_percentage_display', 'is_quota_exceeded')
    list_filter = ('notification_type', 'year', 'month')
    search_fields = ('notification_type',)
    ordering = ('-year', '-month', 'notification_type')
    
    readonly_fields = ('used_count', 'usage_percentage_display', 'is_quota_exceeded', 'remaining_quota', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Quota Configuration', {
            'fields': ('notification_type', 'year', 'month', 'monthly_limit')
        }),
        ('Usage Statistics', {
            'fields': ('used_count', 'remaining_quota', 'usage_percentage_display', 'is_quota_exceeded'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def usage_percentage_display(self, obj):
        """Display usage percentage with formatting"""
        percentage = obj.usage_percentage
        if percentage >= 90:
            color = 'red'
        elif percentage >= 70:
            color = 'orange'
        else:
            color = 'green'
        return f'<span style="color: {color}; font-weight: bold;">{percentage:.1f}%</span>'
    
    usage_percentage_display.allow_tags = True
    usage_percentage_display.short_description = 'Usage %'
    
    def get_readonly_fields(self, request, obj=None):
        """Make used_count readonly for existing objects"""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            return readonly
        else:  # Creating new object
            readonly.remove('used_count')
            readonly.remove('usage_percentage_display')
            readonly.remove('is_quota_exceeded')
            readonly.remove('remaining_quota')
            return readonly


# Custom Admin Site Configuration
admin.site.site_header = 'EduPulse Management System'
admin.site.site_title = 'EduPulse Admin'
admin.site.index_title = 'Welcome to EduPulse Admin Portal'
