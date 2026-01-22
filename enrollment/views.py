import csv
import re

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView, View
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponse

from .models import Enrollment, Attendance
from .forms import EnrollmentForm, EnrollmentUpdateForm, PublicEnrollmentForm, StaffEnrollmentForm, EnrollmentTransferForm, BulkEnrollmentNotificationForm
from students.models import Student
from academics.models import Course
from core.models import OrganisationSettings
from core.services.notification_queue import (
    enqueue_enrollment_pending_email,
    enqueue_enrollment_confirmation_email,
    enqueue_enrollment_welcome_email,
    enqueue_new_enrollment_admin_notification,
)
from .services import EnrollmentAttendanceService



class AdminRequiredMixin(UserPassesTestMixin):
    """Admin permission check mixin"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'


class EnrollmentListView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'core/enrollments/list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Enrollment.objects.select_related('student', 'course').all()
        
        # Filter by student if specified
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        # Filter by course if specified
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
            
        # Filter by status if specified
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by course status (default to published)
        course_status = self.request.GET.get('course_status', 'published')
        if course_status and course_status != 'all':
            queryset = queryset.filter(course__status=course_status)
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter options
        context['students'] = Student.objects.all().order_by('first_name', 'last_name')
        # Show all courses in the filter dropdown, potentially grouped or indicated by status
        context['courses'] = Course.objects.all().order_by('name')
        context['course_status_choices'] = Course.STATUS_CHOICES
        # Pass current filter for UI state
        context['current_course_status'] = self.request.GET.get('course_status', 'published')
        return context


class EnrollmentDetailView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'core/enrollments/detail.html'
    context_object_name = 'enrollment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get other enrollments for this student
        context['other_enrollments'] = Enrollment.objects.filter(
            student=self.object.student
        ).exclude(
            pk=self.object.pk
        ).select_related('course')[:5]

        # Pre-calc price adjustment need for pending enrollments to drive UX hints
        if self.object.status == 'pending':
            try:
                from core.services.early_bird_pricing_service import EarlyBirdPricingService
                price_summary = EarlyBirdPricingService.get_price_adjustment_summary(self.object)
                context['price_adjustment_needed'] = bool(price_summary.get('needs_adjustment'))
                context['price_adjustment_summary'] = price_summary
            except Exception:
                context['price_adjustment_needed'] = False
                context['price_adjustment_summary'] = {}
        else:
            context['price_adjustment_needed'] = False
            context['price_adjustment_summary'] = {}
        
        return context
    
    def post(self, request, *args, **kwargs):
        from core.services.early_bird_pricing_service import EarlyBirdPricingService

        self.object = self.get_object()
        action = request.POST.get('action')

        if action == 'confirm' and self.object.status == 'pending':
            # Note: Price adjustment warning is shown via the yellow banner on the detail page
            # but we allow staff to confirm enrollment based on their judgment.
            # Staff may choose to honor early bird pricing or adjust it before/after confirmation.
            
            # Proceed with confirmation
            self.object.status = 'confirmed'
            self.object.save()

            # Check how many classes exist for automatic attendance creation
            active_classes = self.object.course.classes.filter(is_active=True)
            class_count = active_classes.count()

            # Create student activity record for enrollment confirmation
            from students.models import StudentActivity
            StudentActivity.create_activity(
                student=self.object.student,
                activity_type='enrollment_confirmed',
                title=f'Enrollment confirmed for {self.object.course.name}',
                description=f'Enrollment status changed from pending to confirmed by staff member. '
                           f'Attendance records automatically created for {class_count} existing classes.',
                enrollment=self.object,
                course=self.object.course,
                performed_by=request.user if hasattr(request.user, 'staff') else None,
                metadata={
                    'previous_status': 'pending',
                    'new_status': 'confirmed',
                    'confirmed_at': timezone.now().isoformat(),
                    'attendance_records_created': class_count
                }
            )

            # Send welcome email upon confirmation (queued)
            try:
                enqueue_result = enqueue_enrollment_welcome_email(self.object.id)
                welcome_sent = enqueue_result.get('queued') or enqueue_result.get('sent')
                job_id = enqueue_result.get('job_id')

                if welcome_sent:
                    # Record welcome email activity
                    StudentActivity.create_activity(
                        student=self.object.student,
                        activity_type='email_sent',
                        title='Welcome email sent',
                        description=f'Welcome email sent to {self.object.student.get_contact_email()} after enrollment confirmation',
                        enrollment=self.object,
                        course=self.object.course,
                        performed_by=request.user if hasattr(request.user, 'staff') else None,
                        metadata={
                            'email_type': 'welcome',
                            'recipient': self.object.student.get_contact_email(),
                            'triggered_by': 'enrollment_confirmation',
                            'job_id': job_id,
                        }
                    )
                    status_text = 'queued for sending' if enqueue_result.get('queued') else 'sent'
                    messages.success(
                        request,
                        f'Enrollment for {self.object.student.get_full_name()} has been confirmed and welcome email {status_text}. '
                        f'Attendance records automatically created for {class_count} existing classes.'
                    )
                else:
                    messages.success(
                        request,
                        f'Enrollment for {self.object.student.get_full_name()} has been confirmed, but welcome email could not be sent. '
                        f'Attendance records automatically created for {class_count} existing classes.'
                    )
            except Exception as e:
                messages.success(
                    request,
                    f'Enrollment for {self.object.student.get_full_name()} has been confirmed, but notification error: {str(e)}. '
                    f'Attendance records automatically created for {class_count} existing classes.'
                )

        return redirect('enrollment:enrollment_detail', pk=self.object.pk)


class AttendanceListView(AdminRequiredMixin, ListView):
    model = Attendance
    template_name = 'core/attendance/list.html'
    context_object_name = 'attendance_records'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Attendance.objects.select_related(
            'student', 'class_instance__course'
        ).all()
        
        # Filter by course if specified
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(class_instance__course_id=course_id)
        
        # Filter by date range if specified
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(class_instance__date__gte=date_from)
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(class_instance__date__lte=date_to)
            
        # Filter by student if specified
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
            
        return queryset.order_by('-class_instance__date', '-attendance_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        from academics.models import Course, Class
        context['courses'] = Course.objects.filter(status='published').order_by('name')
        
        # Get upcoming classes for attendance marking
        from django.utils import timezone
        today = timezone.now().date()
        next_week = today + timezone.timedelta(days=7)
        
        context['upcoming_classes'] = Class.objects.filter(
            date__gte=today,
            date__lte=next_week,
            is_active=True
        ).select_related('course').order_by('date', 'start_time')[:12]
        
        return context


class EnrollmentExportView(AdminRequiredMixin, View):
    """
    Export enrollments to CSV
    """
    def get(self, request, *args, **kwargs):
        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename="enrollments_export.csv"'},
        )

        response.write('\ufeff')
        writer = csv.writer(response)
        # Write header row
        writer.writerow([
            'Enrollment ID', 
            'Date', 
            'Student Name', 
            'Age',
            'Guardian Name',
            'Contact Email', 
            'Contact Phone', 
            'Course', 
            'Schedule',
            'Status', 
            'Payment Status', 
            'Total Fee',
            'Is New Student'
        ])

        # Get course status filter (default to published)
        course_status = request.GET.get('course_status', 'published')
        if course_status and course_status != 'all':
            enrollments = Enrollment.objects.filter(
                course__status=course_status
            )
        else:
            enrollments = Enrollment.objects.all()

        student_id = request.GET.get('student')
        if student_id:
            enrollments = enrollments.filter(student_id=student_id)

        course_id = request.GET.get('course')
        if course_id:
            enrollments = enrollments.filter(course_id=course_id)

        status = request.GET.get('status')
        if status:
            enrollments = enrollments.filter(status=status)

        enrollments = enrollments.select_related('student', 'course').order_by('-created_at')

        for enrollment in enrollments:
            student = enrollment.student
            course = enrollment.course
            
            # Helper to safely get student attribute
            student_age = student.get_age() if student.birth_date else 'N/A'
            
            # Determine payment status (simplified logic based on model)
            payment_status = 'Paid' if enrollment.is_fully_paid() else 'Pending'
            
            writer.writerow([
                enrollment.get_reference_id(),
                enrollment.created_at.strftime('%Y-%m-%d'),
                student.get_full_name(),
                student_age,
                student.guardian_name,
                student.get_contact_email(),
                student.get_contact_phone(),
                course.name,
                course.schedule_display(),
                enrollment.get_status_display(),
                payment_status,
                enrollment.get_total_fee(),
                'Yes' if enrollment.is_new_student else 'No'
            ])

        return response


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    """Create enrollment (staff use) - Legacy view, redirects to enhanced version"""
    
    def get(self, request, *args, **kwargs):
        # Redirect to the enhanced staff enrollment creation view
        return redirect('enrollment:staff_enrollment_create')
    
    def post(self, request, *args, **kwargs):
        # Redirect to the enhanced staff enrollment creation view
        return redirect('enrollment:staff_enrollment_create')


class StaffEnrollmentCreateView(LoginRequiredMixin, TemplateView):
    """
    Enhanced enrollment creation view for staff members with student search and creation
    """
    template_name = 'core/enrollments/staff_create.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow staff members to access this view
        if not request.user.is_staff:
            messages.error(request, 'Access denied. Staff members only.')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get course_id from URL if provided
        course_id = self.kwargs.get('course_id')
        selected_course = None
        
        # Get form instances
        enrollment_form = StaffEnrollmentForm(
            course_id=course_id, 
            user=self.request.user
        )
        
        context.update({
            'enrollment_form': enrollment_form,
            'course_id': course_id,
        })
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = Course.objects.get(pk=course_id)
                context['selected_course'] = selected_course
                context['page_title'] = f'Add Enrolment - {selected_course.name}'
            except Course.DoesNotExist:
                messages.error(self.request, 'Course not found.')
                return redirect('academics:course_list')
        else:
            context['page_title'] = 'Create New Enrolment'
        
        return context
    
    def post(self, request, *args, **kwargs):
        course_id = self.kwargs.get('course_id')
        action = request.POST.get('action', 'create_enrollment')
        
        if action == 'create_enrollment':
            return self._handle_enrollment_creation(request, course_id)
        else:
            messages.error(request, 'Invalid action.')
            return self.get(request, *args, **kwargs)
    

    
    def _handle_enrollment_creation(self, request, course_id):
        """Handle enrollment creation"""
        enrollment_form = StaffEnrollmentForm(
            request.POST, 
            course_id=course_id, 
            user=request.user
        )
        
        if enrollment_form.is_valid():
            try:
                enrollment = enrollment_form.save()

                # Check if we should send enrollment notification email
                send_email = enrollment.form_data.get('send_confirmation_email', True)

                # Send enrollment confirmation email if requested and status is pending
                if send_email and enrollment.status == 'pending':
                    email_sent = self._send_enrollment_notification(enrollment)
                    if email_sent:
                        messages.success(request, 'Enrollment created and confirmation email sent.')
                    else:
                        messages.warning(request, 'Enrollment created but email could not be sent.')
                elif not send_email:
                    messages.success(request, 'Enrollment created. No email sent as requested.')
                else:
                    messages.success(request, 'Enrollment created with confirmed status.')

                # Create student activity record for enrollment creation
                from students.models import StudentActivity
                StudentActivity.create_activity(
                    student=enrollment.student,
                    activity_type='enrollment_created',
                    title=f'Enrollment created by staff for {enrollment.course.name}',
                    description=f'Staff member created enrollment for {enrollment.student.get_full_name()} '
                               f'in {enrollment.course.name}. Status: {enrollment.get_status_display()}. '
                               f'Email sent: {"Yes" if send_email and enrollment.status == "pending" else "No"}',
                    enrollment=enrollment,
                    course=enrollment.course,
                    performed_by=request.user if hasattr(request.user, 'staff') else None,
                    metadata={
                        'created_by_staff': True,
                        'email_sent': send_email and enrollment.status == 'pending',
                        'source_channel': 'staff'
                    }
                )
                
                # Redirect based on context
                if course_id:
                    return redirect('academics:course_detail', pk=course_id)
                else:
                    return redirect('enrollment:enrollment_detail', pk=enrollment.pk)
                    
            except Exception as e:
                messages.error(request, f'Error creating enrollment: {str(e)}')
                
        # If form is not valid, re-render with errors
        context = self.get_context_data()
        context['enrollment_form'] = enrollment_form
        return render(request, self.template_name, context)
    
    def _send_enrollment_notification(self, enrollment):
        """Send enrollment confirmation email with fee information and return success status"""
        try:
            from core.services.early_bird_pricing_service import EarlyBirdPricingService

            # Check for price adjustment before sending email
            price_check = EarlyBirdPricingService.check_price_adjustment_needed(enrollment)

            if price_check['needs_adjustment']:
                # Log the price adjustment need but proceed with current enrollment values
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Price adjustment needed for enrollment {enrollment.id} during staff creation, "
                    f"but proceeding with current values: {price_check['reason']}"
                )

            # Use enrollment's calculated fees (which include early bird pricing)
            course_fee = enrollment.course_fee or enrollment.course.get_applicable_price()
            registration_fee = enrollment.registration_fee or 0
            total_fee = course_fee + registration_fee

            # Get contact information
            contact_info = enrollment.student.get_contact_email()
            if not contact_info and hasattr(enrollment, 'form_data'):
                contact_info = enrollment.form_data.get('contact_info', {}).get('primary_email')

            if contact_info:
                enqueue_result = enqueue_enrollment_pending_email(
                    enrollment_id=enrollment.id,
                    recipient_email=contact_info,
                    fee_breakdown={
                        'course_fee': course_fee,
                        'registration_fee': registration_fee,
                        'total_fee': total_fee,
                        'charge_registration_fee': registration_fee > 0,
                        'has_registration_fee': registration_fee > 0,
                        'is_early_bird': enrollment.is_early_bird,
                        'original_price': enrollment.original_price,
                        'early_bird_savings': enrollment.early_bird_savings
                    }
                )
                return enqueue_result.get('queued') or enqueue_result.get('sent')
            else:
                # No email address available
                return False

        except Exception as e:
            # Log error but don't fail the enrollment creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send enrollment notification for enrollment {enrollment.id}: {str(e)}")
            return False


class StudentSearchAPIView(LoginRequiredMixin, View):
    """
    AJAX API for student search functionality
    """
    
    def get(self, request):
        if not request.user.is_staff:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        from .forms import StudentSearchForm
        form = StudentSearchForm(request.GET)
        
        if form.is_valid():
            results = form.search_students()
            return JsonResponse({
                'success': True,
                'results': results
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })


class EnrollmentUpdateView(LoginRequiredMixin, UpdateView):
    """Enhanced enrollment update view with comprehensive form and email notifications"""
    model = Enrollment
    form_class = EnrollmentUpdateForm
    template_name = 'core/enrollments/update.html'
    success_url = reverse_lazy('enrollment:enrollment_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        # Redirect to enrollment detail page after successful update
        return reverse_lazy('enrollment:enrollment_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        from core.services.early_bird_pricing_service import EarlyBirdPricingService

        # Get original status before saving
        original_status = self.object.status

        # Save the enrollment
        enrollment = form.save()

        # Check if status changed and if price adjustment might be needed
        status_changed = enrollment.status != original_status

        if status_changed:
            # Check if price adjustment is needed for status changes
            price_check = EarlyBirdPricingService.check_price_adjustment_needed(enrollment)

            if price_check['needs_adjustment']:
                # Store price check data for frontend handling
                enrollment.form_data = enrollment.form_data or {}
                enrollment.form_data.update({
                    'price_adjustment_needed': True,
                    'price_check_data': EarlyBirdPricingService.get_price_adjustment_summary(enrollment),
                    'status_changed': status_changed,
                    'original_status': original_status
                })
                enrollment.save()

                # Return JSON response for AJAX handling
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'needs_price_adjustment': True,
                        'enrollment_id': enrollment.id,
                        'price_check_data': enrollment.form_data['price_check_data'],
                        'message': 'Price adjustment required before proceeding'
                    })

        # Check if we should send update notification
        send_notification = enrollment.form_data.get('send_update_notification', False)

        # Send notification if requested and status changed to specific states
        if send_notification and status_changed:
            email_sent = self._send_update_notification(enrollment, original_status)
            if email_sent:
                messages.success(
                    self.request,
                    f'Enrollment updated successfully for {enrollment.student.get_full_name()}. '
                    f'Status changed from {original_status} to {enrollment.get_status_display()}. '
                    f'Update notification email sent.'
                )
            else:
                messages.warning(
                    self.request,
                    f'Enrollment updated successfully but email notification could not be sent.'
                )
        elif send_notification and not status_changed:
            messages.info(
                self.request,
                f'Enrollment updated successfully. No email sent as status did not change.'
            )
        else:
            messages.success(
                self.request,
                f'Enrollment updated successfully for {enrollment.student.get_full_name()}.'
            )

        # Create student activity record for enrollment update
        from students.models import StudentActivity
        StudentActivity.create_activity(
            student=enrollment.student,
            activity_type='enrollment_updated' if not status_changed else 'enrollment_status_changed',
            title=f'Enrollment updated by staff for {enrollment.course.name}',
            description=f'Staff member updated enrollment for {enrollment.student.get_full_name()} '
                       f'in {enrollment.course.name}. '
                       f'{"Status changed from " + original_status + " to " + enrollment.get_status_display() + ". " if status_changed else ""}'
                       f'Email sent: {"Yes" if send_notification and status_changed else "No"}',
            enrollment=enrollment,
            course=enrollment.course,
            performed_by=self.request.user if hasattr(self.request.user, 'staff') else None,
            metadata={
                'updated_by_staff': True,
                'status_changed': status_changed,
                'original_status': original_status,
                'new_status': enrollment.status,
                'email_sent': send_notification and status_changed
            }
        )

        return super().form_valid(form)

    def _send_update_notification(self, enrollment, original_status):
        """Send enrollment update notification email and return success status"""
        try:
            # Get contact information
            contact_info = enrollment.student.get_contact_email()
            if not contact_info and hasattr(enrollment, 'form_data'):
                additional_info = enrollment.form_data.get('additional_student_info', {})
                contact_info = additional_info.get('student_email')

            if not contact_info:
                return False

            # Determine email type based on status change
            if enrollment.status == 'confirmed' and original_status == 'pending':
                # Send confirmation email
                enqueue_result = enqueue_enrollment_confirmation_email(enrollment.id)
                notification_sent = enqueue_result.get('queued') or enqueue_result.get('sent')
            elif enrollment.status == 'cancelled':
                # Send cancellation email (if such method exists)
                # For now, we'll use a generic update notification
                notification_sent = self._send_generic_update_email(enrollment, original_status, contact_info)
            else:
                # Send generic update notification
                notification_sent = self._send_generic_update_email(enrollment, original_status, contact_info)

            return notification_sent

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send update notification for enrollment {enrollment.id}: {str(e)}")
            return False

    def _send_generic_update_email(self, enrollment, original_status, contact_info):
        """Send a generic enrollment update email"""
        try:
            from django.core.mail import EmailMultiAlternatives
            from django.template.loader import render_to_string
            from django.contrib.sites.models import Site
            from core.models import OrganisationSettings

            site = Site.objects.get_current()
            org_settings = OrganisationSettings.get_instance()

            # Prepare context for email template
            context = {
                'enrollment': enrollment,
                'student': enrollment.student,
                'course': enrollment.course,
                'original_status': original_status,
                'new_status': enrollment.get_status_display(),
                'recipient_name': enrollment.student.guardian_name or enrollment.student.get_full_name(),
                'site_domain': org_settings.site_domain,
                'contact_email': org_settings.contact_email,
                'contact_phone': org_settings.contact_phone,
            }

            # Create simple update email
            subject = f"Enrollment Update - {enrollment.course.name}"

            # Simple text content for now
            text_content = f"""
Dear {context['recipient_name']},

Your enrollment in {enrollment.course.name} has been updated.

Status changed from: {original_status.title()}
Status changed to: {enrollment.get_status_display()}

If you have any questions, please contact us at {org_settings.contact_email} or {org_settings.contact_phone}.

Best regards,
{org_settings.school_name or 'Perth Art School'}
            """

            # Create and send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[contact_info],
                reply_to=[org_settings.reply_to_email],
            )

            email.send()
            return True

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send generic update email: {str(e)}")
            return False


class EnrollmentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete enrollment (staff use)"""
    model = Enrollment
    template_name = 'core/enrollments/delete.html'
    success_url = reverse_lazy('enrollment:enrollment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Enrollment deleted successfully.')
        return super().delete(request, *args, **kwargs)


class PublicEnrollmentView(TemplateView):
    """Public enrollment page (no login required)"""
    template_name = 'core/enrollments/public_enrollment.html'
    
    def _get_course_sort_key(self, course):
        """
        Generate sort key for courses: Group -> Weekday -> StartTime -> Name.
        This ensures courses are grouped by their main name (e.g. "13/17 Yrs - Artisan Studio")
        and then sorted chronologically (Monday to Sunday) within that group.
        """
        DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        name = course.name
        
        # Default values
        group = name
        weekday = 999
        
        # Regex to find the first occurrence of a day name
        # We look for Day names like "Monday", "Tuesday", etc.
        pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
        match = re.search(pattern, name, re.IGNORECASE)
        
        if match:
            # Extract day
            day_str = match.group(1).title()
            try:
                weekday = DAYS.index(day_str)
            except ValueError:
                pass
            
            # Extract Group (everything before the day)
            start_idx = match.start()
            group_candidate = name[:start_idx].strip()
            # Remove trailing separators like " - "
            group = group_candidate.rstrip(' -')
            
        return (group, weekday, name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            org_settings = OrganisationSettings.get_instance()
            context['organisation_settings'] = org_settings
            context['site_domain'] = getattr(org_settings, 'site_domain', 'perthartschool.com.au')
        except Exception:
            context['organisation_settings'] = None
            context['site_domain'] = 'perthartschool.com.au'
        
        # Get course_id from URL path parameter or query parameter
        course_id = self.kwargs.get('course_id') or self.request.GET.get('course')
        selected_course = None
        
        # Only show published courses that allow online bookings
        courses_qs = Course.objects.filter(
            status='published', 
            is_online_bookable=True
        )
        
        # Sort courses by Group -> Weekday -> Name using the helper method
        courses = sorted(courses_qs, key=self._get_course_sort_key)
        context['courses'] = courses
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = courses_qs.get(pk=course_id)
                context['selected_course'] = selected_course
            except Course.DoesNotExist:
                # If course doesn't exist or isn't bookable, don't pre-select any course
                selected_course = None
        
        # Prepare course fee data for frontend dynamic calculation
        course_fees_data = {}
        for course in courses:
            # Calculate fees
            applicable_price = course.get_applicable_price()
            is_early_bird = course.is_early_bird_available()
            
            course_fees_data[course.pk] = {
                'price': float(applicable_price),
                'registration_fee': float(course.registration_fee or 0),
                'has_registration_fee': course.has_registration_fee(),
                'is_early_bird': is_early_bird,
                'early_bird_savings': float(course.get_early_bird_savings()) if is_early_bird else 0,
                'price_display': course.get_price_display(show_gst_label=False, show_early_bird_info=False)
            }

        context['course_fees_data'] = course_fees_data
        
        # Initialize form with selected course if available
        initial_data = {}
        if selected_course:
            initial_data['course_id'] = selected_course.pk
            
        context['form'] = PublicEnrollmentForm(initial=initial_data, courses=courses)
        return context
    
    def post(self, request, *args, **kwargs):
        # Get course_id from URL path parameter or query parameter
        course_id = self.kwargs.get('course_id') or request.GET.get('course')
        selected_course = None
        
        courses_qs = Course.objects.filter(status='published', is_online_bookable=True)
        
        # Sort courses by Group -> Weekday -> Name using the helper method
        courses = sorted(courses_qs, key=self._get_course_sort_key)
        
        # Pass sorted courses to form
        form = PublicEnrollmentForm(request.POST, courses=courses)
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = courses_qs.get(pk=course_id)
            except Course.DoesNotExist:
                # If course doesn't exist or isn't bookable, add error and continue
                messages.error(request, 'The selected course is not available for online booking.')
                selected_course = None
        
        if form.is_valid():
            from students.services import StudentMatchingService, EnrollmentFeeCalculator
            
            # Get course
            course = Course.objects.get(pk=form.cleaned_data['course_id'])
            
            # Convert form data to JSON-serializable format
            serializable_form_data = {}
            for key, value in form.cleaned_data.items():
                if hasattr(value, 'isoformat'):  # Handle date/datetime objects
                    serializable_form_data[key] = value.isoformat()
                elif hasattr(value, 'pk'):  # Handle Django model objects (like Course)
                    serializable_form_data[key] = value.pk
                elif value is None:
                    serializable_form_data[key] = None
                else:
                    # Convert to string for safety, preserving original data
                    serializable_form_data[key] = str(value) if not isinstance(value, (int, float, bool, str, list, dict)) else value
            
            # Use student matching service to create or find student first
            student, was_created = StudentMatchingService.create_or_update_student(
                form.cleaned_data, None  # Pass None for enrollment initially
            )
            
            # Check for duplicate active enrollments (excluding cancelled)
            existing_enrollment = Enrollment.objects.filter(
                student=student,
                course=course
            ).exclude(status='cancelled')
            
            if existing_enrollment.exists():
                existing = existing_enrollment.first()
                messages.error(
                    request, 
                    f'You already have an active enrollment in {course.name}. '
                    f'Current status: {existing.get_status_display()}. '
                    f'Please contact us if you need to modify your existing enrollment.'
                )
                # Return to form with error
                context = self.get_context_data(**kwargs)
                context['form'] = form
                context['selected_course'] = selected_course
                context['courses'] = courses
                return self.render_to_response(context)
            
            # Determine registration status based on student_status from form
            student_status = form.cleaned_data.get('student_status', 'new')
            
            # Now create enrollment with the student
            enrollment = Enrollment.objects.create(
                student=student,
                course=course,
                status='pending',
                source_channel='website',
                registration_status=student_status,  # Use the status from the form
                original_form_data=serializable_form_data,
                is_new_student=was_created,
                matched_existing_student=not was_created
            )
            
            # Calculate and set enrollment fees
            fees = EnrollmentFeeCalculator.update_enrollment_fees(
                enrollment, course, enrollment.is_new_student
            )
            
            # Check if enrollment already exists for this course
            existing_enrollment = Enrollment.objects.filter(
                student=student, 
                course=course
            ).exclude(pk=enrollment.pk).first()
            
            if existing_enrollment:
                # Delete the temp enrollment we just created
                enrollment.delete()
                
                messages.warning(
                    request, 
                    f'Enrollment already exists for {student.get_full_name()} in {course.name}. Status: {existing_enrollment.get_status_display()}'
                )
                return redirect('enrollment:enrollment_success', enrollment_id=existing_enrollment.pk)
            else:
                # Create student activity record for enrollment creation
                from students.models import StudentActivity
                StudentActivity.create_activity(
                    student=student,
                    activity_type='enrollment_created',
                    title=f'Enrolled in {course.name}',
                    description=f'Student enrolled in course "{course.name}" via website form. Status: pending.',
                    enrollment=enrollment,
                    course=course,
                    metadata={
                        'source_channel': 'website',
                        'form_data_stored': True,
                        'fees_calculated': True,
                        'is_new_student': was_created,
                        'total_fee': str(fees.get('total_fee', 0))
                    }
                )
                
                # Process enrollment notifications
                try:
                    # Send pending email with fee information
                    enqueue_result = enqueue_enrollment_pending_email(
                        enrollment_id=enrollment.id,
                        recipient_email=student.get_contact_email(),
                        fee_breakdown={
                            'course_fee': fees.get('course_fee', 0),
                            'registration_fee': fees.get('registration_fee', 0),
                            'total_fee': fees.get('total_fee', 0),
                            'has_registration_fee': fees.get('has_registration_fee', False),
                            'charge_registration_fee': fees.get('has_registration_fee', False),
                            'is_early_bird': fees.get('is_early_bird', False),
                            'original_price': fees.get('original_price'),
                            'early_bird_savings': fees.get('early_bird_savings')
                        }
                    )
                    
                    if enqueue_result.get('queued'):
                        messages.success(request, 'Enrollment pending email queued for sending.')
                    elif enqueue_result.get('sent'):
                        messages.success(request, 'Enrollment pending email sent.')
                    else:
                        messages.warning(request, 'Enrollment created but pending email could not be sent.')

                    if enqueue_result.get('queued') or enqueue_result.get('sent'):
                        # Record email sent activity
                        StudentActivity.create_activity(
                            student=student,
                            activity_type='email_sent',
                            title='Enrollment pending email sent',
                            description=f'Pending payment email sent to {student.get_contact_email()}',
                            enrollment=enrollment,
                            course=course,
                            metadata={
                                'email_type': 'enrollment_pending',
                                'recipient': student.get_contact_email()
                            }
                        )
                    
                    # Notify organisation admins about the new enrollment
                    try:
                        enqueue_new_enrollment_admin_notification(enrollment.id)
                    except Exception as admin_notify_exc:
                        # Don't fail the enrollment if admin notification fails
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning("Admin notification failed for enrollment %s: %s", enrollment.id, admin_notify_exc)
                        
                except Exception as e:
                    messages.warning(request, f'Enrollment created but notification error: {str(e)}')
                
                success_message = f'Enrollment submitted successfully for {student.get_full_name()} in {course.name}.'
                if was_created:
                    success_message += ' New student profile created.'
                else:
                    success_message += ' Existing student record updated.'

                # Add pricing information with early bird details
                if fees.get('is_early_bird'):
                    success_message += f' Early Bird price: ${fees["course_fee"]} (Save ${fees["early_bird_savings"]})!'
                    if fees['has_registration_fee']:
                        success_message += f' Total fee: ${fees["total_fee"]} (includes ${fees["registration_fee"]} registration fee).'
                    else:
                        success_message += f' Course fee: ${fees["course_fee"]}.'
                else:
                    if fees['has_registration_fee']:
                        success_message += f' Total fee: ${fees["total_fee"]} (includes ${fees["registration_fee"]} registration fee).'
                    else:
                        success_message += f' Course fee: ${fees["course_fee"]}.'
                
                messages.success(request, success_message)
                return redirect('enrollment:enrollment_success', enrollment_id=enrollment.pk)
        
        # Form validation failed - prepare context for re-rendering
        context = self.get_context_data(**kwargs)
        context.update({
            'form': form,
            'courses': courses
        })
        
        # Add selected course context if applicable
        if selected_course:
            context['selected_course'] = selected_course
            
        return render(request, self.template_name, context)


class EnrollmentSuccessView(TemplateView):
    """Enrollment success page"""
    template_name = 'core/enrollments/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment_id = self.kwargs.get('enrollment_id')
        if enrollment_id:
            context['enrollment'] = get_object_or_404(Enrollment, pk=enrollment_id)
        
        # Add organisation contact details for template rendering
        try:
            org_settings = OrganisationSettings.get_instance()
            context['organisation_settings'] = org_settings
            context['contact_email'] = getattr(org_settings, 'contact_email', '')
            context['contact_phone'] = getattr(org_settings, 'contact_phone', '')
            context['site_domain'] = getattr(org_settings, 'site_domain', 'perthartschool.com.au')
        except Exception:
            # Fallbacks to ensure page doesn't break if settings not configured
            from django.conf import settings as dj_settings
            context['contact_email'] = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', 'info@perthartschool.com.au')
            context['contact_phone'] = ''
            context['organisation_settings'] = None
            context['site_domain'] = 'perthartschool.com.au'
        
        return context


class AttendanceMarkView(LoginRequiredMixin, View):
    """Enhanced attendance marking view with batch processing"""
    template_name = 'core/attendance/mark.html'
    
    def get_context_data(self, class_instance, form=None):
        """Prepare context for both GET and POST requests"""
        context = {
            'class_instance': class_instance,
            'course': class_instance.course,
        }
        
        # Get enrolled students for this course
        enrolled_students = class_instance.course.enrollments.filter(
            status='confirmed'
        ).select_related('student')
        context['enrolled_students'] = enrolled_students
        
        # Get existing attendance records
        existing_attendance = class_instance.attendances.select_related('student').all()
        context['existing_attendance'] = existing_attendance
        
        # Also provide as dict for quick lookup
        existing_attendance_dict = {
            att.student.id: att for att in existing_attendance
        }
        context['existing_attendance_dict'] = existing_attendance_dict
        
        # Add form to context
        if form is None:
            from .forms import BulkAttendanceForm
            form = BulkAttendanceForm(class_instance=class_instance)
        context['form'] = form
        
        # Add student field data for easier template rendering
        context['student_fields'] = form.get_student_fields() if hasattr(form, 'get_student_fields') else []
        
        return context
    
    def get(self, request, class_id):
        """Display attendance marking form"""
        from academics.models import Class
        class_instance = get_object_or_404(Class, pk=class_id)
        
        # Permission check - admin can access all classes, teachers only their own
        if (hasattr(request.user, 'role') and request.user.role == 'teacher' and 
            class_instance.course.teacher != request.user):
            messages.error(request, 'You can only mark attendance for your own classes.')
            return redirect('academics:class_list')
        
        context = self.get_context_data(class_instance)
        return render(request, self.template_name, context)
    
    def post(self, request, class_id):
        """Process bulk attendance form submission"""
        from academics.models import Class
        from .forms import BulkAttendanceForm
        
        class_instance = get_object_or_404(Class, pk=class_id)
        
        # Permission check - admin can access all classes, teachers only their own
        if (hasattr(request.user, 'role') and request.user.role == 'teacher' and 
            class_instance.course.teacher != request.user):
            messages.error(request, 'You can only mark attendance for your own classes.')
            return redirect('academics:class_list')
        
        form = BulkAttendanceForm(request.POST, class_instance=class_instance)
        
        if form.is_valid():
            try:
                created_count, updated_count = form.save_attendance(class_instance)
                
                success_msg = f'Attendance updated successfully! '
                if created_count:
                    success_msg += f'{created_count} new records created. '
                if updated_count:
                    success_msg += f'{updated_count} existing records updated.'
                
                messages.success(request, success_msg)
                return redirect('enrollment:attendance_mark', class_id=class_id)
                
            except Exception as e:
                messages.error(request, f'Error saving attendance: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors in the form.')
        
        context = self.get_context_data(class_instance, form)
        return render(request, self.template_name, context)


class StudentSearchView(LoginRequiredMixin, View):
    """AJAX student search endpoint"""
    
    def get(self, request):
        """Handle AJAX student search requests"""
        from django.http import JsonResponse
        from .forms import StudentSearchForm
        
        form = StudentSearchForm(request.GET)
        
        if form.is_valid():
            results = form.search_students()
            return JsonResponse({
                'success': True,
                'results': results,
                'count': len(results)
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)


class AttendanceUpdateView(LoginRequiredMixin, UpdateView):
    """Update individual attendance record"""
    model = Attendance
    template_name = 'core/attendance/update.html'
    fields = ['status', 'attendance_time']

    def get_success_url(self):
        return reverse('enrollment:attendance_mark',
                      kwargs={'class_id': self.object.class_instance.id})

    def form_valid(self, form):
        messages.success(self.request,
                        f'Attendance updated for {self.object.student.get_full_name()}')
        return super().form_valid(form)


class SendEnrollmentEmailView(LoginRequiredMixin, View):
    """AJAX endpoint to manually send enrollment emails"""

    def post(self, request, pk):
        """Handle email sending requests"""
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

        try:
            enrollment = get_object_or_404(Enrollment, pk=pk)
            email_type = request.POST.get('email_type')

            if email_type not in ['pending', 'confirmation']:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid email type. Must be "pending" or "confirmation".'
                }, status=400)

            # Check for price adjustment before sending email
            from core.services.early_bird_pricing_service import EarlyBirdPricingService

            price_check = EarlyBirdPricingService.check_price_adjustment_needed(enrollment)

            if price_check['needs_adjustment']:
                # Return price adjustment needed response
                return JsonResponse({
                    'needs_price_adjustment': True,
                    'enrollment_id': enrollment.id,
                    'price_check_data': EarlyBirdPricingService.get_price_adjustment_summary(enrollment),
                    'message': 'Price adjustment required before sending email',
                    'email_type': email_type  # Include the requested email type for later use
                })

            # Get recipient email
            recipient_email = enrollment.student.get_contact_email()
            if not recipient_email:
                return JsonResponse({
                    'success': False,
                    'error': 'No email address found for this student.'
                }, status=400)

            from students.models import StudentActivity
            job_id = None

            if email_type == 'pending':
                # Send enrollment pending email (for pending status)
                if enrollment.status != 'pending':
                    return JsonResponse({
                        'success': False,
                        'error': 'Enrollment pending email can only be sent for pending enrollments.'
                    }, status=400)

                # Calculate fees for email using enrollment's stored values
                fee_breakdown = {
                    'course_fee': enrollment.course_fee or enrollment.course.get_applicable_price(),
                    'registration_fee': enrollment.registration_fee or 0,
                    'total_fee': enrollment.get_total_fee(),
                    'charge_registration_fee': enrollment.registration_fee > 0,
                    'has_registration_fee': enrollment.registration_fee > 0,
                    'is_early_bird': enrollment.is_early_bird,
                    'original_price': enrollment.original_price,
                    'early_bird_savings': enrollment.early_bird_savings
                }

                enqueue_result = enqueue_enrollment_pending_email(
                    enrollment_id=enrollment.id,
                    recipient_email=recipient_email,
                    fee_breakdown=fee_breakdown
                )
                email_sent = enqueue_result.get('queued') or enqueue_result.get('sent')
                job_id = enqueue_result.get('job_id')
                email_description = 'enrollment pending'
                if enqueue_result.get('queued'):
                    email_description = 'enrollment pending (queued)'

            elif email_type == 'confirmation':
                # Send enrollment confirmation/welcome email (for confirmed status)
                if enrollment.status != 'confirmed':
                    return JsonResponse({
                        'success': False,
                        'error': 'Enrollment confirmation email can only be sent for confirmed enrollments.'
                    }, status=400)

                enqueue_result = enqueue_enrollment_welcome_email(enrollment.id)
                email_sent = enqueue_result.get('queued') or enqueue_result.get('sent')
                job_id = enqueue_result.get('job_id')
                email_description = 'welcome'
                if enqueue_result.get('queued'):
                    email_description = 'welcome (queued)'

            if email_sent:
                # Record activity
                activity_email_type = 'pending' if email_type == 'pending' else 'welcome'
                StudentActivity.create_activity(
                    student=enrollment.student,
                    activity_type='email_sent',
                    title=f'Manual {email_description} email sent',
                    description=f'{email_description.title()} email manually sent to {recipient_email} by staff member',
                    enrollment=enrollment,
                    course=enrollment.course,
                    performed_by=request.user if hasattr(request.user, 'staff') else None,
                    metadata={
                        'email_type': email_description,
                        'email_type_code': activity_email_type,
                        'recipient': recipient_email,
                        'triggered_by': 'manual_staff_action',
                        'staff_user': request.user.username,
                        'price_adjustment_checked': True
                    }
                )

                return JsonResponse({
                    'success': True,
                    'message': f'{email_description.title()} email sent successfully to {recipient_email}.',
                    'job_id': job_id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Failed to send {email_description} email. Please check email configuration.'
                }, status=500)

        except Enrollment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Enrollment not found'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending enrollment email: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred while sending the email.'
            }, status=500)


class CheckPriceAdjustmentAPIView(LoginRequiredMixin, View):
    """
    AJAX API endpoint to check if enrollment needs price adjustment
    """

    def get(self, request, enrollment_id):
        """Check if price adjustment is needed for enrollment"""
        if not request.user.is_staff:
            return JsonResponse({'error': 'Access denied'}, status=403)

        try:
            enrollment = get_object_or_404(Enrollment, pk=enrollment_id)

            from core.services.early_bird_pricing_service import EarlyBirdPricingService

            # Get comprehensive price adjustment summary
            summary = EarlyBirdPricingService.get_price_adjustment_summary(enrollment)

            return JsonResponse(summary)

        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Enrollment not found'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error checking price adjustment for enrollment {enrollment_id}: {str(e)}")
            return JsonResponse({
                'error': 'An unexpected error occurred while checking price adjustment.'
            }, status=500)


class ApplyPriceAdjustmentAPIView(LoginRequiredMixin, View):
    """
    AJAX API endpoint to apply price adjustment to enrollment
    """

    def post(self, request, enrollment_id):
        """Apply price adjustment to enrollment"""
        if not request.user.is_staff:
            return JsonResponse({'error': 'Access denied'}, status=403)

        try:
            enrollment = get_object_or_404(Enrollment, pk=enrollment_id)

            import json
            data = json.loads(request.body)
            adjustment_type = data.get('adjustment_type')

            if adjustment_type not in ['keep_early_bird', 'apply_regular']:
                return JsonResponse({
                    'error': 'Invalid adjustment type. Must be "keep_early_bird" or "apply_regular".'
                }, status=400)

            from core.services.early_bird_pricing_service import EarlyBirdPricingService

            # Determine price adjustment parameters
            use_regular_price = (adjustment_type == 'apply_regular')

            # Apply price adjustment
            result = EarlyBirdPricingService.apply_price_adjustment(
                enrollment=enrollment,
                use_regular_price=use_regular_price,
                performed_by=request.user
            )

            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': result['message'],
                    'adjustment_details': {
                        'previous_price': str(result['previous_price']),
                        'new_price': str(result['new_price']),
                        'price_difference': str(result['price_difference']),
                        'adjustment_type': result['adjustment_type']
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['message']
                }, status=500)

        except Enrollment.DoesNotExist:
            return JsonResponse({'error': 'Enrollment not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error applying price adjustment for enrollment {enrollment_id}: {str(e)}")
            return JsonResponse({
                'error': 'An unexpected error occurred while applying price adjustment.'
            }, status=500)


class DownloadEnrollmentInvoiceView(LoginRequiredMixin, View):
    """Generate and download PDF invoice for an enrollment."""
    
    def get(self, request, pk):
        from django.http import HttpResponse
        from core.services.invoice_service import EnrollmentInvoiceService
        
        enrollment = get_object_or_404(Enrollment, pk=pk)
        
        # Generate invoice PDF using the existing service
        invoice_data = EnrollmentInvoiceService.generate_invoice_pdf(enrollment)
        
        if not invoice_data:
            messages.error(request, 'Failed to generate invoice PDF. Please try again.')
            return redirect('enrollment:enrollment_detail', pk=pk)
        
        # Return PDF as HTTP response with appropriate headers
        response = HttpResponse(
            invoice_data['content'],
            content_type=invoice_data['mimetype']
        )
        response['Content-Disposition'] = f'attachment; filename="{invoice_data["filename"]}"'
        return response


class EnrollmentTransferView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to handle transferring a student from one course to another"""
    template_name = 'core/enrollments/transfer.html'
    
    def test_func(self):
        # Only allow staff/admin
        return self.request.user.is_staff
        
    def get(self, request, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk)
        
        # Security check: ensure enrollment is active/pending
        if enrollment.status == 'cancelled':
             messages.error(request, 'Cannot transfer a cancelled enrollment.')
             return redirect('enrollment:enrollment_detail', pk=enrollment.pk)
             
        form = EnrollmentTransferForm(current_enrollment=enrollment)
        
        return render(request, self.template_name, {
            'form': form,
            'enrollment': enrollment,
            'student': enrollment.student,
            'current_course': enrollment.course
        })
        
    def post(self, request, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk)
        form = EnrollmentTransferForm(request.POST, current_enrollment=enrollment)
        
        if form.is_valid():
            target_course = form.cleaned_data['target_course']
            price_handling = form.cleaned_data['price_handling']
            send_confirmation = form.cleaned_data['send_confirmation']
            transfer_effective_at = form.cleaned_data['transfer_effective_at']
            
            try:
                with transaction.atomic():
                    # 1. Create New Enrollment
                    new_enrollment = Enrollment(
                        student=enrollment.student,
                        course=target_course,
                        status='confirmed',
                        registration_status='transferred',
                        source_channel='staff',
                        registration_fee=0,
                        registration_fee_paid=True,
                        is_new_student=False,
                        active_from=transfer_effective_at
                    )
                    
                    # Handle Course Fee logic
                    if price_handling == 'carry_over':
                        # Use the original enrollment's fee
                        new_enrollment.course_fee = enrollment.course_fee
                    else:
                        # Use new course's price
                        new_enrollment.course_fee = target_course.price
                        
                    # Copy form data
                    if enrollment.form_data:
                        new_enrollment.form_data = enrollment.form_data.copy()
                        new_enrollment.form_data['transferred_from'] = enrollment.id
                        new_enrollment.form_data['original_course'] = enrollment.course.name
                    else:
                        new_enrollment.form_data = {
                            'transferred_from': enrollment.id,
                            'original_course': enrollment.course.name
                        }
                    new_enrollment.form_data['transfer_effective_at'] = transfer_effective_at.isoformat()
                        
                    new_enrollment.save()
                    
                    # 2. Update Old Enrollment window and sync attendance before cancelling
                    enrollment.form_data = enrollment.form_data or {}
                    enrollment.form_data['transferred_to'] = new_enrollment.id
                    enrollment.form_data['target_course'] = target_course.name
                    enrollment.form_data['transfer_effective_at'] = transfer_effective_at.isoformat()
                    enrollment.active_until = transfer_effective_at
                    enrollment.save(update_fields=['form_data', 'active_until', 'updated_at'])
                    EnrollmentAttendanceService.sync_enrollment_attendance(enrollment)
                    
                    # 3. Cancel Old Enrollment
                    enrollment.status = 'cancelled'
                    enrollment.save(update_fields=['status', 'updated_at'])
                    
                    # 4. Log Activities
                    from students.models import StudentActivity
                    StudentActivity.create_activity(
                        student=enrollment.student,
                        activity_type='enrollment_cancelled',
                        title=f'Enrollment transferred to {target_course.name}',
                        description=f'Student transferred to {target_course.name}. Old enrollment cancelled.',
                        enrollment=enrollment,
                        course=enrollment.course,
                        performed_by=request.user,
                        metadata={
                            'transfer_target_id': new_enrollment.id,
                            'transfer_effective_at': transfer_effective_at.isoformat()
                        }
                    )
                    
                    StudentActivity.create_activity(
                        student=enrollment.student,
                        activity_type='enrollment_created',
                        title=f'Enrollment transferred from {enrollment.course.name}',
                        description=f'Transfer enrollment created from {enrollment.course.name}.',
                        enrollment=new_enrollment,
                        course=target_course,
                        performed_by=request.user,
                        metadata={
                            'transfer_source_id': enrollment.id,
                            'transfer_effective_at': transfer_effective_at.isoformat()
                        }
                    )
                    
                    # 5. Send Notification if requested
                    if send_confirmation:
                        transaction.on_commit(
                            lambda enrollment_id=new_enrollment.id: enqueue_enrollment_confirmation_email(enrollment_id)
                        )
                    
                messages.success(request, f'Successfully transferred student to {target_course.name}.')
                return redirect('enrollment:enrollment_detail', pk=new_enrollment.pk)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error during transfer: {str(e)}')
                
        return render(request, self.template_name, {
            'form': form,
            'enrollment': enrollment,
            'student': enrollment.student,
            'current_course': enrollment.course
        })


@login_required
def bulk_enrollment_notification_start(request):
    """Start bulk notification sending for enrollments and return task ID for progress tracking"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    from core.services.bulk_notification_progress import BulkNotificationProgress
    from core.models import NotificationQuota

    form = BulkEnrollmentNotificationForm(request.POST)

    if not form.is_valid():
        errors = {}
        for field, field_errors in form.errors.items():
            errors[field] = field_errors
        return JsonResponse({'error': 'Form validation failed', 'details': errors}, status=400)

    # Get cleaned data
    cleaned_data = form.cleaned_data
    notification_type = cleaned_data['notification_type']
    enrollment_ids = cleaned_data.get('enrollment_id_list', [])

    # Determine recipient students from enrollments
    recipients = []
    
    if enrollment_ids:
        # Get unique students from selected enrollments
        enrollments = Enrollment.objects.filter(id__in=enrollment_ids).select_related('student')
        student_ids = set(e.student_id for e in enrollments if e.student.is_active)
        recipients = Student.objects.filter(id__in=student_ids)

    if not recipients:
        return JsonResponse({'error': 'No active students found for selected enrollments'}, status=400)

    # Check notification quotas
    email_quota_ok = True
    sms_quota_ok = True

    if notification_type in ['email', 'both']:
        email_quota_ok = NotificationQuota.check_quota_available('email', len(recipients))
        if not email_quota_ok:
            return JsonResponse({
                'error': f'Email quota exceeded. Cannot send {len(recipients)} emails.'
            }, status=400)

    if notification_type in ['sms', 'both']:
        sms_quota_ok = NotificationQuota.check_quota_available('sms', len(recipients))
        if not sms_quota_ok:
            return JsonResponse({
                'error': f'SMS quota exceeded. Cannot send {len(recipients)} SMS messages.'
            }, status=400)

    # Create progress tracking task
    task_id = BulkNotificationProgress.create_task(len(recipients), notification_type)

    # Store task data in session for the actual execution
    request.session[f'bulk_task_{task_id}'] = {
        'notification_type': notification_type,
        'message_type': cleaned_data['message_type'],
        'subject': cleaned_data.get('subject', ''),
        'message': cleaned_data['message'],
        'recipient_ids': [r.id for r in recipients],
        'total_recipients': len(recipients)
    }

    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'total_recipients': len(recipients),
        'notification_type': notification_type
    })


@login_required
def bulk_enrollment_notification_execute(request, task_id):
    """Execute the actual bulk notification sending with progress tracking"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    from core.services.bulk_notification_progress import BulkNotificationProgress, create_progress_callback
    from core.services.batch_email_service import BatchEmailService
    from core.services.notification_service import NotificationService
    from core.models import SMSLog, NotificationQuota

    # Get task data from session
    task_data = request.session.get(f'bulk_task_{task_id}')
    if not task_data:
        BulkNotificationProgress.mark_failed(task_id, 'Task data not found')
        return JsonResponse({'error': 'Task data not found'}, status=404)

    try:
        # Get recipients
        recipient_ids = task_data['recipient_ids']
        recipients = Student.objects.filter(id__in=recipient_ids, is_active=True)

        notification_type = task_data['notification_type']
        message_type = task_data['message_type']
        subject = task_data['subject']
        message = task_data['message']

        # Create progress callback
        progress_callback = create_progress_callback(task_id)

        # Send notifications using batch service for emails
        email_sent = 0
        sms_sent = 0
        email_failed = 0
        sms_failed = 0

        # Prepare bulk email data if email notifications are needed
        if notification_type in ['email', 'both']:
            email_data_list = []
            for student in recipients:
                contact_email = student.get_contact_email()
                if contact_email:
                    context = {
                        'student': student,
                        'recipient_name': student.guardian_name if student.guardian_name else student.get_full_name(),
                        'message': message,
                        'message_type': message_type,
                        'site_domain': 'edupulse.perthartschool.com.au',  # TODO: Make configurable
                    }

                    email_data = {
                        'to': contact_email,
                        'subject': subject,
                        'context': context,
                        'template_name': 'core/emails/bulk_notification.html'
                    }
                    email_data_list.append(email_data)

            if email_data_list:
                try:
                    batch_service = BatchEmailService(progress_callback=progress_callback)
                    stats = batch_service.send_bulk_emails(email_data_list)
                    email_sent = stats['sent']
                    email_failed = stats['failed']
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Bulk email notification error: {e}")
                    email_failed = len(email_data_list)
                    email_sent = 0

        # Send SMS notifications (individual processing as before)
        if notification_type in ['sms', 'both']:
            for student in recipients:
                phone = student.get_contact_phone()
                if phone:
                    try:
                        success = NotificationService.send_sms_notification(phone, message, 'bulk')
                        if success:
                            sms_sent += 1
                            SMSLog.objects.create(
                                recipient_phone=phone,
                                recipient_type='student',
                                content=message,
                                sms_type='bulk',
                                status='sent',
                                sent_at=timezone.now()
                            )
                        else:
                            sms_failed += 1
                            SMSLog.objects.create(
                                recipient_phone=phone,
                                recipient_type='student',
                                content=message,
                                sms_type='bulk',
                                status='failed',
                                error_message='SMS sending failed',
                                sent_at=timezone.now()
                            )
                    except Exception as e:
                        sms_failed += 1
                        SMSLog.objects.create(
                            recipient_phone=phone,
                            recipient_type='student',
                            content=message,
                            sms_type='bulk',
                            status='failed',
                            error_message=str(e),
                            sent_at=timezone.now()
                        )

        # Update quotas
        if sms_sent > 0:
            NotificationQuota.consume_quota('sms', sms_sent)
            
        if email_sent > 0:
            NotificationQuota.consume_quota('email', email_sent)

        # Mark task as completed
        final_stats = {
            'sent': email_sent + sms_sent,
            'failed': email_failed + sms_failed,
            'email_sent': email_sent,
            'email_failed': email_failed,
            'sms_sent': sms_sent,
            'sms_failed': sms_failed
        }

        BulkNotificationProgress.mark_completed(task_id, final_stats)

        # Clean up session data
        if f'bulk_task_{task_id}' in request.session:
            del request.session[f'bulk_task_{task_id}']

        return JsonResponse({
            'success': True,
            'stats': final_stats
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bulk notification execution error: {e}")
        BulkNotificationProgress.mark_failed(task_id, str(e))
        return JsonResponse({'error': f'Execution failed: {e}'}, status=500)


@login_required
def bulk_enrollment_notification_progress(request, task_id):
    """Get progress status for a bulk notification task"""
    from core.services.bulk_notification_progress import BulkNotificationProgress

    progress_data = BulkNotificationProgress.get_progress(task_id)

    if not progress_data:
        return JsonResponse({'error': 'Task not found'}, status=404)

    return JsonResponse(progress_data)
