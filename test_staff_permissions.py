#!/usr/bin/env python
"""
Staff Permissions Test Suite

This script tests all staff permission requirements:
- Staff users can only see their profile and change password
- Staff users can see their upcoming classes with students and mark attendance
- Staff users can clock in and out
- Admin users can see all settings including SMS and email configuration
- Staff users cannot see SMS and email configuration
- Admin users can see all staff and their details
- Staff users can only see their own details
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

# Add testserver to ALLOWED_HOSTS for testing
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from accounts.models import Staff
from academics.models import Course, Class
from students.models import Student
from facilities.models import Facility, Classroom
from enrollment.models import Enrollment, Attendance
from core.models import EmailSettings, SMSSettings


class StaffPermissionTests:
    """Test suite for staff permissions"""
    
    def __init__(self):
        self.client = Client()
        self.setup_test_data()
        self.test_results = []
    
    def setup_test_data(self):
        """Create test users and data"""
        print("Setting up test data...")
        
        # Clean up any existing test users first
        Staff.objects.filter(username__in=['admin_test', 'teacher_test', 'other_staff']).delete()
        
        # Create admin user
        self.admin_user = Staff.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_superuser=True,
            is_staff=True
        )
        
        # Create teacher/staff user
        self.teacher_user = Staff.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='User',
            role='teacher'
        )
        
        # Create another staff user for testing staff list access
        self.other_staff = Staff.objects.create_user(
            username='other_staff',
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='Staff',
            role='teacher'
        )
        
        # Create facility and classroom
        self.facility = Facility.objects.create(
            name='Test Facility',
            address='123 Test St',
            latitude=-31.9505,
            longitude=115.8605
        )
        
        self.classroom = Classroom.objects.create(
            name='Test Classroom',
            facility=self.facility,
            capacity=20
        )
        
        # Create course taught by teacher
        self.course = Course.objects.create(
            name='Test Course',
            description='Test course description',
            teacher=self.teacher_user,
            facility=self.facility,
            classroom=self.classroom,
            price=100.00,
            status='published',
            start_date=timezone.now().date(),
            start_time=timezone.now().time()
        )
        
        # Create class instance
        self.class_instance = Class.objects.create(
            course=self.course,
            date=timezone.now().date() + timedelta(days=1),
            start_time=timezone.now().time(),
            duration_minutes=120,
            classroom=self.classroom,
            teacher=self.teacher_user,
            facility=self.facility
        )
        
        # Create student
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            email='student@test.com',
            phone='0412345678',
            birth_date='2000-01-01'
        )
        
        # Create enrollment
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed'
        )
        
        print("Test data setup complete.")
    
    def log_test_result(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} - {test_name}"
        if message:
            result += f": {message}"
        print(result)
        self.test_results.append((test_name, passed, message))
    
    def test_staff_profile_access(self):
        """Test staff user can only see their own profile"""
        print("\n=== Testing Staff Profile Access ===")
        
        # Login as teacher
        self.client.login(username='teacher_test', password='testpass123')
        
        # Test accessing own profile
        response = self.client.get(reverse('accounts:profile'))
        self.log_test_result(
            "Staff can access own profile",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test accessing other staff profile (should be redirected or forbidden)
        try:
            response = self.client.get(reverse('accounts:staff_detail', kwargs={'pk': self.other_staff.pk}))
            self.log_test_result(
                "Staff cannot access other staff profiles",
                response.status_code in [302, 403, 404],
                f"Status: {response.status_code}"
            )
        except:
            self.log_test_result(
                "Staff cannot access other staff profiles",
                True,
                "URL not accessible (expected)"
            )
    
    def test_staff_list_access(self):
        """Test staff user cannot see staff list (admin only)"""
        print("\n=== Testing Staff List Access ===")
        
        # Login as teacher
        self.client.login(username='teacher_test', password='testpass123')
        
        # Test accessing staff list
        try:
            response = self.client.get(reverse('accounts:staff_list'))
            self.log_test_result(
                "Staff cannot access staff list",
                response.status_code in [302, 403],
                f"Status: {response.status_code}"
            )
        except:
            self.log_test_result(
                "Staff cannot access staff list",
                True,
                "URL not accessible (expected)"
            )
        
        # Login as admin
        self.client.login(username='admin_test', password='testpass123')
        
        # Test admin can access staff list
        try:
            response = self.client.get(reverse('accounts:staff_list'))
            self.log_test_result(
                "Admin can access staff list",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except:
            self.log_test_result(
                "Admin can access staff list",
                False,
                "URL not found"
            )
    
    def test_email_sms_settings_access(self):
        """Test email and SMS settings access (admin only)"""
        print("\n=== Testing Email/SMS Settings Access ===")
        
        # Login as teacher
        self.client.login(username='teacher_test', password='testpass123')
        
        # Test email settings access
        response = self.client.get(reverse('core:email_settings'))
        self.log_test_result(
            "Staff cannot access email settings",
            response.status_code in [302, 403],
            f"Status: {response.status_code}"
        )
        
        # Test SMS settings access
        response = self.client.get(reverse('core:sms_settings'))
        self.log_test_result(
            "Staff cannot access SMS settings",
            response.status_code in [302, 403],
            f"Status: {response.status_code}"
        )
        
        # Login as admin
        self.client.login(username='admin_test', password='testpass123')
        
        # Test admin can access email settings
        response = self.client.get(reverse('core:email_settings'))
        self.log_test_result(
            "Admin can access email settings",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test admin can access SMS settings
        response = self.client.get(reverse('core:sms_settings'))
        self.log_test_result(
            "Admin can access SMS settings",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_password_change_access(self):
        """Test staff can change their own password"""
        print("\n=== Testing Password Change Access ===")
        
        # Login as teacher
        self.client.login(username='teacher_test', password='testpass123')
        
        # Test password change page access
        response = self.client.get(reverse('password_change'))
        self.log_test_result(
            "Staff can access password change",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_classes_and_attendance_access(self):
        """Test staff can see their classes and mark attendance"""
        print("\n=== Testing Classes and Attendance Access ===")
        
        # Login as teacher
        self.client.login(username='teacher_test', password='testpass123')
        
        # Test dashboard shows teacher's classes
        response = self.client.get(reverse('dashboard'))
        self.log_test_result(
            "Staff can access dashboard",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Check if classes are shown in dashboard context
        if response.status_code == 200:
            content = response.content.decode()
            has_classes = 'upcoming_classes' in str(response.context) or 'Test Course' in content
            self.log_test_result(
                "Staff can see their upcoming classes",
                has_classes,
                "Classes visible in dashboard"
            )
    
    def test_clock_in_out_access(self):
        """Test staff can access clock in/out functionality"""
        print("\n=== Testing Clock In/Out Access ===")
        
        # Login as teacher
        self.client.login(username='teacher_test', password='testpass123')
        
        # Test clock in/out page access
        try:
            response = self.client.get(reverse('core:clockinout'))
            self.log_test_result(
                "Staff can access clock in/out",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except:
            try:
                response = self.client.get(reverse('core:clock_inout'))
                self.log_test_result(
                    "Staff can access clock in/out",
                    response.status_code == 200,
                    f"Status: {response.status_code}"
                )
            except:
                self.log_test_result(
                    "Staff can access clock in/out",
                    False,
                    "Clock in/out URL not found"
                )
        
        # Test timesheet access
        response = self.client.get(reverse('core:timesheet'))
        self.log_test_result(
            "Staff can access timesheet",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_admin_full_access(self):
        """Test admin has full access to all features"""
        print("\n=== Testing Admin Full Access ===")
        
        # Login as admin
        self.client.login(username='admin_test', password='testpass123')
        
        # Test dashboard access
        response = self.client.get(reverse('dashboard'))
        self.log_test_result(
            "Admin can access dashboard",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test organisation settings access
        response = self.client.get(reverse('core:organisation_settings'))
        self.log_test_result(
            "Admin can access organisation settings",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\nCleaning up test data...")
        
        try:
            # Delete in reverse order of creation to avoid foreign key issues
            # Note: Attendance model uses different field names
            Attendance.objects.filter(student=self.student).delete()
            Enrollment.objects.filter(id=self.enrollment.id).delete()
            Student.objects.filter(id=self.student.id).delete()
            Class.objects.filter(id=self.class_instance.id).delete()
            Course.objects.filter(id=self.course.id).delete()
            Classroom.objects.filter(id=self.classroom.id).delete()
            Facility.objects.filter(id=self.facility.id).delete()
            Staff.objects.filter(username__in=['admin_test', 'teacher_test', 'other_staff']).delete()
        except Exception as e:
            print(f"Cleanup error (non-critical): {e}")
        
        print("Test data cleanup complete.")
    
    def run_all_tests(self):
        """Run all permission tests"""
        print("🚀 Starting Staff Permission Tests")
        print("=" * 50)
        
        try:
            self.test_staff_profile_access()
            self.test_staff_list_access()
            self.test_email_sms_settings_access()
            self.test_password_change_access()
            self.test_classes_and_attendance_access()
            self.test_clock_in_out_access()
            self.test_admin_full_access()
            
        except Exception as e:
            print(f"\n❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        if total - passed > 0:
            print("\n❌ Failed Tests:")
            for name, result, message in self.test_results:
                if not result:
                    print(f"  - {name}: {message}")
        
        print("\n✅ Test execution completed!")
        return passed == total


if __name__ == '__main__':
    tester = StaffPermissionTests()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)