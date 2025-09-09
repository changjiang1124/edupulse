from django.contrib import admin
from django.utils.html import format_html
from .models import Student, StudentTag, StudentActivity


@admin.register(StudentTag)
class StudentTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'colour_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def colour_display(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            obj.colour,
            obj.colour
        )
    colour_display.short_description = 'Colour'


class StudentActivityInline(admin.TabularInline):
    model = StudentActivity
    extra = 0
    readonly_fields = ['created_at']
    fields = ['activity_type', 'title', 'enrollment', 'course', 'performed_by', 'is_visible_to_student', 'created_at']
    ordering = ['-created_at']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'first_name', 'last_name', 'contact_email', 'contact_phone', 
        'get_age_display', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'registration_status', 'created_at', 'tags']
    search_fields = [
        'first_name', 'last_name', 'contact_email', 'contact_phone', 'guardian_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'birth_date', 'address')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone'),
            'description': 'Primary contact information (student or guardian depending on age)'
        }),
        ('Guardian Information', {
            'fields': ('guardian_name',),
            'description': 'Required for students under 18 years of age'
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Medical Information', {
            'fields': ('medical_conditions', 'special_requirements'),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('staff_notes', 'internal_notes', 'registration_status', 'enrollment_source', 'tags'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ['tags']
    inlines = [StudentActivityInline]
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def get_age_display(self, obj):
        """Display student age for admin list"""
        age = obj.get_age()
        if age is not None:
            guardian_info = " (Minor)" if age < 18 else ""
            return f"{age}{guardian_info}"
        return "Unknown"
    get_age_display.short_description = 'Age'
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} student(s) marked as active.')
    mark_as_active.short_description = "Mark selected students as active"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} student(s) marked as inactive.')
    mark_as_inactive.short_description = "Mark selected students as inactive"


@admin.register(StudentActivity)
class StudentActivityAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'activity_type_display', 'title', 'course', 'enrollment', 
        'performed_by', 'is_visible_to_student', 'created_at'
    ]
    list_filter = [
        'activity_type', 'is_visible_to_student', 'created_at', 'course', 'performed_by'
    ]
    search_fields = [
        'student__first_name', 'student__last_name', 'title', 'description',
        'course__name', 'enrollment__id'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('student', 'activity_type', 'title', 'description')
        }),
        ('Related Objects', {
            'fields': ('enrollment', 'course', 'performed_by'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'is_visible_to_student'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def activity_type_display(self, obj):
        icon = obj.get_activity_icon()
        color = obj.get_activity_color()
        return format_html(
            '<i class="fas {} text-{}"></i> {}',
            icon,
            color,
            obj.get_activity_type_display()
        )
    activity_type_display.short_description = 'Activity Type'
    
    actions = ['mark_visible_to_student', 'mark_not_visible_to_student']
    
    def mark_visible_to_student(self, request, queryset):
        updated = queryset.update(is_visible_to_student=True)
        self.message_user(request, f'{updated} activity(ies) marked as visible to students.')
    mark_visible_to_student.short_description = "Mark selected activities as visible to students"
    
    def mark_not_visible_to_student(self, request, queryset):
        updated = queryset.update(is_visible_to_student=False)
        self.message_user(request, f'{updated} activity(ies) marked as not visible to students.')
    mark_not_visible_to_student.short_description = "Mark selected activities as not visible to students"
