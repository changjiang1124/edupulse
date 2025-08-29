from django import forms
from django.contrib.auth.forms import UserCreationForm
from tinymce.widgets import TinyMCE
from .models import Course, Class, Student, Staff, Facility, Classroom, Enrollment


class CourseForm(forms.ModelForm):
    """Course form with Bootstrap styling"""
    
    class Meta:
        model = Course
        fields = [
            'name', 'short_description', 'description', 'price', 'course_type', 'status', 'teacher',
            'start_date', 'end_date', 'repeat_pattern', 'start_time', 'duration_minutes',
            'vacancy', 'facility', 'classroom', 'is_bookable', 'is_active'
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
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'course_type': forms.Select(attrs={
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
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'step': '15'
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
            'is_bookable': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class StudentForm(forms.ModelForm):
    """Student form with Bootstrap styling"""
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'email', 'phone', 'address',
            'guardian_name', 'guardian_phone', 'guardian_email', 'reference', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'student@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+61 xxx xxx xxx'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full address',
                'rows': 3
            }),
            'guardian_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Guardian full name'
            }),
            'guardian_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+61 xxx xxx xxx'
            }),
            'guardian_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'guardian@email.com'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'How did you hear about us?'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class StaffForm(forms.ModelForm):
    """Staff form with Bootstrap styling"""
    
    class Meta:
        model = Staff
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active_staff'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'staff@perthartschool.com.au'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+61 xxx xxx xxx'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class StaffCreationForm(UserCreationForm):
    """Staff creation form with Bootstrap styling"""
    
    class Meta(UserCreationForm.Meta):
        model = Staff
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'phone', 'role')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name in ['password1', 'password2']:
                field.widget.attrs.update({'class': 'form-control'})
            elif field_name == 'role':
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


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


class FacilityForm(forms.ModelForm):
    """Facility form with Bootstrap styling"""
    
    class Meta:
        model = Facility
        fields = ['name', 'address', 'phone', 'email', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter facility name'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full address',
                'rows': 3
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+61 xxx xxx xxx'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'facility@email.com'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


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


# Form mixins for consistent styling
class BootstrapFormMixin:
    """Mixin to apply Bootstrap classes to all form fields"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, 
                                         forms.DateInput, forms.TimeInput, forms.PasswordInput)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control'})


class ClassroomForm(forms.ModelForm):
    """Classroom form with Bootstrap styling"""
    
    class Meta:
        model = Classroom
        fields = ['facility', 'name', 'capacity', 'is_active']
        widgets = {
            'facility': forms.Select(attrs={
                'class': 'form-select'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter classroom name or number'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100',
                'placeholder': 'Maximum number of students'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 只显示活跃的设施
        self.fields['facility'].queryset = Facility.objects.filter(is_active=True)
        
        # 设置字段标签
        self.fields['facility'].label = 'Facility *'
        self.fields['name'].label = 'Classroom Name/Number *'
        self.fields['capacity'].label = 'Capacity *'
        self.fields['is_active'].label = 'Active Classroom'
        
        # 设置帮助文本
        self.fields['name'].help_text = 'Room name, number, or identifier'
        self.fields['capacity'].help_text = 'Maximum number of students this classroom can accommodate'