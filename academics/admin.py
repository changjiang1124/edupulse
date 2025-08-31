from django.contrib import admin
from .models import Course, Class


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'course_type', 'teacher', 'price', 'get_period_display', 'vacancy', 'is_online_bookable', 'bookable_state')
    list_filter = ('status', 'course_type', 'teacher', 'is_online_bookable', 'bookable_state', 'start_date')
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


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('course', 'date', 'start_time', 'teacher', 'classroom', 'is_active')
    list_filter = ('course', 'teacher', 'facility', 'is_active', 'date')
    search_fields = ('course__name', 'teacher__first_name', 'teacher__last_name')
    ordering = ('-date', 'start_time')
