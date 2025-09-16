from django.db.models import Q
from datetime import date
from .models import Student, StudentActivity


class StudentMatchingService:
    """Service for matching and creating students from enrollment data"""
    
    @staticmethod
    def find_existing_student(form_data):
        """
        Intelligently match existing student based on form data
        Matching strategies (in priority order):
        1. Full name + DOB (exact match)
        2. Full name + Phone number
        3. Full name + Email
        Returns: (student_instance, match_type)
        """
        first_name = form_data.get('first_name', '').strip()
        last_name = form_data.get('last_name', '').strip()
        date_of_birth = form_data.get('date_of_birth')
        phone = form_data.get('phone', '').strip()
        email = form_data.get('email', '').strip()
        
        if not first_name or not last_name:
            return None, 'none'
        
        # Strategy 1: Full name + DOB (exact match - highest priority)
        if date_of_birth:
            exact_match = Student.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                birth_date=date_of_birth,
                is_active=True
            ).first()
            
            if exact_match:
                return exact_match, 'name_dob'
        
        # Strategy 2: Full name + Phone number
        if phone:
            phone_match = Student.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                contact_phone=phone,
                is_active=True
            ).first()
            
            if phone_match:
                return phone_match, 'name_phone'
        
        # Strategy 3: Full name + Email
        if email:
            email_match = Student.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                contact_email__iexact=email,
                is_active=True
            ).first()
            
            if email_match:
                return email_match, 'name_email'
        
        # No matches found
        return None, 'none'
    
    @staticmethod
    def create_or_update_student(form_data, enrollment):
        """
        Create new student or update existing student from enrollment form data
        Returns: (student_instance, was_created)
        """
        existing_student, match_type = StudentMatchingService.find_existing_student(form_data)
        
        if existing_student and match_type in ['name_dob', 'name_phone', 'name_email']:
            # Update existing student with new information if needed
            StudentMatchingService._update_student_from_form(existing_student, form_data, match_type, enrollment)
            if enrollment:
                enrollment.student = existing_student
                enrollment.is_new_student = False
                enrollment.matched_existing_student = True
                enrollment.save()
            return existing_student, False
        else:
            # Create new student
            student = StudentMatchingService._create_student_from_form(form_data, enrollment)
            if enrollment:
                enrollment.student = student
                enrollment.is_new_student = True
                enrollment.matched_existing_student = False
                enrollment.save()
            return student, True

    @staticmethod
    def _create_student_from_form(form_data, enrollment):
        """Create new student from enrollment form data"""
        # Calculate age to determine contact type
        age = StudentMatchingService._calculate_age(form_data.get('date_of_birth'))
        is_minor = age is not None and age < 18
        
        # Build a safe internal note without dereferencing enrollment when None
        if enrollment:
            try:
                note_date_str = enrollment.created_at.strftime("%Y-%m-%d") if getattr(enrollment, 'created_at', None) else date.today().strftime("%Y-%m-%d")
                internal_note = f'Created from enrollment on {note_date_str}'
            except Exception:
                internal_note = f'Created from enrollment on {date.today().strftime("%Y-%m-%d")}'
        else:
            internal_note = f'Created from public enrollment form on {date.today().strftime("%Y-%m-%d")}'
        
        # Create student
        student = Student.objects.create(
            first_name=form_data.get('first_name', '').strip(),
            last_name=form_data.get('last_name', '').strip(),
            birth_date=form_data.get('date_of_birth'),
            address=form_data.get('address', ''),
            
            # Contact information (unified - student or guardian depending on age)
            contact_email=form_data.get('email', ''),
            contact_phone=form_data.get('phone', ''),
            
            # Guardian information (for minors)
            guardian_name=form_data.get('guardian_name', '') if is_minor else '',
            
            # Emergency contact
            emergency_contact_name=form_data.get('emergency_contact_name', ''),
            emergency_contact_phone=form_data.get('emergency_contact_phone', ''),
            
            # Medical information
            medical_conditions=form_data.get('medical_conditions', ''),
            special_requirements=form_data.get('special_requirements', ''),
            
            # System fields
            # Note: registration_status is now managed at enrollment level
            enrollment_source='website',
            source_enrollment=enrollment if enrollment else None,
            internal_notes=internal_note,
        )
        
        return student
    
    @staticmethod
    def _update_student_from_form(student, form_data, match_type=None, enrollment=None):
        """Update existing student with new form data, preserving critical contact info"""
        updated = False
        contact_updated = False

        if not student.address and form_data.get('address'):
            student.address = form_data['address']
            updated = True

        new_email = (form_data.get('email') or '').strip()
        current_email = (student.contact_email or '').strip()
        if new_email:
            if not current_email:
                student.contact_email = new_email
                updated = True
                contact_updated = True
            elif match_type in ['name_dob', 'name_phone'] and current_email.lower() != new_email.lower():
                student.contact_email = new_email
                updated = True
                contact_updated = True

        if not student.contact_phone and form_data.get('phone'):
            student.contact_phone = form_data['phone']
            updated = True

        if not student.guardian_name and form_data.get('guardian_name'):
            student.guardian_name = form_data['guardian_name']
            updated = True

        if not student.emergency_contact_name and form_data.get('emergency_contact_name'):
            student.emergency_contact_name = form_data['emergency_contact_name']
            updated = True

        if not student.emergency_contact_phone and form_data.get('emergency_contact_phone'):
            student.emergency_contact_phone = form_data['emergency_contact_phone']
            updated = True

        if updated:
            student.save()

        if contact_updated:
            try:
                StudentActivity.create_activity(
                    student=student,
                    activity_type='contact_updated',
                    title='Contact email updated from enrollment form',
                    description='Email updated after matching existing student during enrollment',
                    metadata={
                        'match_type': match_type,
                        'previous_email': current_email,
                        'new_email': student.contact_email,
                        'source': 'public_enrollment' if enrollment is None else 'staff_enrollment'
                    }
                )
            except Exception:
                pass

        return student
    
    @staticmethod
    def _calculate_age(birth_date):
        """Calculate age based on birth date"""
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


class EnrollmentFeeCalculator:
    """Calculate enrollment fees based on course and student status"""
    
    @staticmethod
    def calculate_total_fees(course, registration_status='new'):
        """Calculate total fees including registration fee if applicable"""
        # Base course fee
        course_fee = course.price or 0
        
        # Registration fee if new student and course has registration fee
        registration_fee = 0
        try:
            if registration_status == 'new' and hasattr(course, 'has_registration_fee') and course.has_registration_fee():
                registration_fee = course.registration_fee or 0
        except Exception:
            registration_fee = 0
        
        total_fee = (course_fee or 0) + (registration_fee or 0)
        
        return {
            'course_fee': course_fee,
            'registration_fee': registration_fee,
            'total_fee': total_fee,
            'has_registration_fee': (registration_fee or 0) > 0,
        }
    
    @staticmethod
    def update_enrollment_fees(enrollment, course, is_new_student=None):
        """Update the enrollment with calculated fees"""
        # Use enrollment.registration_status if available, otherwise fall back to is_new_student
        registration_status = getattr(enrollment, 'registration_status', 'new')
        if registration_status is None and is_new_student is not None:
            registration_status = 'new' if is_new_student else 'returning'
        
        fees = EnrollmentFeeCalculator.calculate_total_fees(course, registration_status)
        
        # Store calculated fees in enrollment (use existing fields)
        try:
            enrollment.course_fee = fees.get('course_fee', 0)
            enrollment.registration_fee = fees.get('registration_fee', 0)
            # Keep is_new_student for backward compatibility if provided
            if is_new_student is not None:
                enrollment.is_new_student = is_new_student
            enrollment.save()
        except Exception:
            # Fail silently to avoid blocking enrollment creation
            pass
        
        return fees