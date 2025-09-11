#!/usr/bin/env python
"""
Test script for enrollment-class attendance automation

This script validates that the automatic attendance creation works correctly for:
1. New enrollment confirmation -> create attendance for existing classes
2. New class creation -> create attendance for existing confirmed enrollments
3. Proper handling of edge cases and duplicates
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
from enrollment.services import EnrollmentAttendanceService, ClassAttendanceService, AttendanceSyncService
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test data for validation"""
    print("Creating test data...")
    
    # Create a test teacher
    teacher, created = Staff.objects.get_or_create(
        username='test_teacher',
        defaults={
            'first_name': 'Test',
            'last_name': 'Teacher',
            'email': 'teacher@test.com',
            'role': 'teacher'
        }
    )
    
    # Create a test course
    course, created = Course.objects.get_or_create(
        name='Test Automation Course',
        defaults={
            'short_description': 'Course for testing automation',
            'price': 100.00,
            'course_type': 'group',
            'status': 'published',
            'teacher': teacher,
            'start_date': date.today(),
            'start_time': time(10, 0),
            'duration_minutes': 60,
            'vacancy': 10,
            'repeat_pattern': 'weekly',
            'repeat_weekday': 1,  # Monday
            'is_online_bookable': True
        }
    )
    
    # Create test students
    students = []
    for i in range(3):
        student, created = Student.objects.get_or_create(
            first_name=f'Test{i+1}',
            last_name='Student',
            defaults={
                'birth_date': date(2000, 1, 1),
                'contact_email': f'student{i+1}@test.com',
                'contact_phone': f'040123456{i+1}'
            }
        )
        students.append(student)
    
    return course, teacher, students

def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    
    # Delete test attendance records
    Attendance.objects.filter(
        student__first_name__startswith='Test',
        class_instance__course__name='Test Automation Course'
    ).delete()
    
    # Delete test enrollments
    Enrollment.objects.filter(
        student__first_name__startswith='Test',
        course__name='Test Automation Course'
    ).delete()
    
    # Delete test classes
    Class.objects.filter(course__name='Test Automation Course').delete()
    
    # Delete test course
    Course.objects.filter(name='Test Automation Course').delete()
    
    # Delete test students
    Student.objects.filter(first_name__startswith='Test').delete()
    
    # Delete test teacher
    Staff.objects.filter(username='test_teacher').delete()

def test_enrollment_to_class_automation():
    """Test: Add enrollment to course with existing classes"""
    print("\n=== Test 1: Enrollment to existing classes automation ===")
    
    course, teacher, students = create_test_data()
    
    try:
        # Step 1: Create some classes first
        class1 = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            duration_minutes=60,
            teacher=teacher,
            is_active=True
        )
        
        class2 = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=8),
            start_time=time(10, 0),
            duration_minutes=60,
            teacher=teacher,
            is_active=True
        )
        
        print(f"Created 2 classes for course '{course.name}'")
        
        # Step 2: Create enrollment as pending first
        enrollment = Enrollment.objects.create(
            student=students[0],
            course=course,
            status='pending',
            source_channel='staff',
            registration_status='new'
        )
        
        print(f"Created pending enrollment for {students[0].get_full_name()}")
        
        # Verify no attendance records exist yet
        attendance_count = Attendance.objects.filter(
            student=students[0],
            class_instance__course=course
        ).count()
        assert attendance_count == 0, f"Expected 0 attendance records, found {attendance_count}"
        print("✓ No attendance records created for pending enrollment")
        
        # Step 3: Confirm the enrollment (this should trigger attendance creation)
        enrollment.status = 'confirmed'
        enrollment.save()
        
        print(f"Confirmed enrollment for {students[0].get_full_name()}")
        
        # Verify attendance records were created
        attendance_records = Attendance.objects.filter(
            student=students[0],
            class_instance__course=course
        )
        
        assert attendance_records.count() == 2, f"Expected 2 attendance records, found {attendance_records.count()}"
        print("✓ 2 attendance records automatically created for confirmed enrollment")
        
        # Verify attendance record details
        for attendance in attendance_records:
            assert attendance.status == 'absent', f"Expected 'absent' status, found '{attendance.status}'"
            assert attendance.class_instance in [class1, class2], "Attendance record linked to wrong class"
        
        print("✓ Attendance records have correct default status and class links")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False
    finally:
        cleanup_test_data()

def test_class_to_enrollment_automation():
    """Test: Add class to course with existing enrollments"""
    print("\n=== Test 2: New class to existing enrollments automation ===")
    
    course, teacher, students = create_test_data()
    
    try:
        # Step 1: Create confirmed enrollments first
        enrollments = []
        for i, student in enumerate(students[:2]):  # Use first 2 students
            enrollment = Enrollment.objects.create(
                student=student,
                course=course,
                status='confirmed',
                source_channel='staff',
                registration_status='returning' if i > 0 else 'new'
            )
            enrollments.append(enrollment)
        
        print(f"Created 2 confirmed enrollments for course '{course.name}'")
        
        # Step 2: Create a new class (this should trigger attendance creation)
        new_class = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=3),
            start_time=time(14, 0),
            duration_minutes=90,
            teacher=teacher,
            is_active=True
        )
        
        print(f"Created new class for {new_class.date} at {new_class.start_time}")
        
        # Verify attendance records were created for all confirmed enrollments
        attendance_records = Attendance.objects.filter(
            class_instance=new_class
        )
        
        assert attendance_records.count() == 2, f"Expected 2 attendance records, found {attendance_records.count()}"
        print("✓ 2 attendance records automatically created for new class")
        
        # Verify each enrolled student has an attendance record
        enrolled_student_ids = {e.student.id for e in enrollments}
        attendance_student_ids = {a.student.id for a in attendance_records}
        
        assert enrolled_student_ids == attendance_student_ids, "Attendance records don't match enrolled students"
        print("✓ Attendance records created for correct students")
        
        # Verify attendance record details
        for attendance in attendance_records:
            assert attendance.status == 'absent', f"Expected 'absent' status, found '{attendance.status}'"
            assert attendance.class_instance == new_class, "Attendance record linked to wrong class"
        
        print("✓ Attendance records have correct default status")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False
    finally:
        cleanup_test_data()

def test_duplicate_prevention():
    """Test: Ensure no duplicate attendance records are created"""
    print("\n=== Test 3: Duplicate prevention ===")
    
    course, teacher, students = create_test_data()
    
    try:
        # Step 1: Create class and enrollment
        test_class = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=5),
            start_time=time(11, 0),
            duration_minutes=60,
            teacher=teacher,
            is_active=True
        )
        
        enrollment = Enrollment.objects.create(
            student=students[0],
            course=course,
            status='confirmed',
            source_channel='staff',
            registration_status='new'
        )
        
        print(f"Created class and confirmed enrollment")
        
        # Step 2: Manually create attendance record
        manual_attendance = Attendance.objects.create(
            student=students[0],
            class_instance=test_class,
            status='present',
            attendance_time=timezone.now()
        )
        
        print(f"Manually created attendance record with 'present' status")
        
        # Step 3: Try to trigger automation again (should not create duplicates)
        result = EnrollmentAttendanceService.auto_create_attendance_for_enrollment(enrollment)
        print(f"Automation result: {result['message']}")
        
        # Verify only one attendance record exists
        attendance_count = Attendance.objects.filter(
            student=students[0],
            class_instance=test_class
        ).count()
        
        assert attendance_count == 1, f"Expected 1 attendance record, found {attendance_count}"
        print("✓ No duplicate attendance records created")
        
        # Verify the original record was not modified
        attendance_record = Attendance.objects.get(
            student=students[0],
            class_instance=test_class
        )
        
        assert attendance_record.status == 'present', f"Expected 'present' status preserved, found '{attendance_record.status}'"
        print("✓ Existing attendance record status preserved")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False
    finally:
        cleanup_test_data()

def test_service_layer():
    """Test: Service layer functions work correctly"""
    print("\n=== Test 4: Service layer functionality ===")
    
    course, teacher, students = create_test_data()
    
    try:
        # Create test data
        test_class = Class.objects.create(
            course=course,
            date=date.today() + timedelta(days=7),
            start_time=time(15, 0),
            duration_minutes=120,
            teacher=teacher,
            is_active=True
        )
        
        enrollment = Enrollment.objects.create(
            student=students[0],
            course=course,
            status='confirmed',
            source_channel='website',
            registration_status='new'
        )
        
        # Test EnrollmentAttendanceService
        result = EnrollmentAttendanceService.auto_create_attendance_for_enrollment(enrollment)
        assert result['status'] == 'success', f"Expected success, got {result['status']}"
        assert result['created_count'] == 1, f"Expected 1 created, got {result['created_count']}"
        print("✓ EnrollmentAttendanceService works correctly")
        
        # Test ClassAttendanceService
        enrollment2 = Enrollment.objects.create(
            student=students[1],
            course=course,
            status='confirmed',
            source_channel='staff',
            registration_status='returning'
        )
        
        result = ClassAttendanceService.auto_create_attendance_for_class(test_class)
        assert result['status'] == 'success', f"Expected success, got {result['status']}"
        assert result['created_count'] == 1, f"Expected 1 created, got {result['created_count']}"
        print("✓ ClassAttendanceService works correctly")
        
        # Test sync service
        result = AttendanceSyncService.sync_all_course_attendance(course)
        assert result['status'] == 'success', f"Expected success, got {result['status']}"
        print("✓ AttendanceSyncService works correctly")
        
        # Verify final state
        total_attendance = Attendance.objects.filter(
            class_instance=test_class
        ).count()
        assert total_attendance == 2, f"Expected 2 total attendance records, found {total_attendance}"
        print("✓ Final attendance count is correct")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False
    finally:
        cleanup_test_data()

def run_all_tests():
    """Run all automation tests"""
    print("Starting automation tests...")
    print("=" * 60)
    
    tests = [
        test_enrollment_to_class_automation,
        test_class_to_enrollment_automation,
        test_duplicate_prevention,
        test_service_layer
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✓ PASSED")
            else:
                failed += 1
                print("✗ FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ FAILED with exception: {str(e)}")
        
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Automation is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)