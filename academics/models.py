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
    
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('expired', 'Expired'),
    ]
    
    BOOKABLE_STATE_CHOICES = [
        ('bookable', 'Bookable'),
        ('fully_booked', 'Fully Booked'),
        ('closed', 'Closed'),
    ]
    
    CATEGORY_CHOICES = [
        ('term_courses', 'Term Courses'),
        ('holiday_program', 'Holiday Program'),
        ('day_courses', 'Day Courses'),
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
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='term_courses',
        verbose_name='Category',
        help_text='Course category for organization and WooCommerce sync'
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
    
    # Repeat configuration fields
    repeat_weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        verbose_name='Weekday',
        help_text='Day of the week for weekly courses (auto-filled from start date)'
    )
    repeat_day_of_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Day of Month',
        help_text='Day of the month for monthly courses (1-31, auto-filled from start date)'
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
    is_online_bookable = models.BooleanField(
        default=True,
        verbose_name='Allow Online Bookings',
        help_text='Enable students to enroll in this course through the online form'
    )
    bookable_state = models.CharField(
        max_length=20,
        choices=BOOKABLE_STATE_CHOICES,
        default='bookable',
        verbose_name='Bookable State',
        help_text='Current booking availability status'
    )
    enrollment_deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name='Enrollment Deadline',
        help_text='Last date to accept enrollments (leave blank for no deadline)'
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
    
    # Course featured image for WooCommerce product display
    featured_image = models.ImageField(
        upload_to='course_images/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Featured Image',
        help_text='Main image for course display and WooCommerce product'
    )
    
    # External system ID for WooCommerce sync
    external_id = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
        verbose_name='WooCommerce Product ID'
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
    
    def get_duration_display(self):
        """
        Return human-friendly duration format
        """
        if self.duration_minutes:
            hours = self.duration_minutes // 60
            minutes = self.duration_minutes % 60
            
            if hours == 0:
                return f"{minutes} minutes"
            elif minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minutes"
        return "Duration not set"
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to auto-set repeat configuration"""
        # Handle empty string values from forms
        if self.repeat_weekday == '':
            self.repeat_weekday = None
        if self.repeat_day_of_month == '':
            self.repeat_day_of_month = None
            
        if self.start_date:
            # Auto-set weekday for weekly courses
            if self.repeat_pattern == 'weekly' and not self.repeat_weekday:
                self.repeat_weekday = self.start_date.weekday()
            
            # Auto-set day of month for monthly courses
            if self.repeat_pattern == 'monthly' and not self.repeat_day_of_month:
                self.repeat_day_of_month = self.start_date.day
            
            # Clear repeat configurations for non-applicable patterns
            if self.repeat_pattern in ['once', 'daily']:
                self.repeat_weekday = None
                self.repeat_day_of_month = None
            elif self.repeat_pattern == 'weekly':
                self.repeat_day_of_month = None
            elif self.repeat_pattern == 'monthly':
                self.repeat_weekday = None
                
        super().save(*args, **kwargs)
    
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
        from datetime import timedelta
        import calendar
        
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
        elif self.repeat_pattern == 'daily':
            # Daily classes
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
                current_date += timedelta(days=1)
        elif self.repeat_pattern == 'weekly':
            # Weekly classes - use specific weekday
            if self.repeat_weekday is not None:
                # Find the first occurrence of the specified weekday on or after start_date
                days_ahead = self.repeat_weekday - current_date.weekday()
                if days_ahead < 0:  # Target day already happened this week
                    days_ahead += 7
                current_date += timedelta(days_ahead)
                
                # Generate classes weekly on the specified day
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
                    current_date += timedelta(days=7)
        elif self.repeat_pattern == 'monthly':
            # Monthly classes - use specific day of month
            if self.repeat_day_of_month is not None:
                # Start from the specified day of the start month
                if current_date.day <= self.repeat_day_of_month:
                    # This month, on the specified day
                    try:
                        current_date = current_date.replace(day=self.repeat_day_of_month)
                    except ValueError:
                        # Day doesn't exist in this month (e.g., Feb 31), skip to next month
                        next_month = current_date.replace(day=1) + timedelta(days=32)
                        try:
                            current_date = next_month.replace(day=self.repeat_day_of_month, month=next_month.month, year=next_month.year)
                        except ValueError:
                            current_date = next_month.replace(day=1) + timedelta(days=32)
                            current_date = current_date.replace(day=min(self.repeat_day_of_month, calendar.monthrange(current_date.year, current_date.month)[1]))
                else:
                    # Next month, on the specified day
                    next_month = current_date.replace(day=1) + timedelta(days=32)
                    try:
                        current_date = next_month.replace(day=self.repeat_day_of_month, month=next_month.month, year=next_month.year)
                    except ValueError:
                        current_date = next_month.replace(day=min(self.repeat_day_of_month, calendar.monthrange(next_month.year, next_month.month)[1]))
                
                # Generate monthly classes
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
                    
                    # Move to next month
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    
                    try:
                        current_date = next_month.replace(day=self.repeat_day_of_month)
                    except ValueError:
                        # Day doesn't exist in next month
                        current_date = next_month.replace(day=min(self.repeat_day_of_month, calendar.monthrange(next_month.year, next_month.month)[1]))
        
        return classes_created
    
    def get_repeat_config_display(self):
        """Get display text for repeat configuration"""
        if self.repeat_pattern == 'weekly' and self.repeat_weekday is not None:
            weekday_name = dict(self.WEEKDAY_CHOICES)[self.repeat_weekday]
            return f"Every {weekday_name}"
        elif self.repeat_pattern == 'monthly' and self.repeat_day_of_month is not None:
            day_suffix = 'th'
            if self.repeat_day_of_month in [1, 21, 31]:
                day_suffix = 'st'
            elif self.repeat_day_of_month in [2, 22]:
                day_suffix = 'nd'
            elif self.repeat_day_of_month in [3, 23]:
                day_suffix = 'rd'
            return f"Every {self.repeat_day_of_month}{day_suffix} of the month"
        elif self.repeat_pattern == 'daily':
            return "Every day"
        elif self.repeat_pattern == 'once':
            return "Single session"
        return self.get_repeat_pattern_display()
    
    def get_current_status(self):
        """Calculate current course status based on dates"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.status == 'draft':
            return 'draft'
        elif self.status == 'published':
            # Check if course has expired (past end date)
            end_date = self.end_date or self.start_date
            if end_date < today:
                return 'expired'
            return 'published'
        return self.status
    
    def get_current_bookable_state(self):
        """Calculate current bookable state based on enrollments and conditions"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Check if enrollment deadline has passed
        if self.enrollment_deadline and self.enrollment_deadline < today:
            return 'closed'
        
        # Check if course has expired
        end_date = self.end_date or self.start_date
        if end_date < today:
            return 'closed'
        
        # Check if course is published and online bookable
        if self.status != 'published' or not self.is_online_bookable:
            return 'closed'
        
        # Check enrollment count vs vacancy
        try:
            from enrollment.models import Enrollment
            confirmed_enrollments = Enrollment.objects.filter(
                course=self,
                status='confirmed'
            ).count()
            
            if confirmed_enrollments >= self.vacancy:
                return 'fully_booked'
        except ImportError:
            # If enrollment app not available, just check base conditions
            pass
        
        return 'bookable'
    
    def update_computed_fields(self):
        """Update computed status fields"""
        current_status = self.get_current_status()
        current_bookable_state = self.get_current_bookable_state()
        
        # Only update if changed to avoid unnecessary saves
        updated = False
        if self.status != current_status and current_status == 'expired':
            self.status = current_status
            updated = True
        
        if self.bookable_state != current_bookable_state:
            self.bookable_state = current_bookable_state
            updated = True
        
        if updated:
            self.save(update_fields=['status', 'bookable_state'])
        
        return updated


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
    
    def get_duration_display(self):
        """
        Return human-friendly duration format
        """
        if self.duration_minutes:
            hours = self.duration_minutes // 60
            minutes = self.duration_minutes % 60
            
            if hours == 0:
                return f"{minutes} min" if minutes < 60 else f"{minutes} minutes"
            elif minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h {minutes}m"
        return "TBD"
    
    def __str__(self):
        return f"{self.course.name} - {self.date} {self.start_time}"
