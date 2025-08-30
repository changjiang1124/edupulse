from django.db import models
from django.utils import timezone
from tinymce.models import HTMLField
from datetime import timedelta
from accounts.models import Staff
from facilities.models import Facility, Classroom


class Course(models.Model):
    """
    Course model - Enhanced with status, descriptions and period management
    """
    COURSE_TYPE_CHOICES = [
        ('group', 'Group Class'),
        ('private', 'Private Lesson'),
    ]
    
    REPEAT_PATTERN_CHOICES = [
        ('once', 'Single Session'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name='Course Name'
    )
    description = HTMLField(
        blank=True,
        verbose_name='Full Description'
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Short Description',
        help_text='Brief description for WooCommerce listing'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Price'
    )
    course_type = models.CharField(
        max_length=20,
        choices=COURSE_TYPE_CHOICES,
        default='group',
        verbose_name='Course Type'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status',
        help_text='Only published courses sync to WooCommerce'
    )
    teacher = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        verbose_name='Teacher'
    )
    
    # Course schedule - enhanced for period management
    start_date = models.DateField(
        verbose_name='Start Date'
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='End Date',
        help_text='Leave blank for single session courses'
    )
    repeat_pattern = models.CharField(
        max_length=20,
        choices=REPEAT_PATTERN_CHOICES,
        default='once',
        verbose_name='Repeat Pattern'
    )
    start_time = models.TimeField(
        verbose_name='Start Time'
    )
    duration_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='Duration (minutes)'
    )
    
    # Capacity and booking
    vacancy = models.PositiveIntegerField(
        default=1,
        verbose_name='Vacancy'
    )
    is_bookable = models.BooleanField(
        default=True,
        verbose_name='Bookable'
    )
    
    # Facilities and classroom
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Facility'
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Classroom'
    )
    
    # External system ID for WooCommerce sync
    external_id = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
        verbose_name='WooCommerce Product ID'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated'
    )
    
    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def is_single_session(self):
        """Check if this is a single session course (workshop style)"""
        return self.repeat_pattern == 'once' or self.start_date == self.end_date
    
    @property
    def is_multi_session(self):
        """Check if this is a multi-session course (term style)"""
        return not self.is_single_session
    
    def get_period_display(self):
        """Get human readable period description"""
        if self.is_single_session:
            return f"Workshop on {self.start_date.strftime('%d %B %Y')}"
        else:
            end_date = self.end_date or self.start_date
            return f"Term: {self.start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}"
    
    def save(self, *args, **kwargs):
        # Auto-set end_date to start_date for single sessions
        if self.repeat_pattern == 'once' and not self.end_date:
            self.end_date = self.start_date
        super().save(*args, **kwargs)
    
    def generate_classes(self):
        """
        Generate Class instances based on course schedule
        Returns the number of classes created
        """
        if not self.pk:
            return 0
        
        # Clear existing classes for this course to regenerate
        self.classes.all().delete()
        
        classes_created = 0
        current_date = self.start_date
        end_date = self.end_date or self.start_date
        
        if self.repeat_pattern == 'once':
            # Single session
            Class.objects.create(
                course=self,
                date=current_date,
                start_time=self.start_time,
                duration_minutes=self.duration_minutes,
                teacher=self.teacher,
                facility=self.facility,
                classroom=self.classroom
            )
            classes_created = 1
        else:
            # Multi-session course
            delta_days = {
                'daily': 1,
                'weekly': 7,
                'monthly': 30,  # Approximate
            }.get(self.repeat_pattern, 7)
            
            while current_date <= end_date:
                Class.objects.create(
                    course=self,
                    date=current_date,
                    start_time=self.start_time,
                    duration_minutes=self.duration_minutes,
                    teacher=self.teacher,
                    facility=self.facility,
                    classroom=self.classroom
                )
                classes_created += 1
                current_date += timedelta(days=delta_days)
        
        return classes_created


class Class(models.Model):
    """
    Class model - Specific instance of a course
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name='Course'
    )
    date = models.DateField(
        verbose_name='Class Date'
    )
    start_time = models.TimeField(
        verbose_name='Start Time'
    )
    duration_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='Duration (minutes)'
    )
    
    # Adjustable teacher and classroom
    teacher = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Teacher'
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Facility'
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Classroom'
    )
    
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
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        unique_together = ['course', 'date', 'start_time']
    
    def __str__(self):
        return f"{self.course.name} - {self.date} {self.start_time}"
