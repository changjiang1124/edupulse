from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q, Prefetch
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from accounts.models import Staff
from core.utils.url_utils import build_absolute_url

from .models import Course, Class, CourseGroup
from .forms import CourseForm, CourseUpdateForm, ClassForm, ClassUpdateForm, CourseGroupForm
from .services import CourseWooCommerceService, CourseGroupCreationService


def _user_is_admin(user):
    return user.is_superuser or getattr(user, 'role', None) == 'admin'


class AdminRequiredMixin(UserPassesTestMixin):
    """Restrict access to administrators for management views."""

    def test_func(self):
        return _user_is_admin(self.request.user)


def _get_group_child_queryset(group, *, status='all'):
    queryset = group.courses.select_related('teacher', 'facility', 'classroom')
    if status != 'all':
        queryset = queryset.filter(status=status)
    return queryset.order_by('start_date', 'repeat_weekday', 'start_time', 'pk')


def _get_course_parent_redirect_url(course):
    if getattr(course, 'group_id', None):
        return reverse('academics:course_group_detail', kwargs={'pk': course.group_id})
    return reverse('academics:course_list')


def _duplicate_single_course(course_pk, include_enrollments=False,
                              new_start_date=None, new_end_date=None,
                              new_early_bird_deadline=None,
                              should_generate_classes=False):
    """
    Duplicate a single course.
    Returns (new_course, enrollment_count, classes_count, error_msg).
    """
    try:
        original = Course.objects.get(pk=course_pk)
    except Course.DoesNotExist:
        return None, 0, 0, f"Course {course_pk} not found."

    original_pk = original.pk
    original_name = original.name
    original_group = original.group

    # Clone the course by nulling pk (standard Django pattern)
    original.pk = None
    original.id = None
    original._state.adding = True
    if not original_group:
        original.name = f"{original_name} (Copy)"
    original.status = 'draft'
    original.external_id = None
    original.woocommerce_last_synced_at = None
    original.enrollment_deadline = None

    if new_start_date:
        original.start_date = new_start_date
    if new_end_date:
        original.end_date = new_end_date
    if new_early_bird_deadline:
        original.early_bird_deadline = new_early_bird_deadline

    if original_group:
        original.group = original_group
    original.save()
    new_course = original  # After save, this is the new course

    classes_count = 0
    if should_generate_classes:
        classes_count = new_course.generate_classes(replace_existing=True)

    enrollment_count = 0
    enrollment_error = None
    if include_enrollments:
        try:
            from enrollment.models import Enrollment
            from django.db import transaction
            original_enrollments = Enrollment.objects.filter(
                course_id=original_pk,
                status__in=['confirmed', 'pending', 'completed']
            )
            with transaction.atomic():
                for old_enrollment in original_enrollments:
                    Enrollment.objects.create(
                        student=old_enrollment.student,
                        course=new_course,
                        status='pending',
                        source_channel='staff',
                        registration_status='returning',
                        is_new_student=False,
                        matched_existing_student=True,
                        registration_fee_paid=False,
                        is_early_bird=new_course.is_early_bird_available(),
                        course_fee=new_course.get_applicable_price(),
                    )
                    enrollment_count += 1
        except ImportError:
            enrollment_error = "Enrolment module unavailable."
        except (IntegrityError, ValidationError) as e:
            enrollment_count = 0
            enrollment_error = str(e)

    return new_course, enrollment_count, classes_count, enrollment_error


class CourseDuplicateView(LoginRequiredMixin, View):
    """
    Duplicate an existing course.
    Copies the course with 'Draft' status and redirects to course list.
    Optionally includes existing enrollments as pending.
    """
    def post(self, request, pk):
        include_enrollments = request.POST.get('include_enrollments') == 'on'
        new_course, enrollment_count, _, error = _duplicate_single_course(
            pk, include_enrollments=include_enrollments
        )

        if new_course is None:
            messages.error(request, error or 'Failed to duplicate course.')
            return redirect('academics:course_list')

        enrollments_msg = ""
        if enrollment_count > 0:
            enrollments_msg = f" {enrollment_count} existing enrolments have been copied as 'Pending'."
        if error:
            enrollments_msg += f" However, there was an error copying enrolments: {error}"

        messages.success(
            request,
            f'Course duplicated successfully as "{new_course.name}" (Draft).{enrollments_msg} Please review the new course.'
        )
        return redirect(_get_course_parent_redirect_url(new_course))

    def get(self, request, pk):
        # Allow GET request for easier linking, but ideally should be POST
        return self.post(request, pk)


class BulkCourseDuplicateView(LoginRequiredMixin, View):
    """Duplicate multiple courses at once with optional date override and class generation."""

    @staticmethod
    def _parse_date(value, field_name):
        """Parse an optional date string. Returns (date_or_None, error_msg_or_None)."""
        if not value:
            return None, None
        try:
            return date.fromisoformat(value), None
        except ValueError:
            return None, f'Invalid {field_name} format.'

    def post(self, request):
        course_ids_str = request.POST.get('course_ids', '')
        include_enrollments = request.POST.get('include_enrollments') == 'on'
        should_generate_classes = request.POST.get('generate_classes') == 'on'
        confirm_duplicate = request.POST.get('confirm_bulk_duplicate') == 'on'

        if not confirm_duplicate:
            messages.error(request, 'Please review and confirm the bulk duplicate settings before duplicating courses.')
            return redirect('academics:course_list')

        # Parse course IDs
        try:
            ids = [int(x.strip()) for x in course_ids_str.split(',') if x.strip()]
        except ValueError:
            messages.error(request, 'Invalid course selection.')
            return redirect('academics:course_list')

        if not ids:
            messages.error(request, 'No courses selected for duplication.')
            return redirect('academics:course_list')

        MAX_BULK = 50
        if len(ids) > MAX_BULK:
            messages.error(request, f'Maximum {MAX_BULK} courses can be duplicated at once.')
            return redirect('academics:course_list')

        # Parse optional dates
        date_fields = [
            (request.POST.get('new_start_date') or None, 'start date'),
            (request.POST.get('new_end_date') or None, 'end date'),
            (request.POST.get('new_early_bird_deadline') or None, 'early bird deadline'),
        ]
        parsed_dates = []
        for value, name in date_fields:
            parsed, err = self._parse_date(value, name)
            if err:
                messages.error(request, err)
                return redirect('academics:course_list')
            parsed_dates.append(parsed)
        parsed_start, parsed_end, parsed_early_bird = parsed_dates

        success_count = 0
        enrollment_total = 0
        classes_total = 0
        errors = []

        for course_id in ids:
            new_course, enroll_count, cls_count, error = _duplicate_single_course(
                course_id,
                include_enrollments=include_enrollments,
                new_start_date=parsed_start,
                new_end_date=parsed_end,
                new_early_bird_deadline=parsed_early_bird,
                should_generate_classes=should_generate_classes,
            )
            if new_course is None:
                errors.append(error or f'Course {course_id} failed.')
            else:
                success_count += 1
                enrollment_total += enroll_count
                classes_total += cls_count
                if error:
                    errors.append(f"{new_course.name}: enrolment error - {error}")

        # Build result message
        msg_parts = [f'{success_count} course(s) duplicated successfully as Draft.']
        if enrollment_total > 0:
            msg_parts.append(f'{enrollment_total} enrolments copied as Pending.')
        if classes_total > 0:
            msg_parts.append(f'{classes_total} classes generated.')
        if errors:
            msg_parts.append(f'{len(errors)} error(s): {"; ".join(errors)}')

        msg = ' '.join(msg_parts)
        if errors:
            messages.warning(request, msg)
        else:
            messages.success(request, msg)

        return redirect('academics:course_list')


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
            sync_result = CourseWooCommerceService.save_course_and_sync(course)
            success_message = f'Course "{course.name}" has been archived.'
            if sync_result.get('status') == 'success':
                success_message = f'{success_message} {CourseWooCommerceService.get_success_suffix(course)}'
            messages.success(request, success_message)
            if sync_result.get('status') not in {'success', 'skipped'}:
                messages.warning(request, CourseWooCommerceService.get_failure_message(sync_result))
            
        return redirect(_get_course_parent_redirect_url(course))

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
            sync_result = CourseWooCommerceService.save_course_and_sync(course)
            success_message = f'Course "{course.name}" has been restored to Draft status.'
            if sync_result.get('status') == 'success':
                success_message = f'{success_message} {CourseWooCommerceService.get_success_suffix(course)}'
            messages.success(request, success_message)
            if sync_result.get('status') not in {'success', 'skipped'}:
                messages.warning(request, CourseWooCommerceService.get_failure_message(sync_result))
            
        return redirect(_get_course_parent_redirect_url(course))

    def get(self, request, pk):
        return self.post(request, pk)


class CourseDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete a draft course.
    """
    model = Course
    template_name = 'core/courses/course_confirm_delete.html'
    success_url = reverse_lazy('academics:course_list')

    def _get_blocking_response(self, request):
        self.object = self.get_object()
        parent_redirect = _get_course_parent_redirect_url(self.object)

        if self.object.enrollments.exists():
            enrollment_count = self.object.enrollments.count()
            messages.warning(
                request,
                f'Cannot delete course "{self.object.name}" because it has {enrollment_count} enrollment(s). '
                f'Please change the course status to "Archived" instead to preserve data integrity.'
            )
            return redirect(parent_redirect)

        if self.object.status != 'draft':
            messages.error(
                request,
                'Only draft courses can be deleted. Please archive published courses instead.'
            )
            return redirect(parent_redirect)

        return None

    def get_success_url(self):
        return _get_course_parent_redirect_url(self.object)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if course has enrollments and add to context for template warning
        context['has_enrollments'] = self.object.enrollments.exists()
        context['enrollment_count'] = self.object.enrollments.count()
        context['cancel_url'] = _get_course_parent_redirect_url(self.object)
        return context
    
    def get(self, request, *args, **kwargs):
        blocking_response = self._get_blocking_response(request)
        if blocking_response:
            return blocking_response
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        blocking_response = self._get_blocking_response(request)
        if blocking_response:
            return blocking_response
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        parent_redirect = _get_course_parent_redirect_url(self.object)
        try:
            course_name = self.object.name
            response = super().form_valid(form)
            messages.success(self.request, f'Course "{course_name}" has been deleted.')
            return response
        except ValidationError as e:
            # Fallback error handling in case model validation raises an error
            messages.error(self.request, ", ".join(e.messages))
            return redirect(parent_redirect)
        except ProtectedError:
            messages.error(
                self.request,
                f'Cannot delete course "{self.object.name}" because related records still exist.',
            )
            return redirect(parent_redirect)


class CourseGroupListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = CourseGroup
    template_name = 'core/course_groups/list.html'
    context_object_name = 'groups'
    paginate_by = 20

    def get_queryset(self):
        status_filter = self.request.GET.get('status', 'published')
        child_queryset = Course.objects.select_related('teacher', 'facility', 'classroom').order_by(
            'start_date', 'repeat_weekday', 'start_time', 'pk'
        )
        queryset = CourseGroup.objects.prefetch_related(
            Prefetch('courses', queryset=child_queryset)
        ).annotate(
            child_count=Count('courses', distinct=True),
            published_count=Count('courses', filter=Q(courses__status='published'), distinct=True),
            draft_count=Count('courses', filter=Q(courses__status='draft'), distinct=True),
            expired_count=Count('courses', filter=Q(courses__status='expired'), distinct=True),
            archived_count=Count('courses', filter=Q(courses__status='archived'), distinct=True),
        )

        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_status = self.request.GET.get('status', 'published')
        search = self.request.GET.get('search', '')
        base_queryset = CourseGroup.objects.all()
        if search:
            base_queryset = base_queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
        context['current_status'] = current_status
        context['counts'] = {
            'published': base_queryset.filter(status='published').count(),
            'draft': base_queryset.filter(status='draft').count(),
            'archived': base_queryset.filter(status='archived').count(),
            'all': base_queryset.count(),
        }
        return context


class CourseGroupCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = CourseGroup
    form_class = CourseGroupForm
    template_name = 'core/course_groups/form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Course group "{self.object.name}" created successfully.')
        return response

    def get_success_url(self):
        return reverse('academics:course_group_detail', kwargs={'pk': self.object.pk})


class CourseGroupDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = CourseGroup
    template_name = 'core/course_groups/detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        child_status = self.request.GET.get('child_status', 'all')
        child_courses = _get_group_child_queryset(self.object, status=child_status)
        context['child_status'] = child_status
        context['child_courses'] = child_courses
        context['public_url'] = build_absolute_url(self.object.get_public_url(), app_domain=True)
        context['child_counts'] = {
            'all': self.object.courses.count(),
            'published': self.object.courses.filter(status='published').count(),
            'draft': self.object.courses.filter(status='draft').count(),
            'expired': self.object.courses.filter(status='expired').count(),
            'archived': self.object.courses.filter(status='archived').count(),
        }
        return context


class CourseGroupUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = CourseGroup
    form_class = CourseGroupForm
    template_name = 'core/course_groups/form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Course group "{self.object.name}" updated successfully.')
        return response

    def get_success_url(self):
        return reverse('academics:course_group_detail', kwargs={'pk': self.object.pk})


class CourseGroupDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = CourseGroup
    template_name = 'core/course_groups/confirm_delete.html'
    success_url = reverse_lazy('academics:course_group_list')

    def _get_blocking_response(self, request):
        self.object = self.get_object()
        if self.object.courses.exists():
            messages.error(
                request,
                f'Cannot delete course group "{self.object.name}" because it still has child courses.',
            )
            return redirect('academics:course_group_detail', pk=self.object.pk)
        return None

    def get(self, request, *args, **kwargs):
        blocking_response = self._get_blocking_response(request)
        if blocking_response:
            return blocking_response
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        blocking_response = self._get_blocking_response(request)
        if blocking_response:
            return blocking_response
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        group_name = self.object.name
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f'Cannot delete course group "{self.object.name}" because it still has child courses.',
            )
            return redirect('academics:course_group_detail', pk=self.object.pk)
        messages.success(self.request, f'Course group "{group_name}" has been deleted.')
        return response


class CourseGroupPublicDetailView(DetailView):
    model = CourseGroup
    template_name = 'core/course_groups/public_detail.html'
    context_object_name = 'group'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return CourseGroup.objects.filter(status='published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child_courses'] = Course.publicly_enrollable_queryset().filter(
            group=self.object,
        ).select_related('teacher', 'facility', 'classroom').order_by(
            'start_date', 'repeat_weekday', 'start_time', 'pk'
        )
        return context


class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'core/courses/list.html'
    context_object_name = 'courses'
    paginate_by = 20

    def _get_selected_teacher(self):
        if hasattr(self, '_selected_teacher'):
            return self._selected_teacher

        teacher_id = self.request.GET.get('teacher')
        if not teacher_id:
            self._selected_teacher = None
            return self._selected_teacher

        try:
            self._selected_teacher = Staff.objects.get(pk=int(teacher_id))
        except (Staff.DoesNotExist, TypeError, ValueError):
            self._selected_teacher = None

        return self._selected_teacher
    
    def get_queryset(self):
        queryset = Course.objects.filter(group__isnull=True).select_related('teacher').annotate(
            enrollment_count=Count('enrollments')
        )

        # Filter by status (default to published)
        status_filter = self.request.GET.get('status', 'published')

        if status_filter != 'all':
            queryset = queryset.filter(status=status_filter)

        selected_teacher = self._get_selected_teacher()
        if selected_teacher is not None:
            queryset = queryset.filter(teacher=selected_teacher)

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
        selected_teacher = self._get_selected_teacher()
        context['courses'] = CourseWooCommerceService.attach_sync_summaries(context['courses'])

        context['current_status'] = current_status
        context['status_choices'] = Course.STATUS_CHOICES
        context['selected_teacher'] = selected_teacher
        context['selected_teacher_id'] = str(selected_teacher.pk) if selected_teacher else ''
        
        # Calculate counts for tabs
        base_queryset = Course.objects.filter(group__isnull=True)
        if selected_teacher is not None:
            base_queryset = base_queryset.filter(teacher=selected_teacher)

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

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get('group_pk') and request.user.is_authenticated and not _user_is_admin(request.user):
            raise PermissionDenied('Only administrators can create child courses from a course group.')
        return super().dispatch(request, *args, **kwargs)

    def get_group(self):
        if hasattr(self, '_group'):
            return self._group
        group_pk = self.kwargs.get('group_pk')
        self._group = get_object_or_404(CourseGroup, pk=group_pk) if group_pk else None
        return self._group

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        group = self.get_group()
        if group:
            kwargs['group'] = group
            kwargs['lock_group_fields'] = True
        return kwargs
    
    def form_valid(self, form):
        group = self.get_group()
        if group:
            CourseGroupCreationService.build_child_from_group(group=group, course=form.instance)

        CourseWooCommerceService.mark_manual_sync(form.instance)
        try:
            response = super().form_valid(form)
        finally:
            CourseWooCommerceService.clear_manual_sync(form.instance)

        sync_result = CourseWooCommerceService.sync_saved_course(self.object)
        should_generate_classes = self.request.POST.get('generate_classes') == 'on'
        classes_created = self.object.generate_classes() if should_generate_classes else 0
        success_message = f'Course "{self.object.name}" created successfully! {classes_created} class(es) generated.'
        if sync_result.get('status') == 'success':
            success_message = f'{success_message} {CourseWooCommerceService.get_success_suffix(self.object)}'
        messages.success(self.request, success_message)
        if sync_result.get('status') not in {'success', 'skipped'}:
            messages.warning(self.request, CourseWooCommerceService.get_failure_message(sync_result))
        return response

    def get_success_url(self):
        group = self.get_group()
        if group:
            return reverse('academics:course_group_detail', kwargs={'pk': group.pk})
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_group'] = self.get_group()
        return context


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
        context['woocommerce_summary'] = CourseWooCommerceService.build_sync_summary(self.object)
        context['selected_group'] = self.object.group
        context['group_public_url'] = (
            build_absolute_url(self.object.group.get_public_url(), app_domain=True)
            if self.object.group_id else ''
        )
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.object and self.object.group_id:
            kwargs['group'] = self.object.group
            kwargs['lock_group_fields'] = True
        return kwargs
    
    def form_valid(self, form):
        # Capture original repeat configuration from the database before saving
        original = Course.objects.get(pk=form.instance.pk)
        original_repeat_weekday = original.repeat_weekday

        CourseWooCommerceService.mark_manual_sync(form.instance)
        try:
            response = super().form_valid(form)
        finally:
            CourseWooCommerceService.clear_manual_sync(form.instance)

        sync_result = CourseWooCommerceService.sync_saved_course(self.object)

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
            if sync_result.get('status') == 'success':
                base_message = f'{base_message} {CourseWooCommerceService.get_success_suffix(self.object)}'
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
            success_message = 'Course updated successfully!'
            if sync_result.get('status') == 'success':
                success_message = f'{success_message} {CourseWooCommerceService.get_success_suffix(self.object)}'
            messages.success(self.request, success_message)

        if sync_result.get('status') not in {'success', 'skipped'}:
            messages.warning(self.request, CourseWooCommerceService.get_failure_message(sync_result))


        return response
    
    def get_success_url(self):
        return reverse_lazy('academics:course_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_group'] = self.object.group
        
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
            teachers = Staff.objects.filter(role='teacher', is_active=True)
            selected_teacher_id = context['selected_teacher']
            if selected_teacher_id:
                teachers = teachers | Staff.objects.filter(pk=selected_teacher_id)
            context['teachers'] = teachers.distinct().order_by('first_name', 'last_name')
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
