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
    
    # Contact Information (unified as per enrollment form logic)
    contact_email = models.EmailField(
        blank=True,
        verbose_name='Contact Email',
        help_text='Primary email address for communications (student or guardian depending on age)'
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
        verbose_name='Contact Phone',
        help_text='Primary phone number for SMS notifications (student or guardian depending on age)'
    )
    
    # Guardian Information (for students under 18)
    guardian_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Guardian Name'
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
    # Staff Management Fields (not shown to public)
    # Note: registration_status field has been moved to Enrollment model
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
        """Get primary contact email (student or guardian based on age)"""
        return self.contact_email
    
    def get_contact_phone(self):
        """Get primary contact phone (student or guardian based on age)"""
        return self.contact_phone
    
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


class StudentActivity(models.Model):
    """
    Student Activity model for tracking enrollment and other student-related activities
    """
    ACTIVITY_TYPES = [
        ('enrollment_created', 'Enrollment Created'),
        ('enrollment_confirmed', 'Enrollment Confirmed'),
        ('enrollment_cancelled', 'Enrollment Cancelled'),
        ('attendance_marked', 'Attendance Marked'),
        ('payment_received', 'Payment Received'),
        ('course_completed', 'Course Completed'),
        ('contact_updated', 'Contact Information Updated'),
        ('notes_added', 'Staff Notes Added'),
        ('email_sent', 'Email Sent'),
        ('sms_sent', 'SMS Sent'),
        ('other', 'Other Activity')
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='Student'
    )
    
    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPES,
        verbose_name='Activity Type'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='Activity Title',
        help_text='Brief description of the activity'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Detailed description of the activity'
    )
    
    # Related objects (optional foreign keys for context)
    enrollment = models.ForeignKey(
        'enrollment.Enrollment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name='Related Enrollment'
    )
    
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_activities',
        verbose_name='Related Course'
    )
    
    # Staff member who performed the activity (if applicable)
    performed_by = models.ForeignKey(
        'accounts.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_activities',
        verbose_name='Performed By'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Additional Data',
        help_text='JSON field for storing additional activity-specific data'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    is_visible_to_student = models.BooleanField(
        default=True,
        verbose_name='Visible to Student/Guardian',
        help_text='Whether this activity should be visible in student portal'
    )
    
    class Meta:
        verbose_name = 'Student Activity'
        verbose_name_plural = 'Student Activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.get_activity_type_display()}"
    
    def get_activity_icon(self):
        """Get FontAwesome icon for activity type"""
        icon_map = {
            'enrollment_created': 'fa-user-plus',
            'enrollment_confirmed': 'fa-check-circle',
            'enrollment_cancelled': 'fa-times-circle',
            'attendance_marked': 'fa-check-square',
            'payment_received': 'fa-dollar-sign',
            'course_completed': 'fa-graduation-cap',
            'contact_updated': 'fa-address-book',
            'notes_added': 'fa-sticky-note',
            'email_sent': 'fa-envelope',
            'sms_sent': 'fa-sms',
            'other': 'fa-info-circle'
        }
        return icon_map.get(self.activity_type, 'fa-info-circle')
    
    def get_activity_color(self):
        """Get Bootstrap color class for activity type"""
        color_map = {
            'enrollment_created': 'primary',
            'enrollment_confirmed': 'success',
            'enrollment_cancelled': 'danger',
            'attendance_marked': 'info',
            'payment_received': 'success',
            'course_completed': 'warning',
            'contact_updated': 'secondary',
            'notes_added': 'secondary',
            'email_sent': 'info',
            'sms_sent': 'info',
            'other': 'secondary'
        }
        return color_map.get(self.activity_type, 'secondary')
    
    @classmethod
    def create_activity(cls, student, activity_type, title, description=None, **kwargs):
        """
        Helper method to create student activities
        """
        return cls.objects.create(
            student=student,
            activity_type=activity_type,
            title=title,
            description=description or '',
            **kwargs
        )
