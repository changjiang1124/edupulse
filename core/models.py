from django.db import models
from django.utils import timezone
from accounts.models import Staff


class ClockInOut(models.Model):
    """
    Staff clock in/out model
    """
    STATUS_CHOICES = [
        ('clock_in', 'Clock In'),
        ('clock_out', 'Clock Out'),
    ]
    
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='clock_records',
        verbose_name='Staff Member'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='Clock Status'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Clock Time'
    )
    
    # GPS location record
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Latitude'
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Longitude'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    class Meta:
        verbose_name = 'Clock Record'
        verbose_name_plural = 'Clock Records'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.staff} - {self.get_status_display()} - {self.timestamp}"


class EmailLog(models.Model):
    """
    Email log model
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('welcome', 'Welcome Email'),
        ('enrollment_confirm', 'Enrolment Confirmation'),
        ('attendance_notice', 'Attendance Notice'),
        ('course_reminder', 'Course Reminder'),
    ]
    
    recipient_email = models.EmailField(
        verbose_name='Recipient Email'
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=[('student', 'Student'), ('staff', 'Staff'), ('guardian', 'Guardian')],
        verbose_name='Recipient Type'
    )
    subject = models.CharField(
        max_length=200,
        verbose_name='Email Subject'
    )
    content = models.TextField(
        verbose_name='Email Content'
    )
    email_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='Email Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name='Send Status'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Send Time'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_email} - {self.subject} ({self.get_status_display()})"


class SMSLog(models.Model):
    """
    SMS log model
    """
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('welcome', 'Welcome SMS'),
        ('enrollment_confirm', 'Enrolment Confirmation'),
        ('attendance_notice', 'Attendance Notice'),
        ('course_reminder', 'Course Reminder'),
    ]
    
    recipient_phone = models.CharField(
        max_length=20,
        verbose_name='Recipient Phone'
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=[('student', 'Student'), ('staff', 'Staff'), ('guardian', 'Guardian')],
        verbose_name='Recipient Type'
    )
    content = models.TextField(
        verbose_name='SMS Content'
    )
    sms_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='SMS Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name='Send Status'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Send Time'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'SMS Log'
        verbose_name_plural = 'SMS Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient_phone} - {self.get_sms_type_display()} ({self.get_status_display()})"
