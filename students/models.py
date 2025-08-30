from django.db import models
from django.core.validators import RegexValidator


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
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Please enter a valid phone number')],
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
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Please enter a valid phone number')],
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
