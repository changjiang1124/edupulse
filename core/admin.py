from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ClockInOut, EmailSettings, SMSSettings, EmailLog, SMSLog, 
    NotificationQuota, WooCommerceSyncLog, WooCommerceSyncQueue
)
import json


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


@admin.register(WooCommerceSyncLog)
class WooCommerceSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        'course_name', 'sync_type', 'status_display', 'wc_product_id', 
        'duration_display', 'retry_count', 'created_at'
    )
    list_filter = (
        'sync_type', 'status', 'created_at', 'retry_count'
    )
    search_fields = (
        'course__name', 'course_name', 'wc_product_id', 'error_message'
    )
    ordering = ('-created_at',)
    readonly_fields = (
        'course', 'sync_type', 'status', 'wc_product_id', 'wc_category_id', 
        'wc_category_name', 'duration_ms', 'retry_count', 'created_at', 
        'last_attempt_at', 'completed_at', 'request_data_display', 
        'response_data_display', 'error_message'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('course', 'course_name', 'sync_type', 'status')
        }),
        ('WooCommerce Data', {
            'fields': ('wc_product_id', 'wc_category_id', 'wc_category_name')
        }),
        ('Performance & Timing', {
            'fields': ('duration_ms', 'retry_count', 'created_at', 'last_attempt_at', 'completed_at')
        }),
        ('Request/Response Data', {
            'fields': ('request_data_display', 'response_data_display'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['retry_failed_syncs', 'mark_as_success']
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'success': 'green',
            'failed': 'red',
            'processing': 'orange',
            'pending': 'blue',
            'retrying': 'purple'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def request_data_display(self, obj):
        """Pretty display for request data"""
        if obj.request_data:
            return format_html(
                '<pre style="white-space: pre-wrap;">{}</pre>',
                json.dumps(obj.request_data, indent=2)
            )
        return 'No request data'
    request_data_display.short_description = 'Request Data'
    
    def response_data_display(self, obj):
        """Pretty display for response data"""
        if obj.response_data:
            return format_html(
                '<pre style="white-space: pre-wrap;">{}</pre>',
                json.dumps(obj.response_data, indent=2)
            )
        return 'No response data'
    response_data_display.short_description = 'Response Data'
    
    def retry_failed_syncs(self, request, queryset):
        """Admin action to retry failed syncs"""
        from core.woocommerce_api import WooCommerceSyncService
        
        failed_logs = queryset.filter(status='failed', course__isnull=False)
        success_count = 0
        
        sync_service = WooCommerceSyncService()
        
        for log in failed_logs:
            if log.can_retry:
                try:
                    result = sync_service.sync_course_to_woocommerce(log.course)
                    if result['status'] == 'success':
                        success_count += 1
                except Exception:
                    continue
        
        self.message_user(
            request,
            f"Retried {failed_logs.count()} failed syncs. {success_count} succeeded."
        )
    retry_failed_syncs.short_description = "Retry failed synchronizations"
    
    def mark_as_success(self, request, queryset):
        """Admin action to manually mark syncs as successful"""
        updated = queryset.update(status='success')
        self.message_user(
            request,
            f"Marked {updated} sync logs as successful."
        )
    mark_as_success.short_description = "Mark selected syncs as successful"


@admin.register(WooCommerceSyncQueue)
class WooCommerceSyncQueueAdmin(admin.ModelAdmin):
    list_display = (
        'course', 'action', 'priority_display', 'status_display', 
        'attempts', 'scheduled_for', 'created_at'
    )
    list_filter = (
        'action', 'status', 'priority', 'created_at', 'scheduled_for'
    )
    search_fields = (
        'course__name', 'last_error'
    )
    ordering = ('priority', 'scheduled_for')
    readonly_fields = (
        'course', 'created_at', 'updated_at', 'started_at', 
        'completed_at', 'duration_display'
    )
    
    fieldsets = (
        ('Task Information', {
            'fields': ('course', 'action', 'priority', 'scheduled_for')
        }),
        ('Status & Progress', {
            'fields': ('status', 'attempts', 'max_retries', 'sync_log')
        }),
        ('Error Information', {
            'fields': ('last_error',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['process_queued_items', 'cancel_queued_items', 'retry_failed_items']
    
    def priority_display(self, obj):
        """Display priority with color coding"""
        colors = {
            1: 'red',      # Critical
            3: 'orange',   # High  
            5: 'blue',     # Normal
            7: 'green',    # Low
            9: 'gray'      # Background
        }
        color = colors.get(obj.priority, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = 'Priority'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'completed': 'green',
            'failed': 'red',
            'processing': 'orange',
            'queued': 'blue',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def process_queued_items(self, request, queryset):
        """Admin action to process queued items"""
        from core.woocommerce_api import WooCommerceSyncService
        
        queued_items = queryset.filter(status='queued')
        processed_count = 0
        
        sync_service = WooCommerceSyncService()
        
        for item in queued_items:
            if item.is_ready:
                item.status = 'processing'
                item.save()
                
                try:
                    if item.action == 'sync':
                        result = sync_service.sync_course_to_woocommerce(item.course)
                    elif item.action == 'delete':
                        result = sync_service.remove_course_from_woocommerce(item.course)
                    
                    if result['status'] == 'success':
                        item.status = 'completed'
                        processed_count += 1
                    else:
                        item.status = 'failed'
                        item.last_error = result.get('message', 'Unknown error')
                    
                    item.attempts += 1
                    item.save()
                    
                except Exception as e:
                    item.status = 'failed'
                    item.last_error = str(e)
                    item.attempts += 1
                    item.save()
        
        self.message_user(
            request,
            f"Processed {queued_items.count()} queue items. {processed_count} succeeded."
        )
    process_queued_items.short_description = "Process selected queue items"
    
    def cancel_queued_items(self, request, queryset):
        """Admin action to cancel queued items"""
        updated = queryset.filter(status='queued').update(status='cancelled')
        self.message_user(
            request,
            f"Cancelled {updated} queued items."
        )
    cancel_queued_items.short_description = "Cancel selected queue items"
    
    def retry_failed_items(self, request, queryset):
        """Admin action to retry failed items"""
        failed_items = queryset.filter(status='failed')
        retryable_items = [item for item in failed_items if item.can_retry]
        
        for item in retryable_items:
            item.status = 'queued'
            item.save()
        
        self.message_user(
            request,
            f"Reset {len(retryable_items)} failed items to queued status for retry."
        )
    retry_failed_items.short_description = "Retry failed queue items"


# Custom Admin Site Configuration
admin.site.site_header = 'EduPulse Management System'
admin.site.site_title = 'EduPulse Admin'
admin.site.index_title = 'Welcome to EduPulse Admin Portal'
