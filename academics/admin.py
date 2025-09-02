from django.contrib import admin
from django.contrib import messages
from .models import Course, Class
from core.woocommerce_api import WooCommerceSyncService


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'course_type', 'category', 'teacher', 'price', 'get_period_display', 'vacancy', 'is_online_bookable', 'bookable_state', 'wc_sync_status')
    list_filter = ('status', 'course_type', 'category', 'teacher', 'is_online_bookable', 'bookable_state', 'start_date')
    search_fields = ('name', 'description', 'short_description', 'teacher__first_name', 'teacher__last_name')
    ordering = ('-start_date',)
    actions = ['generate_classes_action', 'publish_courses', 'unpublish_courses', 'sync_to_woocommerce', 'remove_from_woocommerce']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'short_description', 'description', 'price', 'course_type', 'category', 'status', 'teacher')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes')
        }),
        ('Capacity & Booking', {
            'fields': ('vacancy', 'is_online_bookable', 'enrollment_deadline')
        }),
        ('Location', {
            'fields': ('facility', 'classroom')
        }),
        ('WooCommerce Integration', {
            'fields': ('external_id',),
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
    
    def wc_sync_status(self, obj):
        """Display WooCommerce sync status"""
        if obj.external_id:
            return f"✓ WC ID: {obj.external_id}"
        return "Not synced"
    wc_sync_status.short_description = "WooCommerce Status"
    
    def sync_to_woocommerce(self, request, queryset):
        """Admin action to sync courses to WooCommerce"""
        sync_service = WooCommerceSyncService()
        success_count = 0
        error_count = 0
        
        for course in queryset:
            try:
                result = sync_service.sync_course_to_woocommerce(course)
                if result['status'] == 'success':
                    success_count += 1
                else:
                    error_count += 1
                    messages.error(request, f"Failed to sync {course.name}: {result.get('message', 'Unknown error')}")
            except Exception as e:
                error_count += 1
                messages.error(request, f"Error syncing {course.name}: {str(e)}")
        
        if success_count > 0:
            messages.success(request, f"Successfully synced {success_count} courses to WooCommerce.")
        if error_count > 0:
            messages.warning(request, f"{error_count} courses failed to sync.")
    
    sync_to_woocommerce.short_description = "Sync selected courses to WooCommerce"
    
    def remove_from_woocommerce(self, request, queryset):
        """Admin action to remove courses from WooCommerce"""
        sync_service = WooCommerceSyncService()
        success_count = 0
        error_count = 0
        
        for course in queryset:
            try:
                if course.external_id:
                    result = sync_service.remove_course_from_woocommerce(course)
                    if result['status'] == 'success':
                        success_count += 1
                    else:
                        error_count += 1
                        messages.error(request, f"Failed to remove {course.name}: {result.get('message', 'Unknown error')}")
                else:
                    messages.info(request, f"{course.name} is not synced to WooCommerce.")
            except Exception as e:
                error_count += 1
                messages.error(request, f"Error removing {course.name}: {str(e)}")
        
        if success_count > 0:
            messages.success(request, f"Successfully removed {success_count} courses from WooCommerce.")
        if error_count > 0:
            messages.warning(request, f"{error_count} courses failed to be removed.")
    
    remove_from_woocommerce.short_description = "Remove selected courses from WooCommerce"


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('course', 'date', 'start_time', 'teacher', 'classroom', 'is_active')
    list_filter = ('course', 'teacher', 'facility', 'is_active', 'date')
    search_fields = ('course__name', 'teacher__first_name', 'teacher__last_name')
    ordering = ('-date', 'start_time')
