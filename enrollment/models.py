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
    
    # Enrolment form data (JSON format for original form data)
    form_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Form Data'
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
        unique_together = ['student', 'course']
    
    def __str__(self):
        return f"{self.student} - {self.course} ({self.get_status_display()})"


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
