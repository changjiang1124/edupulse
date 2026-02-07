from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q
from django.db import IntegrityError
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import Course, Class
from .forms import CourseForm, CourseUpdateForm, ClassForm, ClassUpdateForm


def _user_is_admin(user):
    return user.is_superuser or getattr(user, 'role', None) == 'admin'


class CourseDuplicateView(LoginRequiredMixin, View):
    """
    Duplicate an existing course.
    Copies the course with 'Draft' status and redirects to course list.
    Optionally includes existing enrollments as pending.
    """
    def post(self, request, pk):
        original = get_object_or_404(Course, pk=pk)
        
        # Check if we should include enrollments
        include_enrollments = request.POST.get('include_enrollments') == 'on'
        
        # Create a copy by setting pk to None
        original_pk = original.pk
        original.pk = None
        original.id = None
        original._state.adding = True
        
        # Update fields for the copy BEFORE saving to prevent unique constraint violation
        original.name = f"{original.name} (Copy)"
        original.status = 'draft'
        original.external_id = None
        original.woocommerce_last_synced_at = None
        
        original.save()
        
        enrollments_msg = ""
        if include_enrollments:
            try:
                from enrollment.models import Enrollment
                # Get confirmed and pending enrollments from original course
                # We skip cancelled ones as they are not relevant for next term mostly
                original_enrollments = Enrollment.objects.filter(
                    course_id=original_pk, 
                    status__in=['confirmed', 'pending', 'completed']
                )
                
                count = 0
                for old_enrollment in original_enrollments:
                    # Create new enrollment
                    Enrollment.objects.create(
                        student=old_enrollment.student,
                        course=original,
                        status='pending',
                        source_channel='staff',
                        registration_status='returning',
                        is_new_student=False,
                        matched_existing_student=True,
                        # Reset fee flags
                        registration_fee_paid=False,
                        is_early_bird=original.is_early_bird_available(),
                        # Recalculate fees based on NEW course
                        course_fee=original.get_applicable_price(),
                    )
                    count += 1
                
                if count > 0:
                    enrollments_msg = f" {count} existing enrollments have been copied as 'Pending'."
            except ImportError:
                pass
            except Exception as e:
                enrollments_msg = f" However, there was an error copying enrollments: {str(e)}"
        
        messages.success(
            request, 
            f'Course duplicated successfully as "{original.name}" (Draft).{enrollments_msg} Please review the new course.'
        )
        return redirect('academics:course_list')

    def get(self, request, pk):
        # Allow GET request for easier linking, but ideally should be POST
        return self.post(request, pk)


class CourseArchiveView(LoginRequiredMixin, View):
    """
    Archive a published course.
    """
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        if course.status != 'published':
            messages.error(request, 'Only published courses can be archived.')
        else:
            course.status = 'archived'
            course.save()
            messages.success(request, f'Course "{course.name}" has been archived.')
            
        return redirect('academics:course_list')

    def get(self, request, pk):
        return self.post(request, pk)


class CourseRestoreView(LoginRequiredMixin, View):
    """
    Restore an archived course to draft status.
    """
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        if course.status != 'archived':
            messages.error(request, 'Only archived courses can be restored.')
        else:
            course.status = 'draft'
            course.save()
            messages.success(request, f'Course "{course.name}" has been restored to Draft status.')
            
        return redirect('academics:course_list')

    def get(self, request, pk):
        return self.post(request, pk)


class CourseDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a draft course.
    """
    model = Course
    template_name = 'core/courses/course_confirm_delete.html'
    success_url = reverse_lazy('academics:course_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if course has enrollments and add to context for template warning
        context['has_enrollments'] = self.object.enrollments.exists()
        context['enrollment_count'] = self.object.enrollments.count()
        return context
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Pre-check: if course has enrollments, redirect with friendly message
        if self.object.enrollments.exists():
            enrollment_count = self.object.enrollments.count()
            messages.warning(
                request,
                f'Cannot delete course "{self.object.name}" because it has {enrollment_count} enrollment(s). '
                f'Please change the course status to "Archived" instead to preserve data integrity.'
            )
            return redirect('academics:course_detail', pk=self.object.pk)
        
        # Pre-check: if course is not draft, redirect with friendly message
        if self.object.status != 'draft':
            messages.error(
                request, 
                f'Only draft courses can be deleted. Please archive published courses instead.'
            )
            return redirect('academics:course_detail', pk=self.object.pk)
        
        return super().get(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Check if course is not draft
        if self.object.status != 'draft':
            messages.error(request, 'Only draft courses can be deleted. Please archive published courses instead.')
            return redirect('academics:course_list')
        
        # Check if course has enrollments
        if self.object.enrollments.exists():
            enrollment_count = self.object.enrollments.count()
            messages.warning(
                request,
                f'Cannot delete course "{self.object.name}" because it has {enrollment_count} enrollment(s). '
                f'Please change the course status to "Archived" instead to preserve data integrity.'
            )
            return redirect('academics:course_detail', pk=self.object.pk)
            
        try:
            course_name = self.object.name
            self.object.delete()
            messages.success(request, f'Course "{course_name}" has been deleted.')
            return HttpResponseRedirect(self.get_success_url())
        except ValidationError as e:
            # Fallback error handling in case model validation raises an error
            messages.error(request, ", ".join(e.messages))
            return redirect('academics:course_detail', pk=self.object.pk)


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'core/courses/list.html'
    context_object_name = 'courses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Course.objects.all()
        
        # Filter by status (default to published)
        status_filter = self.request.GET.get('status', 'published')
        
        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
            
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_status = self.request.GET.get('status', 'published')
        context['current_status'] = current_status
        context['status_choices'] = Course.STATUS_CHOICES
        
        # Calculate counts for tabs
        base_queryset = Course.objects.all()
        search = self.request.GET.get('search')
        if search:
            base_queryset = base_queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
            
        context['counts'] = {
            'published': base_queryset.filter(status='published').count(),
            'draft': base_queryset.filter(status='draft').count(),
            'archived': base_queryset.filter(status='archived').count(),
            'expired': base_queryset.filter(status='expired').count(),
            'all': base_queryset.count(),
        }
        
        return context


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'core/courses/form.html'
    success_url = reverse_lazy('academics:course_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Auto-generate classes based on course schedule
        classes_created = self.object.generate_classes()
        messages.success(
            self.request, 
            f'Course "{self.object.name}" created successfully! {classes_created} class(es) generated.'
        )
        return response


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'core/courses/detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use the correct related_name 'classes'
        context['classes'] = self.object.classes.filter(is_active=True).order_by('date', 'start_time')
        # Add enrollment information with try/except to avoid errors
        try:
            from enrollment.models import Enrollment
            context['enrollments'] = Enrollment.objects.filter(
                course=self.object
            ).select_related('student').all()
        except ImportError:
            context['enrollments'] = []

        regular_price = self.object.price or Decimal('0')
        early_bird_price = self.object.early_bird_price
        savings = None

        if early_bird_price is not None and regular_price and regular_price > early_bird_price:
            savings = regular_price - early_bird_price

        context['price_breakdown'] = self.object.get_price_breakdown()
        context['early_bird_info'] = {
            'price': early_bird_price,
            'deadline': self.object.early_bird_deadline,
            'savings': savings,
            'is_active': self.object.is_early_bird_available() if early_bird_price else False,
            'regular_price': regular_price,
        }
        return context


class CourseRegenerateClassesView(LoginRequiredMixin, View):
    """Append course-scheduled classes without removing existing ones."""

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        created_count = course.generate_classes(replace_existing=False)

        if created_count:
            messages.success(
                request,
                f"Added {created_count} new class{'es' if created_count != 1 else ''} from the course schedule."
            )
        else:
            messages.info(
                request,
                'No new classes were generated because the schedule already matches existing sessions.'
            )

        return redirect('academics:course_detail', pk=course.pk)

    def get(self, request, pk):  # pragma: no cover - convenience redirect
        return redirect('academics:course_detail', pk=pk)


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    form_class = CourseUpdateForm
    template_name = 'core/courses/form.html'
    
    def form_valid(self, form):
        # Capture original repeat configuration from the database before saving
        original = Course.objects.get(pk=form.instance.pk)
        original_repeat_weekday = original.repeat_weekday

        response = super().form_valid(form)

        new_repeat_pattern = self.object.repeat_pattern
        new_repeat_weekday = self.object.repeat_weekday
        supports_weekday_shift = new_repeat_pattern == 'weekly' and new_repeat_weekday is not None
        weekday_changed = (
            supports_weekday_shift
            and original_repeat_weekday is not None
            and new_repeat_weekday != original_repeat_weekday
        )

        # Handle class updates if requested (only when fields exist)
        if 'update_existing_classes' in form.fields:
            update_existing = form.cleaned_data.get('update_existing_classes', False)
            selected_classes = form.cleaned_data.get('selected_classes', [])
        else:
            update_existing = False
            selected_classes = []

        if update_existing and selected_classes:
            # Get the selected classes to update
            classes_to_update = self.object.classes.filter(
                is_active=True,
                id__in=[int(class_id) for class_id in selected_classes]
            )

            updated_count = 0
            dates_shifted_count = 0
            moved_beyond_end_date = False
            now = timezone.localtime()

            # Apply all course changes to selected classes
            for class_instance in classes_to_update:
                updated = False

                # Update all relevant fields from course
                update_fields = ['teacher', 'start_time', 'duration_minutes', 'facility', 'classroom']
                for field in update_fields:
                    new_value = getattr(self.object, field)
                    current_value = getattr(class_instance, field)
                    if current_value != new_value:
                        setattr(class_instance, field, new_value)
                        updated = True

                # Automatically shift class dates forward to the new weekday (future classes only)
                is_future_class = (
                    class_instance.date > now.date() or
                    (
                        class_instance.date == now.date() and (
                            class_instance.start_time is None or
                            class_instance.start_time >= now.time()
                        )
                    )
                )

                if supports_weekday_shift and weekday_changed and is_future_class:
                    current_weekday = class_instance.date.weekday()
                    if current_weekday != new_repeat_weekday:
                        # Move forward to the nearest occurrence of the new weekday
                        delta_days = (new_repeat_weekday - current_weekday) % 7
                        new_date = class_instance.date + timedelta(days=delta_days)
                        if new_date != class_instance.date:
                            class_instance.date = new_date
                            updated = True
                            dates_shifted_count += 1
                            if self.object.end_date and new_date > self.object.end_date:
                                moved_beyond_end_date = True

                if updated:
                    class_instance.save()
                    updated_count += 1

            # Provide success message
            base_message = 'Course updated successfully!'
            if updated_count > 0:
                details = [f'Course changes applied to {updated_count} selected class(es).']
                if supports_weekday_shift and weekday_changed:
                    if dates_shifted_count > 0:
                        details.append(f'{dates_shifted_count} class date(s) were moved to the new weekday.')
                    else:
                        details.append('No class dates needed to be moved to the new weekday.')
                messages.success(self.request, f"{base_message} {' '.join(details)}")
            else:
                if supports_weekday_shift and weekday_changed:
                    messages.success(self.request, f'{base_message} No classes needed updates or date shifts.')
                else:
                    messages.success(self.request, f'{base_message} No classes needed updates.')

            if moved_beyond_end_date and self.object.end_date:
                messages.warning(
                    self.request,
                    'Some class dates were moved beyond the current course end date; please review the schedule and adjust the course end date if necessary.'
                )
        else:
            messages.success(self.request, f'Course updated successfully!')


        return response
    
    def get_success_url(self):
        return reverse_lazy('academics:course_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check for pending enrollments count
        try:
            from enrollment.models import Enrollment
            if self.object and self.object.pk:
                context['pending_enrollment_count'] = Enrollment.objects.filter(
                    course=self.object,
                    status='pending'
                ).count()
        except Exception:
            context['pending_enrollment_count'] = 0
        
        # Add information about existing classes
        if self.object and self.object.pk:
            context['existing_classes'] = self.object.classes.filter(
                is_active=True,
                date__gte=timezone.now().date()
            ).count()
            context['past_classes'] = self.object.classes.filter(
                is_active=True,
                date__lt=timezone.now().date()
            ).count()
        
        return context


class ClassListView(LoginRequiredMixin, ListView):
    model = Class
    template_name = 'core/classes/list.html'
    context_object_name = 'classes'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Class.objects.select_related(
            'course', 'teacher', 'facility', 'classroom'
        )
        
        # Filter by user role - teachers can only see their classes
        if hasattr(self.request.user, 'role') and self.request.user.role == 'teacher':
            queryset = queryset.filter(course__teacher=self.request.user)
        
        # Filter by active status
        status_filter = self.request.GET.get('status', 'active')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'all':
            pass  # Show all statuses
        
        # Date range filters (simplified - no presets)
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
        else:
            # Default: show upcoming classes if no date filter is applied
            queryset = queryset.filter(date__gte=timezone.now().date())
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass
        
        # Filter by course
        course_id = self.request.GET.get('course')
        if course_id:
            try:
                course_id = int(course_id)
                queryset = queryset.filter(course_id=course_id)
            except (ValueError, TypeError):
                pass
        
        # Filter by teacher
        teacher_id = self.request.GET.get('teacher')
        if teacher_id:
            try:
                teacher_id = int(teacher_id)
                queryset = queryset.filter(teacher_id=teacher_id)
            except (ValueError, TypeError):
                pass
        
        # Filter by facility
        facility_id = self.request.GET.get('facility')
        if facility_id:
            try:
                facility_id = int(facility_id)
                queryset = queryset.filter(facility_id=facility_id)
            except (ValueError, TypeError):
                pass
        
        # Filter by classroom
        classroom_id = self.request.GET.get('classroom')
        if classroom_id:
            try:
                classroom_id = int(classroom_id)
                queryset = queryset.filter(classroom_id=classroom_id)
            except (ValueError, TypeError):
                pass
            
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(course__name__icontains=search) |
                Q(teacher__first_name__icontains=search) |
                Q(teacher__last_name__icontains=search) |
                Q(facility__name__icontains=search) |
                Q(classroom__name__icontains=search)
            )
        
        return queryset.order_by('date', 'start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'active')
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_course'] = self.request.GET.get('course', '')
        context['selected_teacher'] = self.request.GET.get('teacher', '')
        context['selected_facility'] = self.request.GET.get('facility', '')
        context['selected_classroom'] = self.request.GET.get('classroom', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['today'] = timezone.now().date()
        
        # Add user role context for template logic
        context['is_teacher'] = hasattr(self.request.user, 'role') and self.request.user.role == 'teacher'
        
        # Get filter options for dropdowns (only if user is admin)
        if not context['is_teacher']:
            context['courses'] = Course.objects.filter(status='published').order_by('name')
            from accounts.models import Staff
            context['teachers'] = Staff.objects.filter(role='teacher', is_active=True).order_by('first_name', 'last_name')
            from facilities.models import Facility, Classroom
            context['facilities'] = Facility.objects.filter(is_active=True).order_by('name')
            context['classrooms'] = Classroom.objects.filter(is_active=True).order_by('name')
        
        return context


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = Class
    form_class = ClassForm
    template_name = 'core/classes/form.html'
    success_url = reverse_lazy('academics:class_list')

    def get_initial(self):
        initial = super().get_initial()
        course_id = self.request.GET.get('course')
        if course_id:
            try:
                course = Course.objects.get(pk=course_id)
                initial['course'] = course.pk
                # Pre-fill facility and classroom from course defaults
                if course.facility:
                    initial['facility'] = course.facility.pk
                if course.classroom:
                    initial['classroom'] = course.classroom.pk
                # Pre-fill other fields from course defaults
                if course.teacher:
                    initial['teacher'] = course.teacher.pk
                initial['start_time'] = course.start_time
                initial['duration_minutes'] = course.duration_minutes
            except Course.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Provide selected_course to template to disable dropdown and render hidden input
        course_id = self.request.GET.get('course')
        selected_course = None
        if course_id:
            selected_course = Course.objects.filter(pk=course_id).first()
        context['selected_course'] = selected_course
        return context

    def form_valid(self, form):
        from django.contrib import messages
        
        # Ensure course is set from GET when dropdown is disabled
        if not form.cleaned_data.get('course'):
            course_id = self.request.GET.get('course')
            if course_id:
                form.instance.course = Course.objects.filter(pk=course_id).first()
        
        # Save the form first
        response = super().form_valid(form)
        
        # Check how many enrollments exist for automatic attendance creation
        course = form.instance.course
        if course:
            confirmed_enrollments = course.enrollments.filter(status='confirmed')
            enrollment_count = confirmed_enrollments.count()
            
            # Add success message based on course type and include attendance info
            if course.repeat_pattern == 'once':
                messages.success(
                    self.request,
                    f'Single session for "{course.name}" has been scheduled successfully. '
                    f'Attendance records automatically created for {enrollment_count} enrolled students.'
                )
            else:
                messages.success(
                    self.request,
                    f'Class for "{course.name}" has been created successfully. '
                    f'Attendance records automatically created for {enrollment_count} enrolled students.'
                )
        else:
            messages.success(
                self.request,
                f'Class has been created successfully.'
            )
        
        return response
    
    def get_success_url(self):
        # Redirect back to course detail if course was pre-selected
        course_id = self.request.GET.get('course')
        if course_id:
            return reverse('academics:course_detail', kwargs={'pk': course_id})
        return super().get_success_url()


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = Class
    template_name = 'core/classes/detail.html'
    context_object_name = 'class'
    
    def get_queryset(self):
        """Override to ensure teachers can only access their own classes"""
        queryset = super().get_queryset()
        if hasattr(self.request.user, 'role') and self.request.user.role == 'teacher':
            queryset = queryset.filter(course__teacher=self.request.user)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get students for this class - combining enrolled students and manual records
        try:
            from enrollment.models import Enrollment, Attendance, MakeupSession
            
            # Get existing attendance records map
            attendance_map = {
                attendance.student_id: attendance.status
                for attendance in Attendance.objects.filter(class_instance=self.object)
            }

            source_makeups = MakeupSession.objects.filter(
                source_class=self.object
            ).select_related(
                'student', 'target_class', 'target_class__course'
            ).order_by('-created_at')
            target_makeups = MakeupSession.objects.filter(
                target_class=self.object
            ).select_related(
                'student', 'source_class', 'source_class__course'
            ).order_by('-created_at')

            latest_source_makeup_by_student = {}
            for makeup in source_makeups:
                latest_source_makeup_by_student.setdefault(makeup.student_id, makeup)

            latest_target_makeup_by_student = {}
            for makeup in target_makeups:
                latest_target_makeup_by_student.setdefault(makeup.student_id, makeup)
            
            # Get ALL course enrollments (including cancelled) to handle history correctly
            enrollments = Enrollment.objects.filter(
                course=self.object.course
            ).select_related('student')
            
            enrolled_students = []
            seen_student_ids = set()
            from django.utils import timezone
            class_date = self.object.date
            
            for enrollment in enrollments:
                student_id = enrollment.student_id
                
                # Check 1: Always include if they have an attendance record (they were there)
                has_attendance = student_id in attendance_map
                
                if not has_attendance:
                    # Check 2: Filter out students who joined AFTER this class
                    # enrollment.created_at is aware datetime
                    enrollment_date = timezone.localtime(enrollment.created_at).date()
                    if enrollment_date > class_date:
                        continue
                        
                    # Check 3: Filter out students who cancelled BEFORE this class
                    if enrollment.status == 'cancelled':
                        # Use updated_at as proxy for cancellation date
                        cancellation_date = timezone.localtime(enrollment.updated_at).date()
                        if cancellation_date < class_date:
                            continue

                attendance_status = attendance_map.get(student_id)
                participation_type = 'enrolled' if enrollment.status == 'confirmed' else 'pending'
                
                # For cancelled students who attended or are historically valid, show appropriate status
                status_display = enrollment.get_status_display()
                if enrollment.status == 'cancelled':
                    # If they are in this list, they are historically valid or attended
                    # We might want to visually indicate they are no longer enrolled in the COURSE
                    pass

                source_makeup = latest_source_makeup_by_student.get(student_id)
                target_makeup = latest_target_makeup_by_student.get(student_id)

                enrolled_students.append({
                    'student': enrollment.student,
                    'participation_type': participation_type,
                    'attendance_status': attendance_status,
                    'enrollment_status': enrollment.status,
                    'enrollment_status_display': status_display,
                    'source_makeup': source_makeup,
                    'target_makeup': target_makeup,
                })
                seen_student_ids.add(student_id)

            # Include makeup-only students if they are not part of current course enrollments.
            for makeup in target_makeups:
                if makeup.student_id in seen_student_ids:
                    continue
                enrolled_students.append({
                    'student': makeup.student,
                    'participation_type': 'temp',
                    'attendance_status': attendance_map.get(makeup.student_id),
                    'enrollment_status': 'confirmed',
                    'enrollment_status_display': 'Makeup',
                    'source_makeup': None,
                    'target_makeup': makeup,
                })
                seen_student_ids.add(makeup.student_id)
            
            # Sort students by name
            enrolled_students.sort(key=lambda x: (x['student'].first_name, x['student'].last_name))
            
            context['class_students'] = enrolled_students
            
            # Get all attendance records for this class
            context['attendances'] = Attendance.objects.filter(
                class_instance=self.object
            ).select_related('student').order_by('attendance_time')
            
            # Calculate attendance statistics
            attendance_counts = {
                'present': context['attendances'].filter(status='present').count(),
                'absent': context['attendances'].filter(status='absent').count(),
                'late': context['attendances'].filter(status='late').count(),
            }
            context['attendance_stats'] = attendance_counts
            context['source_makeup_sessions'] = source_makeups
            context['target_makeup_sessions'] = target_makeups
            context['available_makeup_classes'] = Class.objects.filter(
                course=self.object.course,
                is_active=True
            ).exclude(pk=self.object.pk).order_by('date', 'start_time')
            context['makeup_reason_choices'] = MakeupSession.REASON_CHOICES
            
        except ImportError:
            context['class_students'] = []
            context['attendances'] = []
            context['attendance_stats'] = {'present': 0, 'absent': 0, 'late': 0}
            context['source_makeup_sessions'] = []
            context['target_makeup_sessions'] = []
            context['available_makeup_classes'] = []
            context['makeup_reason_choices'] = []
        
        # Add user role context for template logic
        context['is_teacher'] = hasattr(self.request.user, 'role') and self.request.user.role == 'teacher'
        context['can_manage_makeup'] = _user_is_admin(self.request.user)
        
        return context


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = Class
    form_class = ClassUpdateForm
    template_name = 'core/classes/form.html'
    
    def get_success_url(self):
        return reverse_lazy('academics:class_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Check if key fields have changed and warn about impacts
        if self.object.pk:  # Only for updates, not new instances
            original = Class.objects.get(pk=self.object.pk)
            changed_fields = []
            
            # Check critical fields that might affect students/attendance
            critical_fields = ['date', 'start_time', 'teacher', 'classroom']
            for field in critical_fields:
                if getattr(original, field) != form.cleaned_data.get(field):
                    changed_fields.append(field)
            
            if changed_fields:
                field_names = ', '.join(changed_fields)
                messages.warning(
                    self.request, 
                    f'Class {field_names} updated. Please notify enrolled students of any changes.'
                )
        
        messages.success(self.request, f'Class updated successfully!')
        return super().form_valid(form)


class ClassDeleteView(LoginRequiredMixin, DeleteView):
    """Delete class with confirmation and safety checks"""
    model = Class
    template_name = 'core/classes/delete.html'
    
    def get_success_url(self):
        # Return to course detail page after deletion
        return reverse_lazy('academics:course_detail', kwargs={'pk': self.object.course.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get deletion impact information
        try:
            from enrollment.models import Attendance
            attendance_count = Attendance.objects.filter(class_instance=self.object).count()
            context['attendance_count'] = attendance_count
            context['has_attendance'] = attendance_count > 0
        except ImportError:
            context['attendance_count'] = 0
            context['has_attendance'] = False
        
        # Get enrolled students for this course
        enrolled_count = self.object.course.enrollments.filter(status='confirmed').count()
        context['enrolled_students_count'] = enrolled_count
        
        return context
    
    def delete(self, request, *args, **kwargs):
        """Override delete to add safety checks and logging"""
        self.object = self.get_object()
        course_name = self.object.course.name
        class_date = self.object.date
        
        try:
            # Check if user has permission (admin only)
            if not request.user.is_superuser and request.user.role != 'admin':
                messages.error(request, 'Only administrators can delete classes.')
                return redirect('academics:class_detail', pk=self.object.pk)
            
            # Delete related attendance records (CASCADE should handle this, but being explicit)
            from enrollment.models import Attendance
            attendance_deleted = Attendance.objects.filter(class_instance=self.object).count()
            
            # Perform the deletion
            response = super().delete(request, *args, **kwargs)
            
            # Success message with impact information
            message = f'Class on {class_date.strftime("%d %B %Y")} for "{course_name}" has been deleted.'
            if attendance_deleted > 0:
                message += f' {attendance_deleted} attendance record(s) were also removed.'
            
            messages.success(request, message)
            return response
            
        except Exception as e:
            messages.error(request, f'Error deleting class: {str(e)}')
            return redirect('academics:class_detail', pk=self.object.pk)



from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


@login_required
@require_http_methods(["POST"])
def class_add_students(request, pk):
    """
    Legacy endpoint kept for backward compatibility.
    Class-level direct add is intentionally disabled to prevent enrollment misuse.
    """
    return JsonResponse({
        'success': False,
        'message': (
            'Direct class add is deprecated. '
            'Please use Course Enrolment for regular students, or Schedule Makeup for one-off attendance.'
        ),
        'deprecated': True,
    }, status=410)


@login_required
@require_http_methods(["GET"])
def class_makeup_candidates(request, pk):
    """
    Return student metadata and candidate classes for makeup scheduling.
    """
    class_instance = get_object_or_404(Class, pk=pk)

    if not _user_is_admin(request.user):
        return JsonResponse({
            'success': False,
            'message': 'Access denied. Only administrators can manage makeup sessions.'
        }, status=403)

    student_id = request.GET.get('student_id')
    initiated_from = request.GET.get('initiated_from', 'source')

    if not student_id:
        return JsonResponse({
            'success': False,
            'message': 'student_id is required.'
        }, status=400)

    from students.models import Student
    from enrollment.services import MakeupSessionService

    student = get_object_or_404(Student, pk=student_id)
    payload = MakeupSessionService.get_candidate_classes(
        student=student,
        current_class=class_instance,
        initiated_from=initiated_from,
        actor=request.user,
    )

    return JsonResponse({
        'success': True,
        **payload,
    })


@login_required
@require_http_methods(["POST"])
def class_schedule_makeup(request, pk):
    """
    AJAX endpoint to schedule a makeup session from either source or target class context.
    """
    try:
        class_instance = get_object_or_404(Class, pk=pk)
        import json
        data = json.loads(request.body)

        if not _user_is_admin(request.user):
            return JsonResponse({
                'success': False,
                'message': 'Access denied. Only administrators can manage makeup sessions.'
            }, status=403)

        student_id = data.get('student_id')
        initiated_from = data.get('initiated_from', 'source')
        reason_type = data.get('reason_type', 'student_request')
        notes = (data.get('notes') or '').strip()

        from students.models import Student
        from enrollment.services import MakeupSessionService

        if not student_id:
            return JsonResponse({
                'success': False,
                'message': 'Student is required.'
            }, status=400)

        student = get_object_or_404(Student, pk=student_id)

        if initiated_from == 'target':
            source_class_id = data.get('source_class_id')
            if not source_class_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Source class is required when initiating from target class.'
                }, status=400)
            source_class = get_object_or_404(Class, pk=source_class_id)
            target_class = class_instance
        else:
            target_class_id = data.get('target_class_id')
            if not target_class_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Target class is required when initiating from source class.'
                }, status=400)
            source_class = class_instance
            target_class = get_object_or_404(Class, pk=target_class_id)
            initiated_from = 'source'

        result = MakeupSessionService.schedule_session(
            student=student,
            source_class=source_class,
            target_class=target_class,
            initiated_from=initiated_from,
            reason_type=reason_type,
            notes=notes,
            actor=request.user,
        )

        warning = result.get('source_warning')
        message = 'Makeup session scheduled successfully.'
        if warning:
            message = f'{message} {warning}'

        return JsonResponse({
            'success': True,
            'message': message,
            'makeup_session_id': result['makeup_session'].id
        })

    except ValidationError as exc:
        return JsonResponse({
            'success': False,
            'message': '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
        }, status=400)
    except IntegrityError:
        return JsonResponse({
            'success': False,
            'message': 'A scheduled makeup already exists for this student and class pair.'
        }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data.'
        }, status=400)
    except Exception as exc:
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(exc)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def class_update_makeup_status(request, pk):
    """
    AJAX endpoint to update makeup session status from class detail page.
    """
    class_instance = get_object_or_404(Class, pk=pk)

    if not _user_is_admin(request.user):
        return JsonResponse({
            'success': False,
            'message': 'Access denied. Only administrators can manage makeup sessions.'
        }, status=403)

    try:
        import json
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data.'
        }, status=400)

    makeup_session_id = data.get('makeup_session_id')
    new_status = data.get('status')
    notes = (data.get('notes') or '').strip()

    if not makeup_session_id or not new_status:
        return JsonResponse({
            'success': False,
            'message': 'makeup_session_id and status are required.'
        }, status=400)

    from enrollment.models import MakeupSession
    from enrollment.services import MakeupSessionService

    makeup_session = get_object_or_404(
        MakeupSession,
        pk=makeup_session_id
    )
    if makeup_session.source_class_id != class_instance.id and makeup_session.target_class_id != class_instance.id:
        return JsonResponse({
            'success': False,
            'message': 'This makeup session does not belong to the selected class.'
        }, status=400)

    try:
        MakeupSessionService.update_session_status(
            makeup_session=makeup_session,
            new_status=new_status,
            actor=request.user,
            note=notes,
        )
    except ValidationError as exc:
        return JsonResponse({
            'success': False,
            'message': '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
        }, status=400)

    return JsonResponse({
        'success': True,
        'message': f'Makeup session marked as {makeup_session.get_status_display()}.'
    })
