from django.contrib import admin
from .models import Student, StudentTag


@admin.register(StudentTag)
class StudentTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'colour', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Tag Information', {
            'fields': ('name', 'colour', 'description', 'is_active')
        }),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'guardian_name', 'get_tags', 'is_active', 'created_at')
    list_filter = ('is_active', 'tags', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'guardian_name', 'guardian_email')
    ordering = ('last_name', 'first_name')
    filter_horizontal = ('tags',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'birth_date', 'email', 'phone', 'address')
        }),
        ('Guardian Information', {
            'fields': ('guardian_name', 'guardian_phone', 'guardian_email')
        }),
        ('Tags and Classification', {
            'fields': ('tags',)
        }),
        ('Additional Info', {
            'fields': ('reference', 'is_active')
        })
    )
    
    def get_tags(self, obj):
        return ', '.join([tag.name for tag in obj.tags.all()[:3]])
    get_tags.short_description = 'Tags'
