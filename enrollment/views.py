from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView, View
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse

from .models import Enrollment, Attendance
from .forms import EnrollmentForm, EnrollmentUpdateForm, PublicEnrollmentForm, StaffEnrollmentForm
from students.models import Student
from academics.models import Course
from core.models import OrganisationSettings


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
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter options
        context['students'] = Student.objects.all().order_by('first_name', 'last_name')
        context['courses'] = Course.objects.filter(status='published').order_by('name')
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
        
        return context
    
    def post(self, request, *args, **kwargs):
        from core.services import NotificationService
        
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'confirm' and self.object.status == 'pending':
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
            
            # Send welcome email upon confirmation
            try:
                welcome_sent = NotificationService.send_welcome_email(self.object)
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
                            'triggered_by': 'enrollment_confirmation'
                        }
                    )
                    messages.success(
                        request, 
                        f'Enrollment for {self.object.student.get_full_name()} has been confirmed and welcome email sent. '
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
            from core.services import NotificationService

            # Calculate total fee
            course_fee = enrollment.course.price
            charge_registration_fee = enrollment.form_data.get('charge_registration_fee', True)
            registration_fee = 0

            if charge_registration_fee and enrollment.course.has_registration_fee():
                registration_fee = enrollment.course.registration_fee

            total_fee = course_fee + registration_fee

            # Get contact information
            contact_info = enrollment.student.get_contact_email()
            if not contact_info and hasattr(enrollment, 'form_data'):
                contact_info = enrollment.form_data.get('contact_info', {}).get('primary_email')

            if contact_info:
                # Send notification with fee breakdown
                notification_sent = NotificationService.send_enrollment_pending_email(
                    enrollment=enrollment,
                    recipient_email=contact_info,
                    fee_breakdown={
                        'course_fee': course_fee,
                        'registration_fee': registration_fee,
                        'total_fee': total_fee,
                        'charge_registration_fee': charge_registration_fee
                    }
                )
                return notification_sent
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
        # Save the enrollment
        enrollment = form.save()

        # Check if we should send update notification
        send_notification = enrollment.form_data.get('send_update_notification', False)
        status_changed = enrollment.form_data.get('status_changed', False)
        original_status = enrollment.form_data.get('original_status')

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
            from core.services import NotificationService

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
                notification_sent = NotificationService.send_enrollment_confirmation(enrollment)
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get course_id from URL path parameter or query parameter
        course_id = self.kwargs.get('course_id') or self.request.GET.get('course')
        selected_course = None
        
        # Only show published courses that allow online bookings
        courses = Course.objects.filter(
            status='published', 
            is_online_bookable=True
        ).order_by('name')
        context['courses'] = courses
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = courses.get(pk=course_id)
                context['selected_course'] = selected_course
            except Course.DoesNotExist:
                # If course doesn't exist or isn't bookable, don't pre-select any course
                selected_course = None
        
        # Initialize form with selected course if available
        initial_data = {}
        if selected_course:
            initial_data['course_id'] = selected_course.pk
            
        context['form'] = PublicEnrollmentForm(initial=initial_data)
        return context
    
    def post(self, request, *args, **kwargs):
        form = PublicEnrollmentForm(request.POST)
        
        # Get course_id from URL path parameter or query parameter
        course_id = self.kwargs.get('course_id') or request.GET.get('course')
        selected_course = None
        
        courses = Course.objects.filter(status='published', is_online_bookable=True).order_by('name')
        
        # Handle pre-selected course
        if course_id:
            try:
                selected_course = courses.get(pk=course_id)
            except Course.DoesNotExist:
                # If course doesn't exist or isn't bookable, add error and continue
                messages.error(request, 'The selected course is not available for online booking.')
                selected_course = None
        
        if form.is_valid():
            from students.services import StudentMatchingService, EnrollmentFeeCalculator
            from core.services import NotificationService
            
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
                    notification_sent = NotificationService.send_enrollment_pending_email(
                        enrollment=enrollment,
                        recipient_email=student.get_contact_email(),
                        fee_breakdown={
                            'course_fee': fees.get('course_fee', 0),
                            'registration_fee': fees.get('registration_fee', 0),
                            'total_fee': fees.get('total_fee', 0),
                            'has_registration_fee': fees.get('has_registration_fee', False),
                            'charge_registration_fee': fees.get('has_registration_fee', False)
                        }
                    )
                    
                    if notification_sent:
                        messages.success(request, 'Enrollment pending email sent.')
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
                    else:
                        messages.warning(request, 'Enrollment created but pending email could not be sent.')
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
        context = {
            'form': form,
            'courses': courses
        }
        
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
        except Exception:
            # Fallbacks to ensure page doesn't break if settings not configured
            from django.conf import settings as dj_settings
            context['contact_email'] = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', 'info@perthartschool.com.au')
            context['contact_phone'] = ''
        
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
