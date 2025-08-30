from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Staff


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
