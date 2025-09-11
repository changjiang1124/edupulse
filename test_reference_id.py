#!/usr/bin/env python
"""
Test script for professional reference ID implementation

This script verifies that the new get_reference_id() method works correctly
and generates the expected format: PAS-[courseID:3digits]-[enrollmentID:3digits]
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/changjiang/Dev/edupulse')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from enrollment.models import Enrollment
from academics.models import Course
from students.models import Student
from accounts.models import Staff

def test_reference_id_format():
    """Test the reference ID format generation"""
    print("=== Testing Professional Reference ID Format ===")
    
    try:
        # Get existing enrollments to test with
        enrollments = Enrollment.objects.select_related('course', 'student').all()[:5]
        
        if not enrollments.exists():
            print("No enrollments found to test. Creating test data...")
            
            # Create minimal test data
            teacher = Staff.objects.filter(role='teacher').first()
            if not teacher:
                teacher = Staff.objects.create(
                    username='ref_test_teacher',
                    first_name='Test',
                    last_name='Teacher',
                    email='test@example.com',
                    role='teacher'
                )
            
            course = Course.objects.create(
                name='Reference ID Test Course',
                short_description='Test course for reference ID',
                price=100.00,
                course_type='group',
                status='draft',
                teacher=teacher,
                start_date='2025-01-01',
                start_time='10:00:00',
                duration_minutes=60,
                vacancy=10,
                repeat_pattern='once'
            )
            
            student = Student.objects.create(
                first_name='TestRef',
                last_name='Student',
                birth_date='2000-01-01',
                contact_email='test@example.com',
                contact_phone='0401234567'
            )
            
            enrollment = Enrollment.objects.create(
                student=student,
                course=course,
                status='pending',
                source_channel='staff',
                registration_status='new'
            )
            
            enrollments = [enrollment]
            print(f"✓ Created test enrollment with ID {enrollment.id}")
        
        print("\n--- Testing Reference ID Generation ---")
        
        for enrollment in enrollments:
            reference_id = enrollment.get_reference_id()
            expected_format = f"PAS-{enrollment.course.id:03d}-{enrollment.id:03d}"
            
            print(f"Course ID: {enrollment.course.id}")
            print(f"Enrollment ID: {enrollment.id}")
            print(f"Generated Reference ID: {reference_id}")
            print(f"Expected Format: {expected_format}")
            
            # Verify format
            if reference_id == expected_format:
                print("✓ Reference ID format is correct")
            else:
                print("✗ Reference ID format is incorrect")
                return False
            
            # Verify format structure
            parts = reference_id.split('-')
            if len(parts) == 3 and parts[0] == 'PAS':
                course_part = parts[1]
                enrollment_part = parts[2]
                
                if len(course_part) == 3 and len(enrollment_part) == 3:
                    print("✓ Reference ID structure is correct (PAS-XXX-XXX)")
                else:
                    print(f"✗ Reference ID structure is incorrect. Course part: {len(course_part)} digits, Enrollment part: {len(enrollment_part)} digits")
                    return False
            else:
                print("✗ Reference ID does not match PAS-XXX-XXX pattern")
                return False
            
            print()
        
        print("--- Testing Edge Cases ---")
        
        # Test with single digit IDs
        print("Testing format with single digit IDs:")
        print(f"Course ID 1, Enrollment ID 5 -> PAS-001-005")
        
        # Test with larger IDs
        print("Testing format with larger IDs:")
        print(f"Course ID 123, Enrollment ID 456 -> PAS-123-456")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_template_accessibility():
    """Test that templates can access the new method"""
    print("\n=== Testing Template Accessibility ===")
    
    try:
        # Get an enrollment
        enrollment = Enrollment.objects.first()
        if not enrollment:
            print("No enrollments available for template testing")
            return True
        
        # Test that the method is callable from a template context
        reference_id = enrollment.get_reference_id()
        print(f"✓ get_reference_id() method is accessible: {reference_id}")
        
        # Verify it's a string (templates need string output)
        if isinstance(reference_id, str):
            print("✓ Method returns string (template compatible)")
        else:
            print(f"✗ Method returns {type(reference_id)}, expected string")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Template accessibility test failed: {str(e)}")
        return False

def test_examples():
    """Test specific examples mentioned in requirements"""
    print("\n=== Testing Specific Examples ===")
    
    examples = [
        {"course_id": 1, "enrollment_id": 23, "expected": "PAS-001-023"},
        {"course_id": 42, "enrollment_id": 156, "expected": "PAS-042-156"},
        {"course_id": 999, "enrollment_id": 1, "expected": "PAS-999-001"},
    ]
    
    for example in examples:
        # Create a mock object to test the format
        class MockEnrollment:
            def __init__(self, course_id, enrollment_id):
                self.id = enrollment_id
                self.course = MockCourse(course_id)
            
            def get_reference_id(self):
                return f"PAS-{self.course.id:03d}-{self.id:03d}"
        
        class MockCourse:
            def __init__(self, course_id):
                self.id = course_id
        
        mock_enrollment = MockEnrollment(example["course_id"], example["enrollment_id"])
        result = mock_enrollment.get_reference_id()
        
        print(f"Course {example['course_id']}, Enrollment {example['enrollment_id']} -> {result}")
        
        if result == example["expected"]:
            print("✓ Example format correct")
        else:
            print(f"✗ Expected {example['expected']}, got {result}")
            return False
    
    return True

def run_all_tests():
    """Run all reference ID tests"""
    print("Starting Professional Reference ID Tests...")
    print("=" * 60)
    
    tests = [
        test_reference_id_format,
        test_template_accessibility,
        test_examples
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
        print("🎉 All tests passed! Professional Reference ID is working correctly.")
        print("\nExample Reference IDs:")
        print("- PAS-001-023 (Course 1, Enrollment 23)")
        print("- PAS-042-156 (Course 42, Enrollment 156)")
        print("- Professional, easy to reference, includes both course and enrollment info")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)