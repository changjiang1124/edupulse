from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
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
    is_early_bird = models.BooleanField(
        default=False,
        verbose_name='Early Bird Enrollment',
        help_text='Whether this enrollment received early bird pricing'
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Original Course Price',
        help_text='Regular course price before early bird discount'
    )
    early_bird_savings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Early Bird Savings',
        help_text='Amount saved through early bird pricing'
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

    # Active window for attendance and class participation
    active_from = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Active From',
        help_text='Start datetime for this enrollment to apply to classes'
    )
    active_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Active Until',
        help_text='End datetime (exclusive) for this enrollment to apply to classes'
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

    def get_price_summary(self):
        """Get a summary of pricing for this enrollment"""
        summary = {
            'course_fee': self.course_fee,
            'registration_fee': self.registration_fee,
            'total_fee': self.get_total_fee(),
            'is_early_bird': self.is_early_bird,
            'price_type': 'Early Bird' if self.is_early_bird else 'Regular'
        }

        if self.is_early_bird:
            summary.update({
                'original_price': self.original_price,
                'early_bird_savings': self.early_bird_savings,
                'savings_amount': self.early_bird_savings or 0
            })

        return summary

    def update_pricing_from_course(self, enrollment_date=None):
        """Update enrollment pricing based on course pricing at enrollment time"""
        applicable_price = self.course.get_applicable_price(enrollment_date)
        is_early_bird = self.course.is_early_bird_available(enrollment_date)

        self.course_fee = applicable_price
        self.is_early_bird = is_early_bird

        if is_early_bird:
            self.original_price = self.course.price
            self.early_bird_savings = self.course.get_early_bird_savings()
        else:
            self.original_price = None
            self.early_bird_savings = None

        return self


class Attendance(models.Model):
    """
    Attendance model
    """
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('early_leave', 'Early Leave'),
        ('unmarked', 'Unmarked'),
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
        default='unmarked',
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


class MakeupSession(models.Model):
    """
    One-off makeup arrangement between a source class and a target class.

    This model is intentionally class-centric so audit exports can reliably
    connect a makeup operation back to the source course via source_class.
    """

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    REASON_CHOICES = [
        ('student_request', 'Student Request'),
        ('teacher_request', 'Teacher Request'),
        ('admin_adjustment', 'Admin Adjustment'),
    ]

    INITIATED_FROM_CHOICES = [
        ('source', 'Source Class'),
        ('target', 'Target Class'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='makeup_sessions',
        verbose_name='Student'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='makeup_sessions',
        verbose_name='Source Course'
    )
    source_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='makeup_sessions_as_source',
        verbose_name='Source Class'
    )
    target_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='makeup_sessions_as_target',
        verbose_name='Target Class'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='Status'
    )
    reason_type = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default='student_request',
        verbose_name='Reason'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )
    initiated_from = models.CharField(
        max_length=20,
        choices=INITIATED_FROM_CHOICES,
        default='source',
        verbose_name='Initiated From'
    )
    snapshot_json = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Audit Snapshot'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_makeup_sessions',
        verbose_name='Created By'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_makeup_sessions',
        verbose_name='Updated By'
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
        verbose_name = 'Makeup Session'
        verbose_name_plural = 'Makeup Sessions'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=~models.Q(source_class=models.F('target_class')),
                name='makeup_source_target_must_differ'
            ),
            models.UniqueConstraint(
                fields=['student', 'source_class', 'target_class'],
                condition=models.Q(status='scheduled'),
                name='unique_active_makeup_session'
            ),
        ]

    def __str__(self):
        return (
            f"{self.student} | {self.source_class} -> {self.target_class} "
            f"({self.get_status_display()})"
        )

    def clean(self):
        if self.source_class_id and self.target_class_id and self.source_class_id == self.target_class_id:
            raise ValidationError({'target_class': 'Source and target classes must be different.'})

        if self.source_class_id:
            source_course = self.source_class.course

            if self.course_id and self.course_id != source_course.id:
                raise ValidationError({'course': 'Course must match the source class course.'})

    def _build_snapshot(self):
        """Capture denormalised audit data to simplify future exports/import checks."""
        if not (self.student_id and self.source_class_id and self.target_class_id):
            return

        self.snapshot_json = {
            'student': {
                'id': self.student_id,
                'name': self.student.get_full_name(),
            },
            'course': {
                'id': self.source_class.course_id,
                'name': self.source_class.course.name,
            },
            'source_class': {
                'id': self.source_class_id,
                'date': self.source_class.date.isoformat(),
                'start_time': self.source_class.start_time.isoformat(),
            },
            'target_class': {
                'id': self.target_class_id,
                'date': self.target_class.date.isoformat(),
                'start_time': self.target_class.start_time.isoformat(),
            },
        }

    def save(self, *args, **kwargs):
        if self.source_class_id:
            self.course = self.source_class.course
        self.full_clean()
        self._build_snapshot()
        super().save(*args, **kwargs)
