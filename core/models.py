from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from tinymce.models import HTMLField


class Staff(AbstractUser):
    """
    员工模型 - 扩展Django内置用户模型
    包含教师和管理员角色
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
    ]
    
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Please enter a valid phone number')],
        verbose_name='Phone Number'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='teacher',
        verbose_name='Role'
    )
    is_active_staff = models.BooleanField(
        default=True,
        verbose_name='Staff Status'
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
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"


class Facility(models.Model):
    """
    设施模型 - 学校的教学设施
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Facility Name'
    )
    address = models.TextField(
        verbose_name='Address'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Contact Phone'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
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
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'
    
    def __str__(self):
        return self.name


class Classroom(models.Model):
    """
    教室模型
    """
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name='Facility'
    )
    name = models.CharField(
        max_length=50,
        verbose_name='Classroom Name/Number'
    )
    capacity = models.PositiveIntegerField(
        verbose_name='Capacity'
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
        verbose_name = 'Classroom'
        verbose_name_plural = 'Classrooms'
        unique_together = ['facility', 'name']
    
    def __str__(self):
        return f"{self.facility.name} - {self.name}"


class Student(models.Model):
    """
    学生模型
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
        """获取联系邮箱，优先学生邮箱，其次监护人邮箱"""
        return self.email or self.guardian_email
    
    def get_contact_phone(self):
        """获取联系电话，优先学生电话，其次监护人电话"""
        return self.phone or self.guardian_phone


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
        from datetime import timedelta
        from django.utils import timezone
        
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
    班级模型 - 课程的具体实例
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


class Enrollment(models.Model):
    """
    报名模型
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
    考勤模型
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


class ClockInOut(models.Model):
    """
    员工打卡模型
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
    邮件日志模型
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
    短信日志模型
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
