from django.db import models
from django.utils import timezone
from students.models import Student
from academics.models import Course, Class


class Enrollment(models.Model):
    """
    Enrollment model
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('form', 'Enrolment Form'),
        ('staff', 'Staff Member'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Student'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Course'
    )
    class_instance = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Class',
        blank=True,
        null=True,
        help_text='Optional: specific class instance for this enrollment'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    source_channel = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='website',
        verbose_name='Enrolment Source'
    )
    
    # Registration status for this specific enrollment
    registration_status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Student'),
            ('returning', 'Returning Student'),
            ('transferred', 'Transferred Student')
        ],
        default='new',
        verbose_name='Registration Status',
        help_text='Student status for this specific enrollment'
    )
    
    # Enrolment form data (JSON format for original form data)
    form_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Form Data'
    )
    
    # Fee Management
    course_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Course Fee',
        help_text='Fee for the course at time of enrollment'
    )
    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Registration Fee',
        help_text='Registration fee for new students'
    )
    registration_fee_paid = models.BooleanField(
        default=False,
        verbose_name='Registration Fee Paid'
    )
    
    # Student Identification
    is_new_student = models.BooleanField(
        default=True,
        verbose_name='Is New Student',
        help_text='Whether student was new at time of enrollment'
    )
    matched_existing_student = models.BooleanField(
        default=False,
        verbose_name='Matched Existing Student',
        help_text='Whether an existing student was matched during enrollment'
    )
    
    # Original form data preservation
    original_form_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Original Form Data',
        help_text='Backup of original enrollment form data for audit purposes'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Enrolment Date'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Enrolment'
        verbose_name_plural = 'Enrolments'
        # Support both course-level and class-level unique constraints
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                condition=models.Q(class_instance__isnull=True),
                name='unique_student_course_enrollment'
            ),
            models.UniqueConstraint(
                fields=['student', 'class_instance'],
                condition=models.Q(class_instance__isnull=False),
                name='unique_student_class_enrollment'
            ),
        ]
    
    def __str__(self):
        base_str = f"{self.student} - {self.course}"
        if self.class_instance:
            base_str += f" ({self.class_instance})"
        return f"{base_str} ({self.get_status_display()})"
    
    def get_total_fee(self):
        """Calculate total fee for this enrollment"""
        return self.course_fee + self.registration_fee
    
    def get_outstanding_fee(self):
        """Calculate outstanding fee amount"""
        outstanding = self.course_fee  # Course fee always outstanding until separately tracked
        if not self.registration_fee_paid:
            outstanding += self.registration_fee
        return outstanding
    
    def is_fully_paid(self):
        """Check if all fees are paid (currently only tracks registration fee)"""
        # Note: Course fee payment would need separate tracking
        return self.registration_fee_paid or self.registration_fee == 0
    
    def get_reference_id(self):
        """
        Generate professional reference ID in format PAS-[courseID:3digits]-[enrollmentID:3digits]
        
        Examples:
        - PAS-001-023 (Course ID 1, Enrollment ID 23)
        - PAS-042-156 (Course ID 42, Enrollment ID 156)
        """
        return f"PAS-{self.course.id:03d}-{self.id:03d}"


class Attendance(models.Model):
    """
    Attendance model
    """
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('early_leave', 'Early Leave'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Student'
    )
    class_instance = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Class'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='present',
        verbose_name='Attendance Status'
    )
    attendance_time = models.DateTimeField(
        default=timezone.now,
        verbose_name='Attendance Time'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Record Time'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        unique_together = ['student', 'class_instance']
    
    def __str__(self):
        return f"{self.student} - {self.class_instance} ({self.get_status_display()})"
