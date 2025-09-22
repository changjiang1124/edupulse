from django import forms
from tinymce.widgets import TinyMCE
from .models import Course, Class
from .widgets import DurationField


class CourseForm(forms.ModelForm):
    """Course form with Bootstrap styling"""
    
    class Meta:
        model = Course
        fields = [
            'name', 'short_description', 'description', 'featured_image', 'price', 'early_bird_price', 'early_bird_deadline', 'registration_fee', 'course_type', 'category', 'status', 'teacher',
            'start_date', 'end_date', 'repeat_pattern', 'repeat_weekday', 'repeat_day_of_month', 'daily_weekdays',
            'start_time', 'duration_minutes', 'vacancy', 'facility', 'classroom', 'is_online_bookable',
            'enrollment_deadline'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course name'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description for website listing',
                'maxlength': 500
            }),
            'description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'featured_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'title': 'Select course feature image'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'early_bird_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Early bird price (optional)'
            }),
            'early_bird_deadline': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'registration_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Leave blank if no registration fee applies'
            }),
            'course_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'teacher': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'repeat_pattern': forms.Select(attrs={
                'class': 'form-select'
            }),
            'repeat_weekday': forms.Select(attrs={
                'class': 'form-select'
            }),
            'repeat_day_of_month': forms.Select(attrs={
                'class': 'form-select'
            }),
            'daily_weekdays': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '10',
                'step': '10',
                'placeholder': 'Duration in minutes (e.g. 60, 90, 120)'
            }),
            'vacancy': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'facility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'classroom': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_online_bookable': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'enrollment_deadline': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For existing instances, ensure all fields are properly pre-filled using initial values
        if self.instance and self.instance.pk:
            # Use form.initial to guarantee the widget receives the value even for disabled fields
            if self.instance.enrollment_deadline:
                self.initial['enrollment_deadline'] = self.instance.enrollment_deadline

            if self.instance.registration_fee is not None:
                self.initial['registration_fee'] = self.instance.registration_fee

            if self.instance.early_bird_price is not None:
                self.initial['early_bird_price'] = self.instance.early_bird_price

            if self.instance.early_bird_deadline:
                self.initial['early_bird_deadline'] = self.instance.early_bird_deadline
                
            if self.instance.end_date:
                self.initial['end_date'] = self.instance.end_date
            
            if self.instance.start_date:
                self.initial['start_date'] = self.instance.start_date
                
            if self.instance.start_time:
                self.initial['start_time'] = self.instance.start_time
                
            # Set other field initial values
            if self.instance.repeat_weekday is not None:
                self.initial['repeat_weekday'] = self.instance.repeat_weekday

            if self.instance.repeat_day_of_month is not None:
                self.initial['repeat_day_of_month'] = self.instance.repeat_day_of_month

            if self.instance.daily_weekdays is not None:
                self.initial['daily_weekdays'] = self.instance.daily_weekdays
        
        # Create day of month choices (1-31)
        day_choices = [('', 'Select day...')] + [(i, f'{i}') for i in range(1, 32)]
        self.fields['repeat_day_of_month'] = forms.ChoiceField(
            choices=day_choices,
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'})
        )

        # Configure daily weekdays field with custom choices
        from .models import Course
        weekday_choices = Course.WEEKDAY_CHOICES
        self.fields['daily_weekdays'] = forms.MultipleChoiceField(
            choices=weekday_choices,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label='Days of the Week',
            help_text='Select which days of the week classes should occur',
            initial=[0, 1, 2, 3, 4]  # Default to weekdays (Mon-Fri)
        )
        
        # Configure classroom field for dynamic filtering
        from facilities.models import Classroom
        self.fields['classroom'].queryset = Classroom.objects.filter(is_active=True).select_related('facility')
        self.fields['classroom'].empty_label = "Select facility first..."
        
        # If there's an existing facility, filter classrooms accordingly
        if self.instance and self.instance.pk and self.instance.facility:
            self.fields['classroom'].queryset = self.fields['classroom'].queryset.filter(
                facility=self.instance.facility
            )
            self.fields['classroom'].empty_label = "Select classroom..."
        
    def clean_featured_image(self):
        """Validate featured image file"""
        image = self.cleaned_data.get('featured_image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file size must be less than 5MB.')
            
            # Check file format
            valid_formats = ['JPEG', 'JPG', 'PNG', 'WEBP']
            try:
                from PIL import Image
                img = Image.open(image)
                if img.format not in valid_formats:
                    raise forms.ValidationError(
                        f'Invalid image format. Supported formats: {", ".join(valid_formats)}'
                    )
            except Exception as e:
                raise forms.ValidationError('Invalid image file.')
                
        return image
        
    def clean_repeat_weekday(self):
        """Clean repeat_weekday field to convert empty string to None"""
        value = self.cleaned_data.get('repeat_weekday')
        return None if value == '' else value
        
    def clean_repeat_day_of_month(self):
        """Clean repeat_day_of_month field to convert empty string to None"""
        value = self.cleaned_data.get('repeat_day_of_month')
        return None if value == '' else value

    def clean_daily_weekdays(self):
        """Clean daily_weekdays field to convert string values to integers"""
        value = self.cleaned_data.get('daily_weekdays')
        if value:
            # Convert string values to integers for JSON storage
            return [int(day) for day in value]
        return value
    
    def clean(self):
        """Validate facility-classroom matching and early bird pricing"""
        cleaned_data = super().clean()
        facility = cleaned_data.get('facility')
        classroom = cleaned_data.get('classroom')
        price = cleaned_data.get('price')
        early_bird_price = cleaned_data.get('early_bird_price')
        early_bird_deadline = cleaned_data.get('early_bird_deadline')
        start_date = cleaned_data.get('start_date')

        # Validate facility-classroom matching
        if facility and classroom:
            if classroom.facility != facility:
                raise forms.ValidationError(
                    f'The selected classroom "{classroom.name}" belongs to "{classroom.facility.name}" '
                    f'but you have selected facility "{facility.name}". '
                    f'Please select a classroom that belongs to the chosen facility, '
                    f'or change the facility to match the classroom.'
                )

        # Auto-assign facility if only classroom is provided
        elif classroom and not facility:
            cleaned_data['facility'] = classroom.facility

        # Validate early bird pricing
        if early_bird_price is not None:
            if price and early_bird_price >= price:
                raise forms.ValidationError({
                    'early_bird_price': 'Early bird price must be lower than the regular course fee.'
                })

            if not early_bird_deadline:
                raise forms.ValidationError({
                    'early_bird_deadline': 'Early bird deadline is required when early bird price is set.'
                })

        if early_bird_deadline:
            if not early_bird_price:
                raise forms.ValidationError({
                    'early_bird_price': 'Early bird price is required when early bird deadline is set.'
                })

            if start_date and early_bird_deadline >= start_date:
                raise forms.ValidationError({
                    'early_bird_deadline': 'Early bird deadline must be before the course start date.'
                })

        return cleaned_data


class CourseUpdateForm(CourseForm):
    """Course update form with class update options"""
    
    class Meta(CourseForm.Meta):
        fields = CourseForm.Meta.fields + ['bookable_state']
        widgets = CourseForm.Meta.widgets.copy()
        widgets.update({
            'bookable_state': forms.Select(attrs={
                'class': 'form-select'
            })
        })
    
    # Additional fields for class update control
    update_existing_classes = forms.BooleanField(
        required=False,
        initial=False,
        label='Apply Changes to Existing Classes',
        help_text='Update existing class sessions with the course changes',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'updateExistingClasses'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # Ensure all fields are properly pre-filled for edit mode using form.initial
        if self.instance and self.instance.pk:
            if self.instance.enrollment_deadline:
                self.initial['enrollment_deadline'] = self.instance.enrollment_deadline

            if self.instance.registration_fee is not None:
                self.initial['registration_fee'] = self.instance.registration_fee

            if self.instance.early_bird_price is not None:
                self.initial['early_bird_price'] = self.instance.early_bird_price

            if self.instance.early_bird_deadline:
                self.initial['early_bird_deadline'] = self.instance.early_bird_deadline
                
            if self.instance.repeat_weekday is not None:
                self.initial['repeat_weekday'] = self.instance.repeat_weekday

            if self.instance.repeat_day_of_month is not None:
                self.initial['repeat_day_of_month'] = self.instance.repeat_day_of_month

            if self.instance.daily_weekdays is not None:
                self.initial['daily_weekdays'] = self.instance.daily_weekdays
                
            # Set date and time field initial values  
            if self.instance.end_date:
                self.initial['end_date'] = self.instance.end_date
                
            if self.instance.start_date:
                self.initial['start_date'] = self.instance.start_date
                
            if self.instance.start_time:
                self.initial['start_time'] = self.instance.start_time
        
        if self.instance and self.instance.pk:
            # Disable fields that shouldn't be changed in edit mode to avoid complications
            readonly_fields = ['repeat_pattern', 'course_type', 'start_date', 'end_date', 'daily_weekdays']
            for field_name in readonly_fields:
                if field_name in self.fields:
                    self.fields[field_name].disabled = True
                    # Add help text to explain why it's disabled
                    if field_name == 'repeat_pattern':
                        self.fields[field_name].help_text = "Cannot be changed after course creation to avoid affecting existing classes"
                    elif field_name in ['start_date', 'end_date']:
                        self.fields[field_name].help_text = "Cannot be changed after course creation to avoid affecting class schedules"
                    elif field_name == 'course_type':
                        self.fields[field_name].help_text = "Cannot be changed after course creation"
                    elif field_name == 'daily_weekdays':
                        self.fields[field_name].help_text = "Cannot be changed after course creation to avoid affecting existing classes"
            
            # Add individual class selection field for upcoming classes
            from django.utils import timezone
            today = timezone.now().date()
            
            upcoming_classes = self.instance.classes.filter(
                is_active=True,
                date__gte=today
            ).order_by('date', 'start_time')
            
            if upcoming_classes.exists():
                class_choices = []
                for class_instance in upcoming_classes:
                    label = f"{class_instance.date.strftime('%a %d/%m/%Y')} at {class_instance.start_time.strftime('%I:%M %p')}"
                    
                    # Add teacher info if available
                    teacher = class_instance.teacher or self.instance.teacher
                    if teacher and (teacher.first_name or teacher.last_name):
                        teacher_name = f"{teacher.first_name} {teacher.last_name}".strip()
                        label += f" - {teacher_name}"
                    elif teacher:
                        label += f" - {teacher.username}"
                    
                    # Add location info if available
                    if class_instance.classroom:
                        label += f" [{class_instance.classroom.name}]"
                    elif class_instance.facility:
                        label += f" [{class_instance.facility.name}]"
                    
                    class_choices.append((class_instance.id, label))
                
                self.fields['selected_classes'] = forms.MultipleChoiceField(
                    choices=class_choices,
                    required=False,
                    label='Select Classes to Update',
                    help_text='Choose which classes should receive the course changes',
                    widget=forms.CheckboxSelectMultiple(attrs={
                        'class': 'form-check-input'
                    })
                )
        
        # Configure classroom field for dynamic filtering (same as parent but after other setup)
        from facilities.models import Classroom
        self.fields['classroom'].queryset = Classroom.objects.filter(is_active=True).select_related('facility')
        self.fields['classroom'].empty_label = "Select facility first..."
        
        # If there's an existing facility, filter classrooms accordingly
        if self.instance and self.instance.pk and self.instance.facility:
            self.fields['classroom'].queryset = self.fields['classroom'].queryset.filter(
                facility=self.instance.facility
            )
            self.fields['classroom'].empty_label = "Select classroom..."
    
    def clean(self):
        cleaned_data = super().clean()
        update_existing = cleaned_data.get('update_existing_classes')
        selected_classes = cleaned_data.get('selected_classes', [])
        
        if update_existing and not selected_classes:
            self.add_error('selected_classes', 
                          'Please select which classes to update.')
        
        return cleaned_data


class ClassForm(forms.ModelForm):
    """Class form with Bootstrap styling"""
    
    class Meta:
        model = Class
        fields = [
            'course', 'date', 'start_time', 'duration_minutes',
            'teacher', 'facility', 'classroom', 'is_active'
        ]
        widgets = {
            'course': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'step': '15'
            }),
            'teacher': forms.Select(attrs={
                'class': 'form-select'
            }),
            'facility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'classroom': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default value for new classes
        if not self.instance.pk:
            self.fields['is_active'].initial = True
        
        # Configure classroom field for dynamic filtering
        from facilities.models import Classroom
        self.fields['classroom'].queryset = Classroom.objects.filter(is_active=True).select_related('facility')
        self.fields['classroom'].empty_label = "Select facility first..."
        
        # If there's an existing facility (for edit mode or pre-filled), filter classrooms accordingly
        if self.instance.pk and self.instance.facility:
            self.fields['classroom'].queryset = self.fields['classroom'].queryset.filter(
                facility=self.instance.facility
            )
            self.fields['classroom'].empty_label = "Select classroom..."
        elif 'facility' in self.initial and self.initial['facility']:
            # Handle pre-filled facility from get_initial
            try:
                from facilities.models import Facility
                facility = Facility.objects.get(pk=self.initial['facility'])
                self.fields['classroom'].queryset = self.fields['classroom'].queryset.filter(
                    facility=facility
                )
                self.fields['classroom'].empty_label = "Select classroom..."
            except Facility.DoesNotExist:
                pass
    
    def clean(self):
        """Validate form data, including single session course restrictions and facility-classroom matching"""
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        facility = cleaned_data.get('facility')
        classroom = cleaned_data.get('classroom')
        
        # Check if single session course already has a class
        if course and course.repeat_pattern == 'once':
            existing_classes = Class.objects.filter(course=course)
            
            # Exclude current instance if editing
            if self.instance and self.instance.pk:
                existing_classes = existing_classes.exclude(pk=self.instance.pk)
            
            if existing_classes.exists():
                raise forms.ValidationError(
                    'This single session course already has a scheduled class. '
                    'Only one class can be created for single session courses. '
                    'Please edit the existing class instead.'
                )
        
        # Validate facility-classroom matching
        if facility and classroom:
            if classroom.facility != facility:
                raise forms.ValidationError(
                    f'The selected classroom "{classroom.name}" belongs to "{classroom.facility.name}" '
                    f'but you have selected facility "{facility.name}". '
                    f'Please select a classroom that belongs to the chosen facility, '
                    f'or change the facility to match the classroom.'
                )
        
        # Warn if only classroom is selected but no facility
        elif classroom and not facility:
            # Auto-assign the facility based on classroom
            cleaned_data['facility'] = classroom.facility
        
        return cleaned_data


class ClassUpdateForm(ClassForm):
    """Class update form with course field disabled"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For editing existing classes, disable course selection
        if self.instance and self.instance.pk:
            self.fields['course'].disabled = True
            self.fields['course'].help_text = "Course cannot be changed for existing classes"
            
            # Configure classroom field for dynamic filtering (inherited from parent)
            # The parent __init__ already handles the facility-classroom filtering