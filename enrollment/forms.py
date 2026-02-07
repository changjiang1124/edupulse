from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Enrollment, Attendance
from students.models import Student
from academics.models import Course, Class
from .services import AttendanceRosterService, MakeupSessionService


class EnrollmentForm(forms.ModelForm):
    """Enrollment form with Bootstrap styling"""
    
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'class_instance', 'status', 'source_channel']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select select2-searchable'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select select2-searchable'
            }),
            'class_instance': forms.Select(attrs={
                'class': 'form-select select2-searchable'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'source_channel': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')
        class_instance = cleaned_data.get('class_instance')
        
        # Check for duplicate active enrollments (excluding cancelled)
        if student:
            existing_enrollment = None
            
            if class_instance:
                # Check for class-level duplicates
                existing_enrollment = Enrollment.objects.filter(
                    student=student,
                    class_instance=class_instance
                ).exclude(status='cancelled')
                
                error_msg = (
                    f'{student.get_full_name()} already has an active enrollment in {class_instance}. '
                    f'Current status: {{status}}. '
                    f'Please cancel the existing enrollment before creating a new one.'
                )
            elif course:
                # Check for course-level duplicates (only when no specific class is selected)
                existing_enrollment = Enrollment.objects.filter(
                    student=student,
                    course=course,
                    class_instance__isnull=True  # Only check course-level enrollments
                ).exclude(status='cancelled')
                
                error_msg = (
                    f'{student.get_full_name()} already has an active enrollment in {course.name}. '
                    f'Current status: {{status}}. '
                    f'Please cancel the existing enrollment before creating a new one.'
                )
            
            # For updates, exclude current instance
            if existing_enrollment and self.instance and self.instance.pk:
                existing_enrollment = existing_enrollment.exclude(pk=self.instance.pk)
                
            if existing_enrollment and existing_enrollment.exists():
                existing = existing_enrollment.first()
                raise forms.ValidationError(
                    error_msg.format(status=existing.get_status_display())
                )
        
        return cleaned_data


class EnrollmentUpdateForm(forms.ModelForm):
    """Enhanced enrollment update form with comprehensive student information and email control"""

    # Email notification control for updates
    send_update_notification = forms.BooleanField(
        required=False,
        initial=False,
        label='Send Update Notification',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Send email notification about enrollment status changes'
    )

    # Fee management fields
    course_fee = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        label='Course Fee',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        }),
        help_text='Course fee amount for this enrollment'
    )

    registration_fee = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        label='Registration Fee',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        }),
        help_text='Registration fee amount (for new students)'
    )

    charge_registration_fee = forms.BooleanField(
        required=False,
        initial=False,
        label='Charge Registration Fee',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Whether to charge registration fee for this enrollment'
    )

    registration_fee_paid = forms.BooleanField(
        required=False,
        initial=False,
        label='Registration Fee Paid',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Mark registration fee as paid'
    )

    # Student information fields (same as StaffEnrollmentForm)
    student_birth_date = forms.DateField(
        required=False,
        label='Student Birth Date',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Used for age verification and guardian requirement determination'
    )

    student_address = forms.CharField(
        required=False,
        label='Student Address',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Full residential address'
        })
    )

    student_email = forms.EmailField(
        required=False,
        label='Contact Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Primary contact email'
        }),
        help_text='Primary email for communications (student or guardian based on age)'
    )

    course = forms.ModelChoiceField(
        queryset=Course.objects.filter(status='published').order_by('name'),
        required=False,
        label='Course',
        widget=forms.Select(attrs={
            'class': 'form-select select2-searchable',
            'placeholder': 'Select Course'
        })
    )
    student_phone = forms.CharField(
        required=False,
        max_length=20,
        label='Contact Phone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        }),
        help_text='Primary phone for SMS notifications'
    )

    guardian_name = forms.CharField(
        required=False,
        max_length=100,
        label='Guardian Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parent/Guardian full name'
        }),
        help_text='Required for students under 18 years of age'
    )

    emergency_contact_name = forms.CharField(
        required=False,
        max_length=100,
        label='Emergency Contact Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact person'
        })
    )

    emergency_contact_phone = forms.CharField(
        required=False,
        max_length=20,
        label='Emergency Contact Phone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        })
    )

    medical_conditions = forms.CharField(
        required=False,
        label='Medical Conditions',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any medical conditions we should be aware of'
        })
    )

    special_requirements = forms.CharField(
        required=False,
        label='Special Requirements',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any special requirements or accommodations needed'
        })
    )

    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'class_instance', 'status', 'registration_status', 'source_channel']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select select2-searchable'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select select2-searchable'
            }),
            'class_instance': forms.Select(attrs={
                'class': 'form-select select2-searchable'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'registration_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'source_channel': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # For editing existing enrollments, disable course selection to avoid mistakes
        if self.instance and self.instance.pk:
            self.fields['course'].disabled = True
            self.fields['course'].help_text = "Course cannot be changed for existing enrollments"

            # Set fee field initial values from enrollment
            self.fields['course_fee'].initial = self.instance.course_fee or self.instance.course.price
            self.fields['registration_fee'].initial = self.instance.registration_fee or 0
            self.fields['registration_fee_paid'].initial = self.instance.registration_fee_paid

            # Determine if registration fee should be charged based on form_data or current state
            charge_reg_fee = False
            if hasattr(self.instance, 'form_data') and self.instance.form_data:
                charge_reg_fee = self.instance.form_data.get('charge_registration_fee', self.instance.registration_fee > 0)
            else:
                charge_reg_fee = self.instance.registration_fee > 0
            self.fields['charge_registration_fee'].initial = charge_reg_fee

            # Pre-populate fields with existing data from form_data
            if hasattr(self.instance, 'form_data') and self.instance.form_data:
                additional_info = self.instance.form_data.get('additional_student_info', {})

                # Set initial values for student information fields
                field_mapping = {
                    'student_birth_date': 'student_birth_date',
                    'student_address': 'student_address',
                    'student_email': 'student_email',
                    'student_phone': 'student_phone',
                    'guardian_name': 'guardian_name',
                    'emergency_contact_name': 'emergency_contact_name',
                    'emergency_contact_phone': 'emergency_contact_phone',
                    'medical_conditions': 'medical_conditions',
                    'special_requirements': 'special_requirements'
                }

                for form_field, data_key in field_mapping.items():
                    if data_key in additional_info:
                        value = additional_info[data_key]
                        # Handle date strings
                        if form_field == 'student_birth_date' and isinstance(value, str):
                            try:
                                from datetime import datetime
                                self.fields[form_field].initial = datetime.fromisoformat(value).date()
                            except:
                                pass
                        else:
                            self.fields[form_field].initial = value

    def clean(self):
        cleaned_data = super().clean()
        student_birth_date = cleaned_data.get('student_birth_date')
        guardian_name = cleaned_data.get('guardian_name')

        # Age-based validation for guardian requirement
        if student_birth_date:
            from datetime import date
            today = date.today()
            age = today.year - student_birth_date.year - (
                (today.month, today.day) < (student_birth_date.month, student_birth_date.day)
            )

            if age < 18 and not guardian_name:
                self.add_error('guardian_name',
                    'Guardian name is required for students under 18 years old')

        return cleaned_data

    def save(self, commit=True):
        enrollment = super().save(commit=False)

        # Store the original status to detect changes
        original_status = None
        if self.instance and self.instance.pk:
            try:
                original_enrollment = Enrollment.objects.get(pk=self.instance.pk)
                original_status = original_enrollment.status
            except Enrollment.DoesNotExist:
                pass

        # Handle fee updates
        course_fee = self.cleaned_data.get('course_fee')
        registration_fee = self.cleaned_data.get('registration_fee')
        charge_registration_fee = self.cleaned_data.get('charge_registration_fee', False)
        registration_fee_paid = self.cleaned_data.get('registration_fee_paid', False)

        # Update enrollment fee fields
        if course_fee is not None:
            enrollment.course_fee = course_fee

        # Handle registration fee logic
        if charge_registration_fee and registration_fee is not None:
            enrollment.registration_fee = registration_fee
        elif not charge_registration_fee:
            enrollment.registration_fee = 0

        enrollment.registration_fee_paid = registration_fee_paid

        # Update additional student information in form_data
        additional_student_info = {}
        student_fields = [
            'student_birth_date', 'student_address', 'student_email', 'student_phone',
            'guardian_name', 'emergency_contact_name', 'emergency_contact_phone',
            'medical_conditions', 'special_requirements'
        ]

        for field_name in student_fields:
            field_value = self.cleaned_data.get(field_name)
            if field_value:
                # Convert date objects to string for JSON serialization
                if hasattr(field_value, 'isoformat'):
                    additional_student_info[field_name] = field_value.isoformat()
                else:
                    additional_student_info[field_name] = field_value

        # Update form_data
        if not enrollment.form_data:
            enrollment.form_data = {}

        enrollment.form_data.update({
            'additional_student_info': additional_student_info,
            'last_updated_by_staff': True,
            'charge_registration_fee': charge_registration_fee,
            'fee_updated': True
        })

        if self.user:
            enrollment.form_data['last_updated_by'] = {
                'username': self.user.username,
                'name': f'{self.user.first_name} {self.user.last_name}'.strip()
            }

        # Store notification preference and status change info
        send_notification = self.cleaned_data.get('send_update_notification', False)
        status_changed = original_status and original_status != enrollment.status

        enrollment.form_data.update({
            'send_update_notification': send_notification,
            'status_changed': status_changed,
            'original_status': original_status
        })

        if commit:
            enrollment.save()
        return enrollment


class PublicEnrollmentForm(forms.Form):
    """Public enrollment form for students/guardians with age-based dynamic fields"""
    
    # Student Identification
    student_status = forms.ChoiceField(
        choices=[
            ('', 'Please select...'),
            ('new', 'New Student (First time enrolling)'),
            ('returning', 'Returning Student (Previously enrolled)')
        ],
        label='Student Status',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_student_status'
        }),
        help_text='Are you enrolling for the first time or returning?'
    )
    
    # Student Information
    first_name = forms.CharField(
        max_length=30,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student\'s first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student\'s last name'
        })
    )
    
    date_of_birth = forms.DateField(
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Used for student identification and determining contact requirements'
    )
    
    address = forms.CharField(
        required=False,
        label='Address',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Full residential address'
        })
    )
    
    # Contact Information (unified - will be labeled dynamically based on age)
    email = forms.EmailField(
        label='Contact Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Primary contact email'
        }),
        help_text='This will be the main contact email for enrollment communications'
    )
    
    phone = forms.CharField(
        max_length=20,
        label='Contact Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        }),
        help_text='Primary contact phone number for SMS notifications'
    )
    
    # Guardian Information (only for students under 18)
    guardian_name = forms.CharField(
        required=False,
        max_length=100,
        label='Parent/Guardian Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name of parent or guardian'
        }),
        help_text='Required for students under 18 years of age'
    )
    
    # Emergency Contact
    emergency_contact_name = forms.CharField(
        required=False,
        max_length=100,
        label='Emergency Contact Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency contact person'
        })
    )
    
    emergency_contact_phone = forms.CharField(
        required=False,
        max_length=20,
        label='Emergency Contact Phone',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0412 345 678'
        })
    )
    
    # Medical & Special Requirements
    medical_conditions = forms.CharField(
        required=False,
        label='Medical Conditions',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any medical conditions we should be aware of'
        })
    )
    
    special_requirements = forms.CharField(
        required=False,
        label='Special Requirements',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special requirements or accommodations needed'
        })
    )
    
    # Course Selection
    course_id = forms.ChoiceField(
        label='Course',
        widget=forms.Select(attrs={
            'class': 'form-select select2-searchable'
        })
    )
    
    def __init__(self, *args, **kwargs):
        courses = kwargs.pop('courses', None)
        super().__init__(*args, **kwargs)
        
        # Populate course choices with pricing information
        if courses is None:
            courses = Course.objects.filter(status='published', is_online_bookable=True).order_by('name')
            
        course_choices = [('', 'Select a course...')]
        
        for course in courses:
            # Get current applicable price (early bird or regular)
            applicable_price = course.get_applicable_price()
            is_early_bird = course.is_early_bird_available()

            if is_early_bird:
                savings = course.get_early_bird_savings()
                course_fee = f"${applicable_price} Early Bird (Save ${savings}!)"
            else:
                course_fee = f"${applicable_price}"

            if course.has_registration_fee():
                reg_fee_info = f" (+${course.registration_fee} registration fee for new students)"
            else:
                reg_fee_info = ""

            choice_label = f"{course.name} - {course_fee}{reg_fee_info}"
            course_choices.append((course.pk, choice_label))
        
        self.fields['course_id'].choices = course_choices
    
    def clean(self):
        cleaned_data = super().clean()
        date_of_birth = cleaned_data.get('date_of_birth')
        guardian_name = cleaned_data.get('guardian_name')
        student_status = cleaned_data.get('student_status')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        if date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            
            # Store calculated age for use in views/templates
            cleaned_data['calculated_age'] = age
            
            if age < 18:
                # Student is under 18, guardian name is required
                if not guardian_name or guardian_name.strip() == '':
                    self.add_error('guardian_name', 'Guardian name is required for students under 18.')
        
        # Validate student status selection
        if not student_status:
            self.add_error('student_status', 'Please select if you are a new or returning student.')
        
        # Check for existing student if returning student is selected
        if student_status == 'returning' and first_name and last_name and date_of_birth:
            from students.services import StudentMatchingService
            existing_student, match_type = StudentMatchingService.find_existing_student({
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': date_of_birth
            })
            
            if not existing_student or match_type == 'none':
                self.add_error('student_status', 
                    'No matching student record found. Please select "New Student" or verify the name and date of birth are correct.')
            elif match_type == 'multiple_matches':
                self.add_error('student_status', 
                    'Multiple students found with this name. Please contact us directly for enrollment.')
            else:
                # Store matched student for use in views
                cleaned_data['matched_student'] = existing_student
                cleaned_data['match_type'] = match_type
        
        return cleaned_data
    
    def get_student_age(self):
        """Helper method to calculate student age"""
        if hasattr(self, 'cleaned_data') and self.cleaned_data.get('date_of_birth'):
            from datetime import date
            birth_date = self.cleaned_data['date_of_birth']
            today = date.today()
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return None


class AttendanceForm(forms.ModelForm):
    """Single student attendance form"""
    
    class Meta:
        model = Attendance
        fields = ['student', 'class_instance', 'status', 'attendance_time']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select'
            }),
            'class_instance': forms.HiddenInput(),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'attendance_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        class_instance = kwargs.pop('class_instance', None)
        super().__init__(*args, **kwargs)
        
        if class_instance:
            self.fields['class_instance'].initial = class_instance
            # Include both confirmed enrolments and target-class makeup students.
            roster_students = AttendanceRosterService.get_roster_students(class_instance)
            student_choices = [
                (student.id, f"{student.get_full_name()} ({student.contact_email or 'No email'})")
                for student in roster_students
            ]
            self.fields['student'].queryset = Student.objects.filter(
                id__in=[choice[0] for choice in student_choices]
            )


class BulkAttendanceForm(forms.Form):
    """Bulk attendance management form"""
    
    class_instance = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        widget=forms.HiddenInput()
    )
    default_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        initial=timezone.now,
        label='Default Attendance Time',
        help_text='Default time for all attendance records'
    )
    
    def __init__(self, *args, **kwargs):
        class_instance = kwargs.pop('class_instance', None)
        super().__init__(*args, **kwargs)
        self.student_meta = {}
        
        if class_instance:
            self.fields['class_instance'].initial = class_instance
            
            roster_entries = AttendanceRosterService.get_roster_entries(class_instance)
            
            # Get existing attendance records
            existing_attendance = {
                att.student.id: att for att in 
                class_instance.attendances.select_related('student').all()
            }
            
            # Create dynamic fields for each roster student
            for entry in roster_entries:
                student = entry['student']
                field_name = f'student_{student.id}'
                self.student_meta[str(student.id)] = {
                    'email': student.contact_email or '',
                    'from_makeup': entry['from_makeup'],
                    'from_enrollment': entry['from_enrollment'],
                    'makeup_status': entry['makeup_status'],
                    'makeup_session_id': entry['makeup_session_id'],
                }
                
                # Student attendance status field
                self.fields[field_name] = forms.ChoiceField(
                    choices=[('', 'No change')] + Attendance.STATUS_CHOICES,
                    required=False,
                    label=student.get_full_name(),
                    widget=forms.Select(attrs={
                        'class': 'form-select student-status',
                        'data-student-id': student.id,
                        'data-student-name': student.get_full_name()
                    })
                )
                
                # Individual time field (optional)
                time_field_name = f'time_{student.id}'
                self.fields[time_field_name] = forms.DateTimeField(
                    required=False,
                    widget=forms.DateTimeInput(attrs={
                        'class': 'form-control student-time',
                        'type': 'datetime-local',
                        'data-student-id': student.id
                    }),
                    label=f'Time for {student.get_full_name()}'
                )
                
                # Set initial values if attendance exists
                if student.id in existing_attendance:
                    attendance = existing_attendance[student.id]
                    self.fields[field_name].initial = attendance.status
                    self.fields[time_field_name].initial = attendance.attendance_time
    
    def get_student_fields(self):
        """Return grouped student fields for template rendering"""
        student_data = []
        for field_name, field in self.fields.items():
            if field_name.startswith('student_'):
                student_id = field_name.replace('student_', '')
                time_field_name = f'time_{student_id}'
                time_field = self.fields.get(time_field_name)
                meta = self.student_meta.get(student_id, {})
                
                student_data.append({
                    'student_id': student_id,
                    'status_field': self[field_name],
                    'time_field': self[time_field_name] if time_field else None,
                    'student_name': field.label,
                    'student_email': meta.get('email', ''),
                    'from_makeup': meta.get('from_makeup', False),
                    'from_enrollment': meta.get('from_enrollment', False),
                    'makeup_status': meta.get('makeup_status'),
                })
        return student_data
    
    def save_attendance(self, class_instance, actor=None):
        """Save attendance records from form data"""
        default_time = self.cleaned_data['default_time']
        updated_count = 0
        created_count = 0
        makeup_synced_count = 0
        
        for field_name, status in self.cleaned_data.items():
            if field_name.startswith('student_') and status:
                student_id = field_name.replace('student_', '')
                time_field_name = f'time_{student_id}'
                attendance_time = self.cleaned_data.get(time_field_name) or default_time
                
                try:
                    student = Student.objects.get(id=student_id)
                    attendance, created = Attendance.objects.update_or_create(
                        student=student,
                        class_instance=class_instance,
                        defaults={
                            'status': status,
                            'attendance_time': attendance_time
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                    makeup_synced_count += MakeupSessionService.sync_status_from_target_attendance(
                        student=student,
                        target_class=class_instance,
                        attendance_status=status,
                        actor=actor,
                    )
                except Student.DoesNotExist:
                    continue
        
        return created_count, updated_count, makeup_synced_count


class BulkEnrollmentNotificationForm(forms.Form):
    """Form for sending bulk notifications to students from enrollment list"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email Only'),
        ('sms', 'SMS Only'),
        ('both', 'Both Email & SMS'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('general', 'General Message'),
        ('course_reminder', 'Course Reminder'),
        ('payment_reminder', 'Payment Reminder'),
        ('attendance_notice', 'Attendance Notice'),
        ('welcome', 'Welcome Message'),
        ('enrollment_confirm', 'Enrollment Confirmation'),
    ]
    
    # Enrollment selection (hidden field populated by JavaScript)
    enrollment_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    # Notification type
    notification_type = forms.ChoiceField(
        choices=NOTIFICATION_TYPE_CHOICES,
        label='Notification Type',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'handleNotificationTypeChange(this.value)'
        }),
        initial='email'
    )
    
    # Message categorization
    message_type = forms.ChoiceField(
        choices=MESSAGE_TYPE_CHOICES,
        label='Message Type',
        initial='general',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='This helps categorize the message for reporting purposes'
    )
    
    # Email specific fields
    subject = forms.CharField(
        max_length=200,
        label='Email Subject',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email subject'
        }),
        required=False
    )
    
    # Email content with TinyMCE (for email)
    email_content = forms.CharField(
        label='Email Content',
        widget=forms.Textarea(attrs={
            'class': 'tinymce-editor',
            'rows': 15,
        }),
        required=False,
        help_text='Rich HTML content for email with images and formatting'
    )
    
    # SMS content (plain text)
    sms_content = forms.CharField(
        label='SMS Message',
        max_length=160,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter SMS message (max 160 characters)',
            'maxlength': '160'
        }),
        required=False,
        help_text='Plain text message for SMS (max 160 characters)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        notification_type = cleaned_data.get('notification_type')
        subject = cleaned_data.get('subject')
        email_content = cleaned_data.get('email_content')
        sms_content = cleaned_data.get('sms_content')
        enrollment_ids = cleaned_data.get('enrollment_ids')
        
        errors = {}
        
        # Validate enrollment selection
        if not enrollment_ids or not enrollment_ids.strip():
            errors['enrollment_ids'] = 'At least one enrollment must be selected'
        else:
            try:
                enrollment_id_list = [int(id.strip()) for id in enrollment_ids.split(',') if id.strip()]
                if not enrollment_id_list:
                    errors['enrollment_ids'] = 'At least one enrollment must be selected'
                cleaned_data['enrollment_id_list'] = enrollment_id_list
            except ValueError:
                errors['enrollment_ids'] = 'Invalid enrollment selection'
        
        # Email specific validation
        if notification_type in ['email', 'both']:
            if not subject or not subject.strip():
                errors['subject'] = 'Email subject is required for email notifications'
            if not email_content or not email_content.strip():
                errors['email_content'] = 'Email content is required for email notifications'
            # Store email_content as message for backward compatibility if just email
            if notification_type == 'email':
                cleaned_data['message'] = email_content
        
        # SMS specific validation
        if notification_type in ['sms', 'both']:
            if not sms_content or not sms_content.strip():
                errors['sms_content'] = 'SMS message is required for SMS notifications'
            if sms_content and len(sms_content) > 160:
                errors['sms_content'] = f'SMS message is too long ({len(sms_content)} characters). Maximum 160 characters allowed.'
            # Store sms_content as message for backward compatibility if just SMS
            if notification_type == 'sms':
                cleaned_data['message'] = sms_content
        
        # Raise all errors at once
        if errors:
            raise ValidationError(errors)
        
        return cleaned_data


class StaffEnrollmentForm(forms.ModelForm):
    """
    Simplified enrollment form for staff members with student search functionality
    """

    # Student Selection/Search
    student_search = forms.CharField(
        required=False,
        label='Search Student',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, or phone...',
            'autocomplete': 'off',
            'data-toggle': 'student-search'
        }),
        help_text='Search for existing student or create new if not found'
    )

    # Registration fee option
    charge_registration_fee = forms.BooleanField(
        required=False,
        initial=False,
        label='Charge Registration Fee',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Check if this enrollment should include registration fee (for new students)'
    )

    # Additional enrollment options
    send_confirmation_email = forms.BooleanField(
        required=False,
        initial=False,
        label='Send Confirmation Email',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Send enrollment confirmation email to student/guardian with payment instructions'
    )

    # Staff notes for internal use
    staff_notes = forms.CharField(
        required=False,
        label='Staff Notes',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Internal notes about this enrollment...'
        }),
        help_text='Internal notes visible only to staff members'
    )

    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'class_instance', 'status', 'registration_status', 'source_channel']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select d-none',  # Hidden by default using Bootstrap class
                'required': False  # Remove browser-level required validation since we handle it manually
            }),
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'class_instance': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'registration_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'source_channel': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        # Extract course_id if provided
        self.course_id = kwargs.pop('course_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set default values
        self.fields['status'].initial = 'pending'
        self.fields['registration_status'].initial = 'returning'  # Default to returning student
        self.fields['source_channel'].initial = 'staff'
        self.fields['charge_registration_fee'].initial = False  # Default to unchecked

        # Configure student field for search functionality
        self.fields['student'].required = False  # Disable Django form-level validation
        self.fields['student'].widget.attrs.update({
            'required': False  # Remove HTML5 required attribute
        })

        # Handle course pre-selection
        if self.course_id:
            try:
                course = Course.objects.get(id=self.course_id)
                self.fields['course'].initial = course
                # Use Django's disabled attribute instead of HTML widget attribute
                self.fields['course'].disabled = True
                self.fields['course'].help_text = f'Pre-selected course: {course.name}'

                # Set registration fee default - always default to unchecked per UX requirement
                self.fields['charge_registration_fee'].initial = False
                if hasattr(course, 'has_registration_fee') and course.has_registration_fee():
                    # Course has registration fee but still default to unchecked
                    self.fields['charge_registration_fee'].help_text = 'Registration fee available for this course (unchecked by default)'
                else:
                    self.fields['charge_registration_fee'].widget.attrs['disabled'] = 'disabled'
                    self.fields['charge_registration_fee'].help_text = 'No registration fee for this course'

            except Course.DoesNotExist:
                pass

        # Customize status choices for staff
        self.fields['status'].choices = [
            ('pending', 'Pending - Awaiting payment confirmation'),
            ('confirmed', 'Confirmed - Payment received'),
            ('cancelled', 'Cancelled'),
        ]
    def clean_course(self):
        """Ensure course is not changed if pre-selected"""
        course = self.cleaned_data.get('course')

        # If course_id is provided (pre-selected), use that course regardless of form data
        if self.course_id:
            try:
                expected_course = Course.objects.get(id=self.course_id)
                # Always return the expected course when pre-selected
                return expected_course
            except Course.DoesNotExist:
                raise forms.ValidationError('Invalid course selection')

        # If no course_id provided, validate that a course was selected
        if not course:
            raise forms.ValidationError('Please select a course')

        return course

    def clean_student(self):
        """Validate student selection"""
        student = self.cleaned_data.get('student')
        if not student:
            raise forms.ValidationError('Please select a student')
        return student

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')
        class_instance = cleaned_data.get('class_instance')

        # Check for duplicate active enrollments (excluding cancelled)
        if student:
            existing_enrollment = None

            if class_instance:
                # Check for class-level duplicates
                existing_enrollment = Enrollment.objects.filter(
                    student=student,
                    class_instance=class_instance
                ).exclude(status='cancelled')

                error_msg = (
                    f'{student.get_full_name()} is already enrolled in {class_instance}. '
                    f'Status: {{status}}'
                )
            elif course:
                # Check for course-level duplicates (only when no specific class is selected)
                existing_enrollment = Enrollment.objects.filter(
                    student=student,
                    course=course,
                    class_instance__isnull=True  # Only check course-level enrollments
                ).exclude(status='cancelled')

                error_msg = (
                    f'{student.get_full_name()} is already enrolled in {course.name}. '
                    f'Status: {{status}}'
                )

            # For updates, exclude current instance
            if existing_enrollment and self.instance and self.instance.pk:
                existing_enrollment = existing_enrollment.exclude(pk=self.instance.pk)

            if existing_enrollment and existing_enrollment.exists():
                raise forms.ValidationError(
                    error_msg.format(status=existing_enrollment.first().get_status_display())
                )

        return cleaned_data

    def save(self, commit=True):
        enrollment = super().save(commit=False)

        # Add staff notes to form_data if provided
        staff_notes = self.cleaned_data.get('staff_notes')
        send_confirmation_email = self.cleaned_data.get('send_confirmation_email', False)
        charge_registration_fee = self.cleaned_data.get('charge_registration_fee', False)

        if not enrollment.form_data:
            enrollment.form_data = {}

        # Store form preferences and metadata
        enrollment.form_data.update({
            'send_confirmation_email': send_confirmation_email,
            'charge_registration_fee': charge_registration_fee,
            'created_by_staff': True
        })

        if staff_notes:
            enrollment.form_data['staff_notes'] = staff_notes

        if self.user:
            enrollment.form_data['created_by'] = {
                'username': self.user.username,
                'name': f'{self.user.first_name} {self.user.last_name}'.strip()
            }

        # Calculate and set enrollment fees using the fee calculator
        if commit:
            enrollment.save()

            # Import here to avoid circular imports
            from students.services import EnrollmentFeeCalculator

            # Determine registration status for fee calculation
            registration_status = enrollment.registration_status or 'new'

            # Calculate fees and update enrollment
            fees = EnrollmentFeeCalculator.update_enrollment_fees(
                enrollment,
                enrollment.course,
                registration_status == 'new'
            )

            # Override registration fee based on staff choice
            if not charge_registration_fee:
                enrollment.registration_fee = 0
                enrollment.save()

        return enrollment


class QuickStudentCreateForm(forms.ModelForm):
    """
    Quick student creation form for use within enrollment process
    """
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'contact_email', 'contact_phone',
            'address', 'guardian_name',
            'emergency_contact_name', 'emergency_contact_phone',
            'medical_conditions', 'special_requirements'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@email.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full residential address'
            }),
            'guardian_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Parent/Guardian name (required for under 18)'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency contact name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0412 345 678'
            }),
            'medical_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any medical conditions...'
            }),
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any special requirements...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set all fields as not required initially
        for field_name in self.fields:
            self.fields[field_name].required = False
        
        # Set essential fields as required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['birth_date'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        guardian_name = cleaned_data.get('guardian_name')
        
        # Calculate age and check guardian requirement
        if birth_date:
            from datetime import date
            today = date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            
            if age < 18 and not guardian_name:
                self.add_error('guardian_name', 
                    'Guardian name is required for students under 18 years old')
        
        return cleaned_data


class StudentSearchForm(forms.Form):
    """Student search form for AJAX requests"""
    
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search students by name, email, or phone...',
            'autocomplete': 'off'
        })
    )
    course_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False
    )
    limit = forms.IntegerField(
        initial=10,
        min_value=1,
        max_value=50,
        widget=forms.HiddenInput(),
        required=False  # Make this field optional
    )
    
    def search_students(self):
        """Perform student search and return results"""
        if not self.is_valid():
            return []
            
        query = self.cleaned_data.get('query', '').strip()
        course_id = self.cleaned_data.get('course_id')
        limit = self.cleaned_data.get('limit', 10)
        
        if not query:
            return []
        
        # Base queryset
        students_qs = Student.objects.filter(is_active=True)
        
        # Filter by course enrollment if specified
        if course_id:
            students_qs = students_qs.filter(
                enrollments__course_id=course_id,
                enrollments__status='confirmed'
            )
        
        # Search across multiple fields
        from django.db.models import Q
        search_query = (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(contact_email__icontains=query) |
            Q(contact_phone__icontains=query)
        )
        
        students = students_qs.filter(search_query).distinct()[:limit]
        
        # Format results
        results = []
        for student in students:
            # Ensure we have proper names
            full_name = student.get_full_name()
            if not full_name or full_name.strip() == " ":
                # Handle case where names might be empty
                full_name = f"Student #{student.id}"

            # Get contact information with better defaults
            email = student.contact_email or 'No email provided'
            phone = student.contact_phone or 'No phone provided'

            results.append({
                'id': student.id,
                'name': full_name,
                'email': email,
                'phone': phone,
                'display': f"{full_name} ({email})"
            })

        return results


class EnrollmentTransferForm(forms.Form):
    """Form for transferring a student from one course to another"""
    
    target_course = forms.ModelChoiceField(
        queryset=Course.objects.filter(status='published').order_by('name'),
        label='Transfer to Course',
        widget=forms.Select(attrs={
            'class': 'form-select select2-searchable'
        }),
        help_text='Select the course to transfer the student to'
    )
    
    PRICE_HANDLING_CHOICES = [
        ('new_price', 'Use New Course Price'),
        ('carry_over', 'Carry Over Original Price'),
    ]
    
    price_handling = forms.ChoiceField(
        choices=PRICE_HANDLING_CHOICES,
        initial='new_price',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='Price Handling',
        help_text='How to handle price difference between courses'
    )

    transfer_effective_at = forms.DateTimeField(
        label='Transfer Effective From',
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }
        ),
        help_text='Attendance will apply to classes on or after this time'
    )
    
    force_transfer = forms.BooleanField(
        required=False,
        label='Force Transfer (Override Vacancy)',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Check to proceed even if the target course is full'
    )
    
    send_confirmation = forms.BooleanField(
        required=False,
        initial=True,
        label='Send Transfer Confirmation',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Send email notification to student/guardian about the transfer'
    )
    
    def __init__(self, *args, **kwargs):
        self.current_enrollment = kwargs.pop('current_enrollment', None)
        super().__init__(*args, **kwargs)

        if not self.initial.get('transfer_effective_at'):
            self.initial['transfer_effective_at'] = timezone.localtime(timezone.now())

        if self.current_enrollment:
            # Exclude current course from choices
            current_course_id = self.current_enrollment.course.id
            self.fields['target_course'].queryset = Course.objects.filter(
                status='published'
            ).exclude(id=current_course_id).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        target_course = cleaned_data.get('target_course')
        force_transfer = cleaned_data.get('force_transfer')
        transfer_effective_at = cleaned_data.get('transfer_effective_at')

        if transfer_effective_at and timezone.is_naive(transfer_effective_at):
            cleaned_data['transfer_effective_at'] = timezone.make_aware(
                transfer_effective_at,
                timezone.get_current_timezone()
            )
        
        if target_course:
            # Check vacancy - only if force_transfer is NOT checked
            if not force_transfer:
                existing_count = Enrollment.objects.filter(
                    course=target_course,
                    status='confirmed'
                ).count()
                
                if existing_count >= target_course.vacancy:
                    # We add error to target_course field
                    self.add_error('target_course', 
                         ValidationError(
                            f'Target course {target_course.name} is full ({existing_count}/{target_course.vacancy}). '
                            f'Please check "Force Transfer" below to override this check.'
                        )
                    )
        
            # Check if student is already enrolled in target course
            if self.current_enrollment:
                student = self.current_enrollment.student
                is_enrolled = Enrollment.objects.filter(
                    student=student,
                    course=target_course,
                    status__in=['pending', 'confirmed']
                ).exists()
                
                if is_enrolled:
                    self.add_error('target_course',
                        f'Student is already enrolled in {target_course.name}.'
                    )
        
        return cleaned_data
