from django.db import models
from django.core.validators import RegexValidator


class StudentTag(models.Model):
    """
    Student tag model for grouping and categorising students
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Tag Name'
    )
    colour = models.CharField(
        max_length=7,
        default='#007bff',
        verbose_name='Tag Colour',
        help_text='Hex colour code (e.g., #007bff)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active Status'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    class Meta:
        verbose_name = 'Student Tag'
        verbose_name_plural = 'Student Tags'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Student(models.Model):
    """
    Student model - Enhanced student management
    """
    # Basic Information
    first_name = models.CharField(
        max_length=50,
        verbose_name='First Name'
    )
    last_name = models.CharField(
        max_length=50,
        verbose_name='Last Name'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date of Birth'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
        verbose_name='Phone Number'
    )
    address = models.TextField(
        blank=True,
        verbose_name='Address'
    )
    
    # Guardian Information
    guardian_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Guardian Name'
    )
    guardian_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
        verbose_name='Guardian Phone'
    )
    guardian_email = models.EmailField(
        blank=True,
        verbose_name='Guardian Email'
    )
    
    # Reference Information
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference'
    )
    
    # Tags for grouping and batch operations
    tags = models.ManyToManyField(
        StudentTag,
        blank=True,
        related_name='students',
        verbose_name='Tags'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active Status'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_contact_email(self):
        """Get contact email, prioritise student email then guardian email"""
        return self.email or self.guardian_email
    
    def get_contact_phone(self):
        """Get contact phone, prioritise student phone then guardian phone"""
        return self.phone or self.guardian_phone
