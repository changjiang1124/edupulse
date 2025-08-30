from django.contrib import admin
from .models import Student


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
