from django.contrib import admin
from .models import Facility, Classroom


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
