from django.db.models import Q
from datetime import date
from .models import Student


class StudentMatchingService:
    """Service for matching and creating students from enrollment data"""
    
    @staticmethod
    def find_existing_student(form_data):
        """
        Intelligently match existing student based on form data
        Returns: (student_instance, match_type)
        """
        first_name = form_data.get('first_name', '').strip()
        last_name = form_data.get('last_name', '').strip()
        date_of_birth = form_data.get('date_of_birth')
        
        if not first_name or not last_name:
            return None, 'none'
        
        # First try exact name + DOB match
        if date_of_birth:
            exact_match = Student.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                birth_date=date_of_birth,
                is_active=True
            ).first()
            
            if exact_match:
                return exact_match, 'exact'
        
        # Try name-only match if unique
        name_matches = Student.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            is_active=True
        )
        
        if name_matches.count() == 1:
            return name_matches.first(), 'name_only'
        elif name_matches.count() > 1:
            return None, 'multiple_matches'
        
        return None, 'none'
    
    @staticmethod
    def create_or_update_student(form_data, enrollment):
        """
        Create new student or update existing student from enrollment form data
        Returns: (student_instance, was_created)
        """
        existing_student, match_type = StudentMatchingService.find_existing_student(form_data)
        
        if existing_student and match_type in ['exact', 'name_only']:
            # Update existing student with new information if needed
            StudentMatchingService._update_student_from_form(existing_student, form_data)
            enrollment.student = existing_student
            enrollment.is_new_student = False
            enrollment.matched_existing_student = True
            enrollment.save()
            return existing_student, False
        else:
            # Create new student
            student = StudentMatchingService._create_student_from_form(form_data, enrollment)
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
        
        # Determine primary contact type
        primary_contact_type = 'guardian' if is_minor else 'student'
        
        # Create student
        student = Student.objects.create(
            first_name=form_data.get('first_name', '').strip(),
            last_name=form_data.get('last_name', '').strip(),
            birth_date=form_data.get('date_of_birth'),
            address=form_data.get('address', ''),
            
            # Primary contact (from unified enrollment form fields)
            primary_contact_email=form_data.get('email', ''),
            primary_contact_phone=form_data.get('phone', ''),
            primary_contact_type=primary_contact_type,
            
            # Guardian information (for minors)
            guardian_name=form_data.get('guardian_name', '') if is_minor else '',
            
            # Emergency contact
            emergency_contact_name=form_data.get('emergency_contact_name', ''),
            emergency_contact_phone=form_data.get('emergency_contact_phone', ''),
            
            # Medical information
            medical_conditions=form_data.get('medical_conditions', ''),
            special_requirements=form_data.get('special_requirements', ''),
            
            # System fields
            registration_status='new',
            enrollment_source='website',
            source_enrollment=enrollment,
            internal_notes=f'Created from enrollment #{enrollment.id} on {enrollment.created_at.strftime("%Y-%m-%d")}'
        )
        
        return student
    
    @staticmethod
    def _update_student_from_form(student, form_data):
        """Update existing student with new form data if fields are empty"""
        # Only update empty fields to avoid overwriting existing data
        updated = False
        
        if not student.address and form_data.get('address'):
            student.address = form_data['address']
            updated = True
        
        if not student.primary_contact_email and form_data.get('email'):
            student.primary_contact_email = form_data['email']
            updated = True
        
        if not student.primary_contact_phone and form_data.get('phone'):
            student.primary_contact_phone = form_data['phone']
            updated = True
        
        if not student.emergency_contact_name and form_data.get('emergency_contact_name'):
            student.emergency_contact_name = form_data['emergency_contact_name']
            updated = True
        
        if not student.emergency_contact_phone and form_data.get('emergency_contact_phone'):
            student.emergency_contact_phone = form_data['emergency_contact_phone']
            updated = True
        
        if not student.medical_conditions and form_data.get('medical_conditions'):
            student.medical_conditions = form_data['medical_conditions']
            updated = True
        
        if not student.special_requirements and form_data.get('special_requirements'):
            student.special_requirements = form_data['special_requirements']
            updated = True
        
        if updated:
            student.internal_notes += f'\nUpdated from enrollment on {date.today().strftime("%Y-%m-%d")}'
            student.save()
    
    @staticmethod
    def _calculate_age(birth_date):
        """Calculate age from birth date"""
        if not birth_date:
            return None
        
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


class EnrollmentFeeCalculator:
    """Service for calculating enrollment fees"""
    
    @staticmethod
    def calculate_total_fees(course, is_new_student=True):
        """
        Calculate total fees for enrollment
        Returns: dict with fee breakdown
        """
        course_fee = course.price
        registration_fee = 0
        
        if is_new_student and course.has_registration_fee():
            registration_fee = course.registration_fee
        
        return {
            'course_fee': course_fee,
            'registration_fee': registration_fee,
            'total_fee': course_fee + registration_fee,
            'has_registration_fee': registration_fee > 0
        }
    
    @staticmethod
    def update_enrollment_fees(enrollment, course, is_new_student):
        """Update enrollment with calculated fees"""
        fees = EnrollmentFeeCalculator.calculate_total_fees(course, is_new_student)
        
        enrollment.course_fee = fees['course_fee']
        enrollment.registration_fee = fees['registration_fee']
        enrollment.is_new_student = is_new_student
        enrollment.save()
        
        return fees