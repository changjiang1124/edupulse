from django import forms
from tinymce.widgets import TinyMCE
from .models import Course, Class
from .widgets import DurationField


class CourseForm(forms.ModelForm):
    """Course form with Bootstrap styling"""
    
    class Meta:
        model = Course
        fields = [
            'name', 'short_description', 'description', 'featured_image', 'price', 'registration_fee', 'course_type', 'category', 'status', 'teacher',
            'start_date', 'end_date', 'repeat_pattern', 'repeat_weekday', 'repeat_day_of_month', 
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
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
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
            'enrollment_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For existing instances, ensure all fields are properly pre-filled
        if self.instance and self.instance.pk:
            # Set widget values directly to ensure proper pre-filling
            if self.instance.enrollment_deadline:
                self.fields['enrollment_deadline'].widget.attrs['value'] = self.instance.enrollment_deadline.strftime('%Y-%m-%d')
            
            if self.instance.registration_fee is not None:
                self.fields['registration_fee'].widget.attrs['value'] = self.instance.registration_fee
                
            if self.instance.end_date:
                self.fields['end_date'].widget.attrs['value'] = self.instance.end_date.strftime('%Y-%m-%d')
            
            if self.instance.start_date:
                self.fields['start_date'].widget.attrs['value'] = self.instance.start_date.strftime('%Y-%m-%d')
                
            if self.instance.start_time:
                self.fields['start_time'].widget.attrs['value'] = self.instance.start_time.strftime('%H:%M')
        
        # Create day of month choices (1-31)
        day_choices = [('', 'Select day...')] + [(i, f'{i}') for i in range(1, 32)]
        self.fields['repeat_day_of_month'] = forms.ChoiceField(
            choices=day_choices,
            required=False,
            widget=forms.Select(attrs={'class': 'form-select'})
        )
        
        # Set initial value for repeat_day_of_month if editing
        if self.instance and self.instance.pk and self.instance.repeat_day_of_month is not None:
            self.fields['repeat_day_of_month'].initial = self.instance.repeat_day_of_month
            self.fields['repeat_day_of_month'].widget.attrs['selected'] = self.instance.repeat_day_of_month
        
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
        
        # Ensure all fields are properly pre-filled for edit mode
        if self.instance and self.instance.pk:
            # Set widget values directly for better pre-filling
            if self.instance.enrollment_deadline:
                self.fields['enrollment_deadline'].widget.attrs['value'] = self.instance.enrollment_deadline.strftime('%Y-%m-%d')
            
            if self.instance.registration_fee is not None:
                self.fields['registration_fee'].widget.attrs['value'] = self.instance.registration_fee
                
            if self.instance.repeat_weekday is not None:
                self.fields['repeat_weekday'].initial = self.instance.repeat_weekday
                
            if self.instance.repeat_day_of_month is not None:
                self.fields['repeat_day_of_month'].initial = self.instance.repeat_day_of_month
                
            # Set date and time field values
            if self.instance.end_date:
                self.fields['end_date'].widget.attrs['value'] = self.instance.end_date.strftime('%Y-%m-%d')
                
            if self.instance.start_date:
                self.fields['start_date'].widget.attrs['value'] = self.instance.start_date.strftime('%Y-%m-%d')
                
            if self.instance.start_time:
                self.fields['start_time'].widget.attrs['value'] = self.instance.start_time.strftime('%H:%M')
        
        if self.instance and self.instance.pk:
            # Disable fields that shouldn't be changed in edit mode to avoid complications
            readonly_fields = ['repeat_pattern', 'course_type', 'start_date', 'end_date']
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
            'date': forms.DateInput(attrs={
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