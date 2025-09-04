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
    address = models.TextField(
        blank=True,
        verbose_name='Address'
    )
    
    # Primary Contact Information (from enrollment form)
    primary_contact_email = models.EmailField(
        blank=True,
        verbose_name='Primary Contact Email',
        help_text='Main email address for course communications'
    )
    primary_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
        verbose_name='Primary Contact Phone',
        help_text='Main phone number for SMS notifications'
    )
    primary_contact_type = models.CharField(
        max_length=20,
        choices=[('student', 'Student'), ('guardian', 'Guardian')],
        default='student',
        verbose_name='Primary Contact Type',
        help_text='Indicates if primary contact is the student or guardian'
    )
    
    # Detailed Contact Information (for internal management)
    email = models.EmailField(
        blank=True,
        verbose_name='Student Personal Email'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
        verbose_name='Student Personal Phone'
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
    
    # Emergency Contact Information
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Emergency Contact Name'
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
        verbose_name='Emergency Contact Phone'
    )
    
    # Medical and Special Requirements
    medical_conditions = models.TextField(
        blank=True,
        verbose_name='Medical Conditions',
        help_text='Any medical conditions we should be aware of'
    )
    special_requirements = models.TextField(
        blank=True,
        verbose_name='Special Requirements',
        help_text='Any special requirements or accommodations needed'
    )
    
    # Reference Information
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference'
    )
    
    # Student Status and Management
    registration_status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Student'),
            ('returning', 'Returning Student'),
            ('transferred', 'Transferred')
        ],
        default='new',
        verbose_name='Registration Status'
    )
    
    # Staff Management Fields (not shown to public)
    staff_notes = models.TextField(
        blank=True,
        verbose_name='Staff Notes',
        help_text='Internal notes for staff/teachers only'
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name='Internal Notes',
        help_text='System internal notes and history'
    )
    enrollment_source = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Enrollment Source',
        help_text='Where/how the student enrolled'
    )
    
    # Source tracking
    source_enrollment = models.OneToOneField(
        'enrollment.Enrollment',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_student',
        verbose_name='Source Enrollment',
        help_text='The enrollment record that created this student'
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
        """Get primary contact email with fallback logic"""
        return self.primary_contact_email or self.email or self.guardian_email
    
    def get_contact_phone(self):
        """Get primary contact phone with fallback logic"""
        return self.primary_contact_phone or self.phone or self.guardian_phone
    
    def get_age(self):
        """Calculate student's current age"""
        if self.birth_date:
            from datetime import date
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None
    
    def is_minor(self):
        """Check if student is under 18"""
        age = self.get_age()
        return age is not None and age < 18
    
    def get_full_name(self):
        """Get student's full name"""
        return f"{self.first_name} {self.last_name}"
