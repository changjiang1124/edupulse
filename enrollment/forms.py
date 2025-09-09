from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Enrollment, Attendance
from students.models import Student
from academics.models import Course, Class


class EnrollmentForm(forms.ModelForm):
    """Enrollment form with Bootstrap styling"""
    
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'status', 'source_channel']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select'
            }),
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'source_channel': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


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
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate course choices with pricing information
        courses = Course.objects.filter(status='published').order_by('name')
        course_choices = [('', 'Select a course...')]
        
        for course in courses:
            course_fee = f"${course.price}"
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
            # Only show students enrolled in this course
            enrolled_students = class_instance.course.enrollments.filter(
                status='confirmed'
            ).select_related('student')
            student_choices = [
                (enrollment.student.id, f"{enrollment.student.get_full_name()} ({enrollment.student.contact_email or 'No email'})")
                for enrollment in enrolled_students
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
        
        if class_instance:
            self.fields['class_instance'].initial = class_instance
            
            # Get enrolled students for this course
            enrolled_students = class_instance.course.enrollments.filter(
                status='confirmed'
            ).select_related('student')
            
            # Get existing attendance records
            existing_attendance = {
                att.student.id: att for att in 
                class_instance.attendances.select_related('student').all()
            }
            
            # Create dynamic fields for each enrolled student
            for enrollment in enrolled_students:
                student = enrollment.student
                field_name = f'student_{student.id}'
                
                # Student attendance status field
                self.fields[field_name] = forms.ChoiceField(
                    choices=[('', 'Not Set')] + Attendance.STATUS_CHOICES,
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
                
                student_data.append({
                    'student_id': student_id,
                    'status_field': self[field_name],
                    'time_field': self[time_field_name] if time_field else None,
                    'student_name': field.label
                })
        return student_data
    
    def save_attendance(self, class_instance):
        """Save attendance records from form data"""
        default_time = self.cleaned_data['default_time']
        updated_count = 0
        created_count = 0
        
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
                except Student.DoesNotExist:
                    continue
        
        return created_count, updated_count


class StaffEnrollmentForm(forms.ModelForm):
    """
    Enhanced enrollment form for staff members with student search and creation capabilities
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
        initial=True,
        label='Charge Registration Fee',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Check if this enrollment should include registration fee (for new students)'
    )
    
    # Additional notes for staff
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
        fields = ['student', 'course', 'status', 'registration_status', 'source_channel']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select d-none',  # Hidden by default using Bootstrap class
                'required': False  # Remove browser-level required validation since we handle it manually
            }),
            'course': forms.Select(attrs={
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
        self.fields['source_channel'].initial = 'staff'
        
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
                self.fields['course'].widget.attrs['disabled'] = 'disabled'
                self.fields['course'].help_text = f'Pre-selected course: {course.name}'
                
                # Set registration fee default based on course
                if hasattr(course, 'has_registration_fee') and course.has_registration_fee():
                    self.fields['charge_registration_fee'].initial = True
                else:
                    self.fields['charge_registration_fee'].initial = False
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
        if self.course_id:
            try:
                expected_course = Course.objects.get(id=self.course_id)
                if course != expected_course:
                    # Force the correct course
                    course = expected_course
            except Course.DoesNotExist:
                raise forms.ValidationError('Invalid course selection')
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
        
        # Check for duplicate enrollments
        if student and course:
            existing_enrollment = Enrollment.objects.filter(
                student=student,
                course=course
            ).exclude(status='cancelled')
            
            if self.instance and self.instance.pk:
                existing_enrollment = existing_enrollment.exclude(pk=self.instance.pk)
                
            if existing_enrollment.exists():
                raise forms.ValidationError(
                    f'{student.get_full_name()} is already enrolled in {course.name}. '
                    f'Status: {existing_enrollment.first().get_status_display()}'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        enrollment = super().save(commit=False)
        
        # Add staff notes to form_data if provided
        staff_notes = self.cleaned_data.get('staff_notes')
        if staff_notes:
            if not enrollment.form_data:
                enrollment.form_data = {}
            enrollment.form_data['staff_notes'] = staff_notes
            enrollment.form_data['created_by_staff'] = True
            if self.user:
                enrollment.form_data['created_by'] = {
                    'username': self.user.username,
                    'name': f'{self.user.first_name} {self.user.last_name}'.strip()
                }
        
        # Store registration fee decision
        charge_registration_fee = self.cleaned_data.get('charge_registration_fee', True)
        if not enrollment.form_data:
            enrollment.form_data = {}
        enrollment.form_data['charge_registration_fee'] = charge_registration_fee
        
        if commit:
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
            results.append({
                'id': student.id,
                'name': student.get_full_name(),
                'email': student.contact_email or 'No email',
                'phone': student.contact_phone or 'No phone',
                'display': f"{student.get_full_name()} ({student.contact_email or 'No email'})"
            })
        
        return results