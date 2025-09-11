#!/usr/bin/env python
"""
Simple test script for enrollment-class attendance automation
This version avoids WooCommerce integration issues
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/changjiang/Dev/edupulse')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from datetime import date, time, timedelta
from enrollment.models import Enrollment, Attendance
from academics.models import Course, Class
from students.models import Student
from accounts.models import Staff

def simple_automation_test():
    """Simple test to verify automation works"""
    print("=== Simple Automation Test ===")
    
    try:
        # Get existing data or create minimal test data
        teacher = Staff.objects.filter(role='teacher').first()
        if not teacher:
            teacher = Staff.objects.create(
                username='simple_test_teacher',
                first_name='Test',
                last_name='Teacher',
                email='test@example.com',
                role='teacher'
            )
        
        # Create a simple course without WooCommerce sync
        course = Course.objects.create(
            name='Simple Test Course',
            short_description='Simple test',
            price=50.00,
            course_type='group',
            status='draft',  # Use draft to avoid WooCommerce sync
            teacher=teacher,
            start_date=date.today(),
            start_time=time(10, 0),
            duration_minutes=60,
            vacancy=5,
            repeat_pattern='once',
            is_online_bookable=False  # Avoid sync
        )
        
        # Create a test student
        student = Student.objects.create(
            first_name='TestStudent',
            last_name='AutoTest',
            birth_date=date(2000, 1, 1),
            contact_email='test@example.com',
            contact_phone='0401234567'
        )
        
        print(f"✓ Created course: {course.name}")
        print(f"✓ Created student: {student.get_full_name()}")
        
        # Test 1: Create class first, then enrollment
        print("\n--- Test 1: Class first, then enrollment ---")
        
        test_class = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=1),
            start_time=time(11, 0),
            duration_minutes=60,
            teacher=teacher,
            is_active=True
        )
        print(f"✓ Created class for {test_class.date}")
        
        # Create confirmed enrollment (should trigger attendance creation)
        enrollment = Enrollment.objects.create(
            student=student,
            course=course,
            status='confirmed',
            source_channel='staff',
            registration_status='new'
        )
        print(f"✓ Created confirmed enrollment")
        
        # Check if attendance was created
        attendance = Attendance.objects.filter(
            student=student,
            class_instance=test_class
        ).first()
        
        if attendance:
            print(f"✓ Attendance record created automatically: {attendance.status}")
        else:
            print("✗ No attendance record found")
        
        # Test 2: Create another class (should add to existing enrollment)
        print("\n--- Test 2: Add class to existing enrollment ---")
        
        test_class2 = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=2),
            start_time=time(11, 0),
            duration_minutes=60,
            teacher=teacher,
            is_active=True
        )
        print(f"✓ Created second class for {test_class2.date}")
        
        # Check if attendance was created for the new class
        attendance2 = Attendance.objects.filter(
            student=student,
            class_instance=test_class2
        ).first()
        
        if attendance2:
            print(f"✓ Attendance record created for new class: {attendance2.status}")
        else:
            print("✗ No attendance record found for new class")
        
        # Summary
        total_attendance = Attendance.objects.filter(
            student=student,
            class_instance__course=course
        ).count()
        
        print(f"\n--- Summary ---")
        print(f"✓ Total attendance records: {total_attendance}")
        print(f"✓ Expected: 2 (one for each class)")
        
        success = total_attendance == 2
        
        # Cleanup
        print(f"\n--- Cleanup ---")
        Attendance.objects.filter(student=student).delete()
        enrollment.delete()
        Class.objects.filter(course=course).delete()
        course.delete()
        student.delete()
        if teacher.username == 'simple_test_teacher':
            teacher.delete()
        print("✓ Cleaned up test data")
        
        return success
        
    except Exception as e:
        print(f"✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Running simple automation test...")
    success = simple_automation_test()
    
    if success:
        print("\n🎉 Automation test PASSED! The system is working correctly.")
    else:
        print("\n⚠️ Automation test FAILED. Please check the implementation.")
    
    sys.exit(0 if success else 1)