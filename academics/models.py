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
        verbose_name='Course Fee'
    )
    early_bird_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Early Bird Price',
        help_text='Special price for early enrollments. Must be lower than regular course fee.'
    )
    early_bird_deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name='Early Bird Deadline',
        help_text='Last date to enjoy early bird pricing. Must be before course start date.'
    )
    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        verbose_name='Registration Fee',
        help_text='Additional fee for new student registration. Leave blank if no registration fee required.'
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
        default='weekly',
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
    daily_weekdays = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Daily Weekdays',
        help_text='Days of the week for daily courses (list of weekday numbers)',
        default=list
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
                self.daily_weekdays = None
            elif self.repeat_pattern == 'monthly':
                self.repeat_weekday = None
                self.daily_weekdays = None

            # Handle daily_weekdays for daily pattern
            if self.repeat_pattern == 'daily':
                # If daily_weekdays is empty, set default to weekdays (Mon-Fri)
                if not self.daily_weekdays:
                    self.daily_weekdays = [0, 1, 2, 3, 4]  # Mon-Fri
            else:
                # Clear daily_weekdays for non-daily patterns
                self.daily_weekdays = None
                
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
    
    def get_total_cost_for_new_student(self, enrollment_date=None):
        """Calculate total cost including registration fee for new students"""
        applicable_price = self.get_applicable_price(enrollment_date)
        return applicable_price + (self.registration_fee or 0)

    def get_total_cost_for_existing_student(self, enrollment_date=None):
        """Calculate total cost excluding registration fee for existing students"""
        return self.get_applicable_price(enrollment_date)
    
    def has_registration_fee(self):
        """Check if course has a registration fee"""
        return self.registration_fee and self.registration_fee > 0

    def has_early_bird_pricing(self):
        """Check if course has early bird pricing configured"""
        return self.early_bird_price is not None and self.early_bird_deadline is not None

    def is_early_bird_available(self, enrollment_date=None):
        """Check if early bird pricing is currently available"""
        if not self.has_early_bird_pricing():
            return False

        from django.utils import timezone
        check_date = enrollment_date or timezone.now().date()
        return check_date <= self.early_bird_deadline

    def get_applicable_price(self, enrollment_date=None):
        """Get the applicable price for enrollment on a given date"""
        if self.is_early_bird_available(enrollment_date):
            return self.early_bird_price
        return self.price

    def get_price_type(self, enrollment_date=None):
        """Get the type of price applicable for enrollment"""
        if self.is_early_bird_available(enrollment_date):
            return 'early_bird'
        return 'regular'

    def get_early_bird_savings(self):
        """Calculate savings from early bird pricing"""
        if not self.has_early_bird_pricing():
            return 0
        return self.price - self.early_bird_price
    
    def schedule_display(self):
        """Return formatted schedule information for display"""
        if self.is_single_session:
            return f"{self.start_date.strftime('%A, %d %B %Y')} at {self.start_time.strftime('%I:%M %p')}"
        else:
            weekday_name = dict(self.WEEKDAY_CHOICES).get(self.repeat_weekday, '')
            if self.repeat_pattern == 'weekly' and weekday_name:
                return f"Every {weekday_name} at {self.start_time.strftime('%I:%M %p')}"
            elif self.repeat_pattern == 'daily':
                if self.daily_weekdays:
                    weekday_names = [dict(self.WEEKDAY_CHOICES)[wd] for wd in self.daily_weekdays]
                    if len(weekday_names) == 7:
                        return f"Daily at {self.start_time.strftime('%I:%M %p')}"
                    elif weekday_names == ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                        return f"Weekdays at {self.start_time.strftime('%I:%M %p')}"
                    else:
                        days_str = ", ".join(weekday_names)
                        return f"Daily ({days_str}) at {self.start_time.strftime('%I:%M %p')}"
                else:
                    return f"Daily at {self.start_time.strftime('%I:%M %p')}"
            elif self.repeat_pattern == 'monthly' and self.repeat_day_of_month:
                return f"Monthly on the {self.repeat_day_of_month}{self._get_ordinal_suffix(self.repeat_day_of_month)} at {self.start_time.strftime('%I:%M %p')}"
            else:
                return f"{self.start_time.strftime('%I:%M %p')}"
    
    def location_display(self):
        """Return formatted location information for display"""
        if self.classroom and self.facility:
            return f"{self.classroom.name}, {self.facility.name}"
        elif self.facility:
            return self.facility.name
        elif self.classroom:
            return f"{self.classroom.name}, {self.classroom.facility.name if self.classroom.facility else 'Unknown Facility'}"
        else:
            return "Location to be confirmed"
    
    def _get_ordinal_suffix(self, day):
        """Helper method to get ordinal suffix for day numbers"""
        if 10 <= day % 100 <= 20:
            return 'th'
        else:
            return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    def clean(self):
        """Validate Course model data"""
        from django.core.exceptions import ValidationError

        # Validate facility-classroom matching
        if self.facility and self.classroom:
            if self.classroom.facility != self.facility:
                raise ValidationError({
                    'classroom': f'Classroom "{self.classroom.name}" belongs to facility "{self.classroom.facility.name}" '
                               f'but course is assigned to facility "{self.facility.name}". '
                               f'Please ensure classroom and facility match.'
                })

        # Auto-assign facility if only classroom is provided
        elif self.classroom and not self.facility:
            self.facility = self.classroom.facility

        # Validate early bird pricing
        if self.early_bird_price is not None:
            if self.early_bird_price >= self.price:
                raise ValidationError({
                    'early_bird_price': 'Early bird price must be lower than the regular course fee.'
                })

            if not self.early_bird_deadline:
                raise ValidationError({
                    'early_bird_deadline': 'Early bird deadline is required when early bird price is set.'
                })

        if self.early_bird_deadline:
            if not self.early_bird_price:
                raise ValidationError({
                    'early_bird_price': 'Early bird price is required when early bird deadline is set.'
                })

            if self.start_date and self.early_bird_deadline >= self.start_date:
                raise ValidationError({
                    'early_bird_deadline': 'Early bird deadline must be before the course start date.'
                })
    
    def save(self, *args, **kwargs):
        """Enhanced save method with automatic status management"""
        from django.utils import timezone
        
        # Auto-set end_date to start_date for single sessions
        if self.repeat_pattern == 'once' and not self.end_date:
            self.end_date = self.start_date
        
        # Automatic status update based on dates
        if self.status == 'published' and hasattr(self, '_skip_auto_status_update'):
            # Skip auto-update if explicitly requested (for admin overrides)
            pass
        elif self.status == 'published':
            # Check if course should be expired
            end_date = self.end_date or self.start_date
            today = timezone.now().date()
            
            if end_date < today:
                self.status = 'expired'
                # Log status change for debugging
                print(f"Auto-expired course: {self.name} (end date: {end_date})")
        
        super().save(*args, **kwargs)
    
    def _iter_schedule_dates(self):
        """Yield scheduled class dates based on course configuration."""
        from datetime import timedelta, date as date_cls
        import calendar

        if not self.start_date:
            return

        current_date = self.start_date
        end_date = self.end_date or self.start_date

        if end_date < current_date:
            end_date = current_date

        if self.repeat_pattern == 'once':
            yield current_date
            return

        if self.repeat_pattern == 'daily':
            allowed_weekdays = self.daily_weekdays or [0, 1, 2, 3, 4, 5, 6]
            while current_date <= end_date:
                if current_date.weekday() in allowed_weekdays:
                    yield current_date
                current_date += timedelta(days=1)
            return

        if self.repeat_pattern == 'weekly':
            target_weekday = self.repeat_weekday if self.repeat_weekday is not None else current_date.weekday()
            days_ahead = target_weekday - current_date.weekday()
            if days_ahead < 0:
                days_ahead += 7
            current_date += timedelta(days=days_ahead)
            while current_date <= end_date:
                yield current_date
                current_date += timedelta(days=7)
            return

        if self.repeat_pattern == 'monthly':
            target_day = self.repeat_day_of_month or current_date.day

            def clamp_day(year, month):
                return min(target_day, calendar.monthrange(year, month)[1])

            year = current_date.year
            month = current_date.month
            day = clamp_day(year, month)
            candidate = date_cls(year, month, day)

            if candidate < current_date:
                # move to next month if the initial candidate is before the start
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                day = clamp_day(year, month)
                candidate = date_cls(year, month, day)

            while candidate <= end_date:
                yield candidate
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                day = clamp_day(year, month)
                candidate = date_cls(year, month, day)

    def generate_classes(self, replace_existing=True):
        """Generate Class instances based on course schedule.

        When ``replace_existing`` is True (default), existing classes are deleted before
        regeneration (behaviour used when creating a course). When False, the schedule
        is applied non-destructively and new classes are appended without touching
        existing ones.
        """
        if not self.pk or not self.start_date or not self.start_time:
            return 0

        schedule_dates = list(self._iter_schedule_dates() or [])

        if replace_existing:
            self.classes.all().delete()
            existing_keys = set()
        else:
            existing_keys = set(self.classes.values_list('date', 'start_time'))

        classes_created = 0

        for class_date in schedule_dates:
            key = (class_date, self.start_time)
            if key in existing_keys:
                continue

            Class.objects.create(
                course=self,
                date=class_date,
                start_time=self.start_time,
                duration_minutes=self.duration_minutes,
                teacher=self.teacher,
                facility=self.facility,
                classroom=self.classroom
            )
            classes_created += 1
            existing_keys.add(key)

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
            if self.daily_weekdays:
                weekday_names = [dict(self.WEEKDAY_CHOICES)[wd] for wd in self.daily_weekdays]
                if len(weekday_names) == 7:
                    return "Every day"
                elif weekday_names == ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                    return "Every weekday"
                else:
                    days_str = ", ".join(weekday_names)
                    return f"Daily ({days_str})"
            else:
                return "Every day"
        elif self.repeat_pattern == 'once':
            return "Single session"
        return self.get_repeat_pattern_display()
    
    
    def get_price_breakdown(self, enrollment_date=None):
        """Get price breakdown with GST calculations using applicable price"""
        from core.models import OrganisationSettings
        from decimal import Decimal, ROUND_HALF_UP

        settings = OrganisationSettings.get_instance()
        applicable_price = self.get_applicable_price(enrollment_date)

        if settings.prices_include_gst:
            # Database price is inclusive of GST
            price_inc_gst = applicable_price
            gst_amount = price_inc_gst / (1 + settings.gst_rate) * settings.gst_rate
            price_ex_gst = price_inc_gst - gst_amount
        else:
            # Database price is exclusive of GST
            price_ex_gst = applicable_price
            gst_amount = price_ex_gst * settings.gst_rate
            price_inc_gst = price_ex_gst + gst_amount

        # Round to 2 decimal places
        price_ex_gst = price_ex_gst.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        gst_amount = gst_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        price_inc_gst = price_inc_gst.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'stored_price': self.price,  # Original price
            'applicable_price': applicable_price,  # Current applicable price
            'price_ex_gst': price_ex_gst,
            'gst_amount': gst_amount,
            'price_inc_gst': price_inc_gst,
            'display_price': applicable_price,
            'includes_gst': settings.prices_include_gst,
            'gst_rate': settings.gst_rate,
            'gst_label': settings.gst_label,
            'is_early_bird': self.is_early_bird_available(enrollment_date),
            'price_type': self.get_price_type(enrollment_date),
            'early_bird_savings': self.get_early_bird_savings() if self.is_early_bird_available(enrollment_date) else None
        }
    
    def get_registration_fee_breakdown(self):
        """Get registration fee breakdown with GST calculations"""
        if not self.registration_fee:
            return None
            
        from core.models import OrganisationSettings
        from decimal import Decimal, ROUND_HALF_UP
        
        settings = OrganisationSettings.get_instance()
        
        if settings.prices_include_gst:
            # Database price is inclusive of GST
            price_inc_gst = self.registration_fee
            gst_amount = price_inc_gst / (1 + settings.gst_rate) * settings.gst_rate
            price_ex_gst = price_inc_gst - gst_amount
        else:
            # Database price is exclusive of GST
            price_ex_gst = self.registration_fee
            gst_amount = price_ex_gst * settings.gst_rate
            price_inc_gst = price_ex_gst + gst_amount
        
        # Round to 2 decimal places
        price_ex_gst = price_ex_gst.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        gst_amount = gst_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        price_inc_gst = price_inc_gst.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'stored_price': self.registration_fee,
            'price_ex_gst': price_ex_gst,
            'gst_amount': gst_amount,
            'price_inc_gst': price_inc_gst,
            'display_price': self.registration_fee,
            'includes_gst': settings.prices_include_gst,
            'gst_rate': settings.gst_rate,
            'gst_label': settings.gst_label
        }
    
    def get_price_display(self, show_gst_label=True, enrollment_date=None, show_early_bird_info=True):
        """Get formatted price display with GST label and early bird information"""
        from core.models import OrganisationSettings

        settings = OrganisationSettings.get_instance()
        applicable_price = self.get_applicable_price(enrollment_date)
        is_early_bird = self.is_early_bird_available(enrollment_date)

        formatted_price = f"${applicable_price:,.2f}"

        if show_gst_label:
            gst_label = " (inc GST)" if settings.prices_include_gst else " (ex GST)"
            formatted_price += gst_label

        # Add early bird information if applicable and requested
        if show_early_bird_info and is_early_bird:
            savings = self.get_early_bird_savings()
            formatted_price += f" Early Bird (Save ${savings:,.2f}!)"

        return formatted_price

    def get_price_comparison_display(self):
        """Get price comparison display showing both regular and early bird prices"""
        if not self.has_early_bird_pricing():
            return self.get_price_display()

        from core.models import OrganisationSettings
        settings = OrganisationSettings.get_instance()
        gst_label = " (inc GST)" if settings.prices_include_gst else " (ex GST)"

        early_bird_price = f"${self.early_bird_price:,.2f}{gst_label}"
        regular_price = f"${self.price:,.2f}{gst_label}"
        savings = self.get_early_bird_savings()

        return {
            'early_bird_price': early_bird_price,
            'regular_price': regular_price,
            'savings': f"${savings:,.2f}",
            'deadline': self.early_bird_deadline
        }
    
    def get_total_course_fee_breakdown(self, enrollment_date=None):
        """Get total course fee including registration fee with GST breakdown"""
        from decimal import Decimal

        course_breakdown = self.get_price_breakdown(enrollment_date)
        total_breakdown = {
            'course_fee_ex_gst': course_breakdown['price_ex_gst'],
            'course_fee_gst': course_breakdown['gst_amount'],
            'course_fee_inc_gst': course_breakdown['price_inc_gst'],
            'registration_fee_ex_gst': Decimal('0.00'),
            'registration_fee_gst': Decimal('0.00'),
            'registration_fee_inc_gst': Decimal('0.00'),
            'total_ex_gst': course_breakdown['price_ex_gst'],
            'total_gst': course_breakdown['gst_amount'],
            'total_inc_gst': course_breakdown['price_inc_gst'],
            'includes_gst': course_breakdown['includes_gst'],
            'gst_rate': course_breakdown['gst_rate'],
            'gst_label': course_breakdown['gst_label'],
            'is_early_bird': course_breakdown.get('is_early_bird', False),
            'price_type': course_breakdown.get('price_type', 'regular'),
            'early_bird_savings': course_breakdown.get('early_bird_savings')
        }

        # Add registration fee if exists
        if self.registration_fee:
            reg_breakdown = self.get_registration_fee_breakdown()
            total_breakdown.update({
                'registration_fee_ex_gst': reg_breakdown['price_ex_gst'],
                'registration_fee_gst': reg_breakdown['gst_amount'],
                'registration_fee_inc_gst': reg_breakdown['price_inc_gst'],
                'total_ex_gst': course_breakdown['price_ex_gst'] + reg_breakdown['price_ex_gst'],
                'total_gst': course_breakdown['gst_amount'] + reg_breakdown['gst_amount'],
                'total_inc_gst': course_breakdown['price_inc_gst'] + reg_breakdown['price_inc_gst']
            })

        return total_breakdown


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
    
    def get_class_datetime(self):
        """
        Return a datetime object combining class date and start time
        """
        from django.utils import timezone
        import datetime
        
        # Combine date and time
        naive_datetime = datetime.datetime.combine(self.date, self.start_time)
        
        # Make it timezone aware
        return timezone.make_aware(naive_datetime)
    
    def clean(self):
        """Validate Class model data"""
        from django.core.exceptions import ValidationError
        
        # Validate facility-classroom matching
        if self.facility and self.classroom:
            if self.classroom.facility != self.facility:
                raise ValidationError({
                    'classroom': f'Classroom "{self.classroom.name}" belongs to facility "{self.classroom.facility.name}" '
                               f'but class is assigned to facility "{self.facility.name}". '
                               f'Please ensure classroom and facility match.'
                })
        
        # Auto-assign facility if only classroom is provided
        elif self.classroom and not self.facility:
            self.facility = self.classroom.facility
    
    def __str__(self):
        return f"{self.course.name} - {self.date} {self.start_time}"
