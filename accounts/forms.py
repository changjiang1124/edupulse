from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.utils import timezone

from academics.models import Class
from facilities.models import Facility

from .models import Staff


class StaffForm(forms.ModelForm):
    """Staff form with Bootstrap styling and role-based field management"""
    
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
                'placeholder': '0412 345 678'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def save(self, commit=True):
        """Override save to ensure Django auth fields are consistent with role"""
        staff = super().save(commit=False)
        
        # Set Django auth fields based on role
        if staff.role == 'admin':
            staff.is_staff = True
            staff.is_superuser = True
        elif staff.role == 'teacher':
            staff.is_staff = False
            staff.is_superuser = False
        
        if commit:
            staff.save()
        return staff


class StaffCreationForm(UserCreationForm):
    """Staff creation form with Bootstrap styling and role-based field management"""
    
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
    
    def save(self, commit=True):
        """Override save to ensure Django auth fields are consistent with role"""
        staff = super().save(commit=False)
        
        # Set Django auth fields based on role
        if staff.role == 'admin':
            staff.is_staff = True
            staff.is_superuser = True
        elif staff.role == 'teacher':
            staff.is_staff = False
            staff.is_superuser = False
        
        # Set default active status
        staff.is_active_staff = True
        
        if commit:
            staff.save()
        return staff


class StaffAttendanceManualEntryForm(forms.Form):
    """Admin form for payroll-first manual staff attendance entries."""

    ENTRY_MODE_CHOICES = [
        ('full_session', 'Full Session'),
        ('single_event', 'Single Event'),
    ]

    CLOCK_TYPE_CHOICES = [
        ('clock_in', 'Clock In'),
        ('clock_out', 'Clock Out'),
    ]

    entry_mode = forms.ChoiceField(
        choices=ENTRY_MODE_CHOICES,
        initial='full_session',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    work_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'}
        )
    )
    clock_type = forms.ChoiceField(
        choices=CLOCK_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    event_time = forms.TimeField(
        required=False,
        input_formats=['%H:%M'],
        widget=forms.TimeInput(
            attrs={'class': 'form-control', 'type': 'time'}
        )
    )
    session_start_time = forms.TimeField(
        required=False,
        input_formats=['%H:%M'],
        widget=forms.TimeInput(
            attrs={'class': 'form-control', 'type': 'time'}
        )
    )
    session_end_time = forms.TimeField(
        required=False,
        input_formats=['%H:%M'],
        widget=forms.TimeInput(
            attrs={'class': 'form-control', 'type': 'time'}
        )
    )
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    classes = forms.ModelMultipleChoiceField(
        queryset=Class.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional note for the attendance record.'
            }
        )
    )
    manual_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional payroll or audit note.'
            }
        )
    )

    def __init__(self, *args, staff=None, existing_records=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff = staff
        self.existing_records = [record for record in (existing_records or []) if record]
        self.existing_record_ids = [record.pk for record in self.existing_records]
        self.fields['facility'].queryset = Facility.objects.filter(is_active=True).order_by('name')
        self.fields['facility'].empty_label = 'No facility'

        class_queryset = Class.objects.none()
        if staff is not None:
            current_class_ids = []
            for record in self.existing_records:
                current_class_ids.extend(record.classes.values_list('pk', flat=True))
            class_queryset = Class.objects.filter(
                teacher=staff
            ).filter(
                Q(is_active=True) | Q(pk__in=set(current_class_ids))
            ).select_related('course', 'facility').order_by('-date', 'start_time')

        self.fields['classes'].queryset = class_queryset
        self._set_initial_values()

    def clean(self):
        cleaned_data = super().clean()
        entry_mode = cleaned_data.get('entry_mode')
        facility = cleaned_data.get('facility')
        classes = cleaned_data.get('classes')
        work_date = cleaned_data.get('work_date')

        if self.staff is None:
            raise forms.ValidationError('A staff member is required for manual attendance entry.')

        event_timestamp = self._combine_datetime(work_date, cleaned_data.get('event_time'))
        session_start = self._combine_datetime(work_date, cleaned_data.get('session_start_time'))
        session_end = self._combine_datetime(work_date, cleaned_data.get('session_end_time'))

        cleaned_data['event_timestamp'] = event_timestamp
        cleaned_data['session_start'] = session_start
        cleaned_data['session_end'] = session_end

        if entry_mode == 'single_event':
            if not cleaned_data.get('clock_type'):
                self.add_error('clock_type', 'Select the attendance event type.')
            if not event_timestamp:
                self.add_error('event_time', 'Enter the event time.')
            self._validate_single_event_conflict(cleaned_data)
        else:
            if not session_start:
                self.add_error('session_start_time', 'Enter the clock in time.')
            if not session_end:
                self.add_error('session_end_time', 'Enter the clock out time.')
            if session_start and session_end and session_end <= session_start:
                session_end = session_end + timedelta(days=1)
                cleaned_data['session_end'] = session_end
            self._validate_session_conflict(cleaned_data)

        for class_instance in classes or []:
            if class_instance.teacher_id != self.staff.id:
                self.add_error('classes', 'Selected classes must belong to the chosen staff member.')
                break
            if facility and class_instance.facility_id and class_instance.facility_id != facility.id:
                self.add_error('classes', 'Selected classes must belong to the selected facility.')
                break

        return cleaned_data

    def _combine_datetime(self, work_date, time_value):
        if not work_date or not time_value:
            return None

        combined = datetime.combine(work_date, time_value)
        if timezone.is_naive(combined):
            combined = timezone.make_aware(combined, timezone.get_current_timezone())

        return timezone.localtime(combined)

    def _set_initial_values(self):
        if not self.existing_records or self.is_bound:
            return

        clock_in_record = next(
            (record for record in self.existing_records if record.clock_type == 'clock_in'),
            None
        )
        clock_out_record = next(
            (record for record in self.existing_records if record.clock_type == 'clock_out'),
            None
        )
        primary_record = clock_in_record or clock_out_record
        if primary_record is None:
            return

        local_timestamp = timezone.localtime(primary_record.timestamp)
        initial = {
            'work_date': local_timestamp.date(),
            'facility': next(
                (record.facility for record in self.existing_records if record.facility_id),
                None
            ),
            'classes': self._merge_classes(),
            'notes': self._first_populated_value('notes'),
            'manual_reason': self._first_populated_value('manual_reason'),
        }

        if clock_in_record and clock_out_record:
            initial.update({
                'entry_mode': 'full_session',
                'session_start_time': timezone.localtime(clock_in_record.timestamp).time().replace(second=0, microsecond=0),
                'session_end_time': timezone.localtime(clock_out_record.timestamp).time().replace(second=0, microsecond=0),
            })
        else:
            initial.update({
                'entry_mode': 'single_event',
                'clock_type': primary_record.clock_type,
                'event_time': local_timestamp.time().replace(second=0, microsecond=0),
            })

        for field_name, value in initial.items():
            if value in (None, '', []):
                continue
            self.fields[field_name].initial = value

    def _first_populated_value(self, attribute_name):
        for record in self.existing_records:
            value = getattr(record, attribute_name, '')
            if value:
                return value
        return ''

    def _merge_classes(self):
        merged_classes = []
        seen = set()
        for record in self.existing_records:
            for class_instance in record.classes.all():
                if class_instance.pk in seen:
                    continue
                seen.add(class_instance.pk)
                merged_classes.append(class_instance.pk)
        return merged_classes

    def _attendance_queryset(self):
        from core.models import TeacherAttendance

        queryset = TeacherAttendance.objects.filter(teacher=self.staff)
        if self.existing_record_ids:
            queryset = queryset.exclude(pk__in=self.existing_record_ids)
        return queryset

    def _validate_single_event_conflict(self, cleaned_data):
        event_timestamp = cleaned_data.get('event_timestamp')
        clock_type = cleaned_data.get('clock_type')
        if not event_timestamp or not clock_type:
            return

        conflict = self._attendance_queryset().filter(
            clock_type=clock_type,
            timestamp=event_timestamp
        ).exists()
        if conflict:
            self.add_error(
                'event_time',
                'A matching attendance record already exists at this date and time.'
            )

    def _validate_session_conflict(self, cleaned_data):
        session_start = cleaned_data.get('session_start')
        session_end = cleaned_data.get('session_end')
        if not session_start or not session_end:
            return

        queryset = self._attendance_queryset().filter(
            timestamp__date__gte=(session_start - timedelta(days=1)).date(),
            timestamp__date__lte=(session_end + timedelta(days=1)).date()
        ).select_related('facility').prefetch_related('classes__course').order_by('timestamp')

        if not queryset.exists():
            return

        from core.services.staff_timesheet_service import StaffTimesheetService

        paired_records = StaffTimesheetService._pair_teacher_attendance(list(queryset))
        if not paired_records:
            paired_records = StaffTimesheetService._build_unmatched_from_records(list(queryset))

        for record in paired_records:
            existing_start = record.get('clock_in')
            existing_end = record.get('clock_out')

            if existing_start and existing_end:
                existing_start_ts = existing_start.timestamp
                existing_end_ts = existing_end.timestamp
                if session_start < existing_end_ts and session_end > existing_start_ts:
                    self.add_error(
                        None,
                        (
                            'This session overlaps an existing attendance entry from '
                            f'{timezone.localtime(existing_start_ts).strftime("%d/%m/%Y %H:%M")} '
                            f'to {timezone.localtime(existing_end_ts).strftime("%d/%m/%Y %H:%M")}.'
                        )
                    )
                    return
                continue

            single_record = existing_start or existing_end
            if single_record and session_start <= single_record.timestamp <= session_end:
                self.add_error(
                    None,
                    (
                        'This session overlaps an existing attendance event at '
                        f'{timezone.localtime(single_record.timestamp).strftime("%d/%m/%Y %H:%M")}.'
                    )
                )
                return
