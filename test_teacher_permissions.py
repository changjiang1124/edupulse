#!/usr/bin/env python
"""
Test script for Teacher Permissions System
Tests all aspects of the teacher permission control implementation
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

# Override ALLOWED_HOSTS for testing
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import Staff
from academics.models import Course, Class
from students.models import Student
from enrollment.models import Enrollment
from facilities.models import Facility, Classroom
from datetime import date, time
from decimal import Decimal

def create_test_data():
    """Create test data for permission testing"""
    print("🔧 Creating test data...")
    
    # Create test facility
    facility = Facility.objects.get_or_create(
        name="Test Facility",
        defaults={
            'address': "123 Test St",
            'is_active': True,
            'latitude': -31.9505,
            'longitude': 115.8605
        }
    )[0]
    
    # Create test classroom
    classroom = Classroom.objects.get_or_create(
        name="Room 1",
        facility=facility,
        defaults={'capacity': 20, 'is_active': True}
    )[0]
    
    # Create admin user
    admin_user = Staff.objects.get_or_create(
        username="admin_test",
        defaults={
            'email': 'admin@test.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'admin',
            'is_active': True,
            'is_staff': True,
            'is_superuser': True
        }
    )[0]
    admin_user.set_password('testpass123')
    admin_user.save()
    
    # Create teacher user
    teacher_user = Staff.objects.get_or_create(
        username="teacher_test",
        defaults={
            'email': 'teacher@test.com',
            'first_name': 'Teacher',
            'last_name': 'User',
            'role': 'teacher',
            'is_active': True,
            'is_staff': True
        }
    )[0]
    teacher_user.set_password('testpass123')
    teacher_user.save()
    
    # Create another teacher for testing access restrictions
    other_teacher = Staff.objects.get_or_create(
        username="other_teacher",
        defaults={
            'email': 'other@test.com',
            'first_name': 'Other',
            'last_name': 'Teacher',
            'role': 'teacher',
            'is_active': True,
            'is_staff': True
        }
    )[0]
    other_teacher.set_password('testpass123')
    other_teacher.save()
    
    # Create test student
    student = Student.objects.get_or_create(
        email="student@test.com",
        defaults={
            'first_name': 'Test',
            'last_name': 'Student',
            'phone': '0412345678',
            'birth_date': date(1990, 1, 1),
            'is_active': True
        }
    )[0]
    
    # Create teacher's course
    teacher_course = Course.objects.get_or_create(
        name="Teacher's Course",
        defaults={
            'teacher': teacher_user,
            'price': Decimal('100.00'),
            'facility': facility,
            'classroom': classroom,
            'start_time': time(9, 0),
            'duration_minutes': 60,
            'status': 'published',
            'repeat_pattern': 'weekly',
            'start_date': date.today(),
            'end_date': date(2025, 12, 31)
        }
    )[0]
    
    # Create other teacher's course
    other_course = Course.objects.get_or_create(
        name="Other Teacher's Course",
        defaults={
            'teacher': other_teacher,
            'price': Decimal('150.00'),
            'facility': facility,
            'classroom': classroom,
            'start_time': time(11, 0),
            'duration_minutes': 90,
            'status': 'published',
            'repeat_pattern': 'weekly',
            'start_date': date.today(),
            'end_date': date(2025, 12, 31)
        }
    )[0]
    
    # Create classes for both courses
    teacher_class = Class.objects.get_or_create(
        course=teacher_course,
        date=date.today(),
        defaults={
            'teacher': teacher_user,
            'start_time': time(9, 0),
            'duration_minutes': 60,
            'facility': facility,
            'classroom': classroom,
            'is_active': True
        }
    )[0]
    
    other_class = Class.objects.get_or_create(
        course=other_course,
        date=date.today(),
        defaults={
            'teacher': other_teacher,
            'start_time': time(11, 0),
            'duration_minutes': 90,
            'facility': facility,
            'classroom': classroom,
            'is_active': True
        }
    )[0]
    
    # Create enrollment
    enrollment = Enrollment.objects.get_or_create(
        student=student,
        course=teacher_course,
        defaults={
            'status': 'confirmed',
            'form_data': {'test': 'data'}
        }
    )[0]
    
    print("✅ Test data created successfully")
    return {
        'admin_user': admin_user,
        'teacher_user': teacher_user,
        'other_teacher': other_teacher,
        'student': student,
        'teacher_course': teacher_course,
        'other_course': other_course,
        'teacher_class': teacher_class,
        'other_class': other_class,
        'enrollment': enrollment,
        'facility': facility,
        'classroom': classroom
    }

def test_navigation_permissions():
    """Test navigation menu permissions"""
    print("\n🧭 Testing Navigation Permissions...")
    client = Client()
    
    # Test admin navigation
    print("  📋 Testing admin navigation...")
    admin = Staff.objects.get(username="admin_test")
    client.force_login(admin)
    
    response = client.get('/')
    assert response.status_code == 200
    content = response.content.decode()
    
    # Admin should see all navigation items
    assert 'Students' in content, "Admin should see Students menu"
    assert 'Courses' in content, "Admin should see Courses menu"
    assert 'Enrollments' in content, "Admin should see Enrollments menu"
    assert 'Staff' in content, "Admin should see Staff menu"
    assert 'Facilities' in content, "Admin should see Facilities menu"
    print("    ✅ Admin navigation correct")
    
    # Test teacher navigation
    print("  👨‍🏫 Testing teacher navigation...")
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    response = client.get('/')
    assert response.status_code == 200
    content = response.content.decode()
    
    # Teacher should NOT see admin menus
    assert 'Students</a>' not in content, "Teacher should NOT see Students menu"
    assert 'Courses</a>' not in content, "Teacher should NOT see Courses menu"
    assert 'Enrollments</a>' not in content, "Teacher should NOT see Enrollments menu"
    assert 'Staff</a>' not in content, "Teacher should NOT see Staff menu"
    assert 'Facilities</a>' not in content, "Teacher should NOT see Facilities menu"
    
    # Teacher should see My Classes
    assert 'My Classes' in content, "Teacher should see My Classes menu"
    
    # Check dropdown menu
    assert 'Profile' in content, "Teacher should see Profile in dropdown"
    assert 'Change Password' in content, "Teacher should see Change Password in dropdown"
    assert 'Clock In/Out' in content, "Teacher should see Clock In/Out in dropdown"
    assert 'My Attendance History' in content, "Teacher should see Attendance History in dropdown"
    print("    ✅ Teacher navigation correct")

def test_profile_access():
    """Test profile page access"""
    print("\n👤 Testing Profile Access...")
    client = Client()
    
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    # Test profile access
    response = client.get('/accounts/profile/')
    assert response.status_code == 200
    content = response.content.decode()
    
    # Should see profile but not management buttons
    assert 'Teacher' in content, "Should see user name"
    assert 'My Profile' in content, "Should show My Profile title"
    assert 'Edit Staff' not in content, "Should NOT see Edit Staff button"
    assert 'Back to Staff' not in content, "Should NOT see Back to Staff button"
    print("  ✅ Profile access working correctly")

def test_password_change():
    """Test password change functionality"""
    print("\n🔑 Testing Password Change...")
    client = Client()
    
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    # Test password change form access
    response = client.get('/auth/password_change/')
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Change Password' in content, "Should show password change form"
    print("  ✅ Password change form accessible")

def test_class_data_filtering():
    """Test class list data filtering for teachers"""
    print("\n📚 Testing Class Data Filtering...")
    client = Client()
    
    # Test teacher class filtering
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    response = client.get('/academics/classes/')
    assert response.status_code == 200
    content = response.content.decode()
    
    # Teacher should only see their own classes
    assert "Teacher's Course" in content, "Teacher should see their own course"
    assert "Other Teacher's Course" not in content, "Teacher should NOT see other teacher's course"
    print("  ✅ Class filtering working correctly")
    
    # Test class detail access
    teacher_class = Class.objects.get(course__name="Teacher's Course")
    other_class = Class.objects.get(course__name="Other Teacher's Course")
    
    # Should access own class
    response = client.get(f'/academics/classes/{teacher_class.pk}/')
    assert response.status_code == 200
    print("  ✅ Teacher can access own class details")
    
    # Should NOT access other teacher's class
    response = client.get(f'/academics/classes/{other_class.pk}/')
    assert response.status_code == 404, "Teacher should NOT access other teacher's class"
    print("  ✅ Teacher blocked from other teacher's class")

def test_dashboard_filtering():
    """Test dashboard data filtering"""
    print("\n📊 Testing Dashboard Data Filtering...")
    client = Client()
    
    # Test admin dashboard
    admin = Staff.objects.get(username="admin_test")
    client.force_login(admin)
    
    response = client.get('/')
    assert response.status_code == 200
    content = response.content.decode()
    
    # Admin should see full statistics
    assert 'Add Student' in content, "Admin should see Add Student button"
    assert 'Create Course' in content, "Admin should see Create Course button"
    print("  ✅ Admin dashboard shows full access")
    
    # Test teacher dashboard
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    response = client.get('/')
    assert response.status_code == 200
    content = response.content.decode()
    
    # Teacher should see limited quick actions
    assert 'My Classes' in content, "Teacher should see My Classes button"
    assert 'Clock In/Out' in content, "Teacher should see Clock In/Out button"
    assert 'My Attendance' in content, "Teacher should see My Attendance button"
    
    # Teacher should NOT see admin buttons
    assert 'Add Student</a>' not in content, "Teacher should NOT see Add Student admin button"
    assert 'Create Course</a>' not in content, "Teacher should NOT see Create Course admin button"
    print("  ✅ Teacher dashboard shows limited access")

def test_attendance_permissions():
    """Test attendance marking permissions"""
    print("\n📋 Testing Attendance Permissions...")
    client = Client()
    
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    teacher_class = Class.objects.get(course__name="Teacher's Course")
    other_class = Class.objects.get(course__name="Other Teacher's Course")
    
    # Should access own class attendance
    response = client.get(f'/enrollment/attendance/mark/{teacher_class.pk}/')
    assert response.status_code == 200
    print("  ✅ Teacher can access own class attendance")
    
    # Should NOT access other teacher's class attendance  
    response = client.get(f'/enrollment/attendance/mark/{other_class.pk}/')
    assert response.status_code == 302, "Teacher should be redirected from other teacher's attendance"
    print("  ✅ Teacher blocked from other teacher's attendance")
    
    # Test admin access to attendance list (should work)
    admin = Staff.objects.get(username="admin_test")
    client.force_login(admin)
    
    response = client.get('/enrollment/attendance/')
    assert response.status_code == 200
    print("  ✅ Admin can access attendance list")
    
    # Test teacher access to attendance list (should be blocked)
    client.force_login(teacher)
    response = client.get('/enrollment/attendance/')
    assert response.status_code == 403, "Teacher should be blocked from attendance list"
    print("  ✅ Teacher blocked from attendance list")

def test_template_button_visibility():
    """Test template button visibility based on role"""
    print("\n👁️ Testing Template Button Visibility...")
    client = Client()
    
    # Test class list buttons for admin
    admin = Staff.objects.get(username="admin_test")
    client.force_login(admin)
    
    response = client.get('/academics/classes/')
    assert response.status_code == 200
    content = response.content.decode()
    assert 'fa-edit' in content, "Admin should see edit buttons"
    print("  ✅ Admin sees edit buttons")
    
    # Test class list buttons for teacher
    teacher = Staff.objects.get(username="teacher_test")
    client.force_login(teacher)
    
    response = client.get('/academics/classes/')
    assert response.status_code == 200
    content = response.content.decode()
    # Should NOT see edit buttons for teachers
    assert 'Add New Class' not in content, "Teacher should NOT see Add New Class button"
    print("  ✅ Teacher doesn't see admin buttons")

def run_all_tests():
    """Run all permission tests"""
    print("🚀 Starting Teacher Permissions System Tests")
    print("=" * 60)
    
    try:
        # Create test data
        test_data = create_test_data()
        
        # Run all tests
        test_navigation_permissions()
        test_profile_access()
        test_password_change()
        test_class_data_filtering()
        test_dashboard_filtering()
        test_attendance_permissions()
        test_template_button_visibility()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Teacher permissions system working correctly!")
        print("\n📋 Test Summary:")
        print("  ✅ Navigation permissions - PASS")
        print("  ✅ Profile access control - PASS") 
        print("  ✅ Password change functionality - PASS")
        print("  ✅ Class data filtering - PASS")
        print("  ✅ Dashboard data filtering - PASS")
        print("  ✅ Attendance permissions - PASS")
        print("  ✅ Template button visibility - PASS")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return False
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)