#!/usr/bin/env python
"""
Test script to simulate enrollment submission and trigger pending email
Usage: python test_enrollment_email.py
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, time

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.utils import timezone
from academics.models import Course
from students.models import Student
from enrollment.models import Enrollment
from facilities.models import Facility
from accounts.models import Staff
from core.services.notification_service import NotificationService

def create_test_data():
    """
    Create test data for enrollment email testing
    """
    print("Creating test data...")
    
    # Create or get test facility
    facility, created = Facility.objects.get_or_create(
        name="Perth Art School Main Campus",
        defaults={
            'address': '123 Art Street, Perth WA 6000',
            'phone': '08 9123 4567',
            'latitude': Decimal('-31.9505'),
            'longitude': Decimal('115.8605'),
            'attendance_radius': 100
        }
    )
    if created:
        print(f"✓ Created facility: {facility.name}")
    else:
        print(f"✓ Using existing facility: {facility.name}")
    
    # Create or get test teacher
    teacher, created = Staff.objects.get_or_create(
        username="test_teacher",
        defaults={
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'teacher@perthartschool.com.au',
            'role': 'teacher',
            'is_active_staff': True
        }
    )
    if created:
        teacher.set_password('testpass123')
        teacher.save()
        print(f"✓ Created teacher: {teacher.get_full_name()}")
    else:
        print(f"✓ Using existing teacher: {teacher.get_full_name()}")
    
    # Create or get test course
    course, created = Course.objects.get_or_create(
        name="Watercolour Painting for Beginners",
        defaults={
            'description': '<p>Learn the fundamentals of watercolour painting in this comprehensive beginner course.</p>',
            'short_description': 'Perfect introduction to watercolour techniques and colour theory.',
            'price': Decimal('280.00'),
            'registration_fee': Decimal('50.00'),
            'course_type': 'group',
            'category': 'term_courses',
            'status': 'published',
            'teacher': teacher,
            'start_date': date.today(),
            'end_date': date.today(),
            'repeat_pattern': 'weekly',
            'repeat_weekday': 5,  # Saturday
            'start_time': time(10, 0),  # 10:00 AM
            'duration_minutes': 180,  # 3 hours
            'vacancy': 12,
            'is_online_bookable': True,
            'facility': facility
        }
    )
    if created:
        print(f"✓ Created course: {course.name}")
    else:
        print(f"✓ Using existing course: {course.name}")
    
    # Create or get test student
    student, created = Student.objects.get_or_create(
        first_name="John",
        last_name="Doe",
        defaults={
            'birth_date': date(1990, 5, 15),
            'address': '456 Student Street, Perth WA 6001',
            'contact_email': 'changjiang1124+test@gmail.com',  # Test email
            'contact_phone': '0401909771',
            'guardian_name': '',  # Adult student
            'emergency_contact_name': 'Jane Doe',
            'emergency_contact_phone': '0401909772',
            'reference': 'TEST_STUDENT_001'
        }
    )
    if created:
        print(f"✓ Created student: {student.get_full_name()}")
    else:
        print(f"✓ Using existing student: {student.get_full_name()}")
        # Update email for testing
        student.contact_email = 'changjiang1124+test@gmail.com'
        student.save()
        print(f"✓ Updated student email to: {student.contact_email}")
    
    return course, student, facility, teacher

def create_test_enrollment(course, student):
    """
    Create a test enrollment and trigger pending email
    """
    print("\nCreating test enrollment...")
    
    # Check if enrollment already exists
    existing_enrollment = Enrollment.objects.filter(
        student=student,
        course=course
    ).first()
    
    if existing_enrollment:
        print(f"✓ Found existing enrollment: {existing_enrollment.id}")
        enrollment = existing_enrollment
    else:
        # Create new enrollment
        enrollment = Enrollment.objects.create(
            student=student,
            course=course,
            status='pending',
            source_channel='test_script',
            registration_status='new',
            original_form_data={
                'student_status': 'new',
                'contact_info': {
                    'primary_email': student.contact_email,
                    'primary_phone': student.contact_phone
                },
                'course_selection': {
                    'course_id': course.id,
                    'course_name': course.name
                },
                'test_submission': True
            },
            is_new_student=True,
            matched_existing_student=False
        )
        print(f"✓ Created enrollment: {enrollment.id}")
    
    return enrollment

def send_test_email(enrollment):
    """
    Send test pending enrollment email
    """
    print("\nSending test pending enrollment email...")
    
    # Calculate fees
    course_fee = enrollment.course.price
    registration_fee = enrollment.course.registration_fee or Decimal('0')
    total_fee = course_fee + registration_fee
    
    fee_breakdown = {
        'course_fee': course_fee,
        'registration_fee': registration_fee,
        'total_fee': total_fee,
        'has_registration_fee': registration_fee > 0,
        'charge_registration_fee': True
    }
    
    print(f"Course Fee: ${course_fee}")
    print(f"Registration Fee: ${registration_fee}")
    print(f"Total Fee: ${total_fee}")
    print(f"Recipient: {enrollment.student.contact_email}")
    
    # Send the email
    try:
        success = NotificationService.send_enrollment_pending_email(
            enrollment=enrollment,
            recipient_email=enrollment.student.contact_email,
            fee_breakdown=fee_breakdown
        )
        
        if success:
            print("✅ Email sent successfully!")
            print(f"📧 Check your inbox at: {enrollment.student.contact_email}")
            return True
        else:
            print("❌ Failed to send email")
            return False
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

def main():
    """
    Main test function
    """
    print("🧪 Starting Enrollment Email Test")
    print("=" * 50)
    
    try:
        # Create test data
        course, student, facility, teacher = create_test_data()
        
        # Create enrollment
        enrollment = create_test_enrollment(course, student)
        
        # Send test email
        success = send_test_email(enrollment)
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 Test completed successfully!")
            print(f"📧 Check email at: {student.contact_email}")
            print(f"🔗 Enrollment ID: {enrollment.id}")
            print(f"📋 Reference: {enrollment.get_reference_id()}")
        else:
            print("❌ Test failed - email not sent")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()