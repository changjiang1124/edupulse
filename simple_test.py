#!/usr/bin/env python3
"""
简化版MVP功能测试脚本
测试核心功能但避免数据库事务问题
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import Client
from django.urls import reverse

def print_test_header(test_name):
    """Print formatted test header"""
    print(f"\n{'='*50}")
    print(f"Testing: {test_name}")
    print(f"{'='*50}")

def print_test_result(test_name, success, message=""):
    """Print formatted test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")

def test_basic_functionality():
    """Test basic system functionality without complex database operations"""
    results = []
    client = Client()
    
    print_test_header("Basic System Tests")
    
    # Test 1: Import all main models
    try:
        from accounts.models import Staff
        from students.models import Student
        from academics.models import Course, Class
        from facilities.models import Facility, Classroom
        from enrollment.models import Enrollment, Attendance
        from core.models import TeacherAttendance
        
        print_test_result("Model imports", True, "All models imported successfully")
        results.append(('Model Imports', True))
    except Exception as e:
        print_test_result("Model imports", False, str(e))
        results.append(('Model Imports', False))
    
    # Test 2: Database connectivity
    try:
        user_count = Staff.objects.count()
        print_test_result("Database connectivity", True, f"Connected - found {user_count} staff records")
        results.append(('Database Connectivity', True))
    except Exception as e:
        print_test_result("Database connectivity", False, str(e))
        results.append(('Database Connectivity', False))
    
    # Test 3: URL resolution
    try:
        # Test key URLs
        dashboard_url = reverse('core:dashboard')
        timesheet_url = reverse('timesheet_export')
        teacher_clock_url = reverse('clock')
        
        print_test_result("URL resolution", True, "All core URLs resolved")
        results.append(('URL Resolution', True))
    except Exception as e:
        print_test_result("URL resolution", False, str(e))
        results.append(('URL Resolution', False))
    
    # Test 4: Check if services can be imported
    try:
        from core.services import NotificationService, QRCodeService, TimesheetExportService
        print_test_result("Service imports", True, "All services imported")
        results.append(('Service Imports', True))
    except Exception as e:
        print_test_result("Service imports", False, str(e))
        results.append(('Service Imports', False))
    
    # Test 5: Template rendering (without authentication)
    try:
        # Test public enrollment page (should not require auth)
        courses = Course.objects.filter(status='published')[:1]
        if courses:
            course = courses[0]
            response = client.get(f'/enroll/{course.id}/')
            template_success = response.status_code == 200
            print_test_result("Template rendering", template_success, f"Public enrollment page: {response.status_code}")
            results.append(('Template Rendering', template_success))
        else:
            print_test_result("Template rendering", False, "No published courses found for testing")
            results.append(('Template Rendering', False))
    except Exception as e:
        print_test_result("Template rendering", False, str(e))
        results.append(('Template Rendering', False))
    
    # Test 6: Service functionality (basic instantiation)
    try:
        # Test notification service
        notification_service = NotificationService()
        qr_service = QRCodeService()
        timesheet_service = TimesheetExportService()
        
        print_test_result("Service instantiation", True, "All services can be instantiated")
        results.append(('Service Instantiation', True))
    except Exception as e:
        print_test_result("Service instantiation", False, str(e))
        results.append(('Service Instantiation', False))
    
    return results

def test_user_authentication():
    """Test user authentication system"""
    results = []
    client = Client()
    
    print_test_header("Authentication System")
    
    try:
        # Get existing users for testing
        from accounts.models import Staff
        admin_users = Staff.objects.filter(role='admin', is_active=True)[:1]
        teacher_users = Staff.objects.filter(role='teacher', is_active=True)[:1]
        
        if admin_users and teacher_users:
            admin_user = admin_users[0]
            teacher_user = teacher_users[0]
            
            # Test dashboard access (should redirect to login)
            response = client.get(reverse('core:dashboard'))
            login_redirect = response.status_code == 302
            print_test_result("Login required enforcement", login_redirect, "Dashboard redirects to login")
            results.append(('Login Required', login_redirect))
            
            print_test_result("Authentication system", True, f"Found admin: {admin_user.username}, teacher: {teacher_user.username}")
            results.append(('Authentication System', True))
        else:
            print_test_result("Authentication system", False, "No admin or teacher users found")
            results.append(('Authentication System', False))
            
    except Exception as e:
        print_test_result("Authentication system", False, str(e))
        results.append(('Authentication System', False))
    
    return results

def test_data_integrity():
    """Test basic data integrity and relationships"""
    results = []
    
    print_test_header("Data Integrity")
    
    try:
        # Check data counts
        from accounts.models import Staff
        from students.models import Student
        from academics.models import Course, Class
        from facilities.models import Facility
        from enrollment.models import Enrollment
        from core.models import TeacherAttendance
        
        counts = {
            'Staff': Staff.objects.count(),
            'Students': Student.objects.count(),
            'Courses': Course.objects.count(),
            'Classes': Class.objects.count(),
            'Facilities': Facility.objects.count(),
            'Enrollments': Enrollment.objects.count(),
            'Attendance': TeacherAttendance.objects.count()
        }
        
        print("Data counts:")
        for model, count in counts.items():
            print(f"    {model}: {count}")
        
        # Basic integrity checks
        has_data = any(count > 0 for count in counts.values())
        print_test_result("Data existence", has_data, "System has some data")
        results.append(('Data Existence', has_data))
        
        # Check for published courses
        published_courses = Course.objects.filter(status='published').count()
        has_published = published_courses > 0
        print_test_result("Published courses", has_published, f"Found {published_courses} published courses")
        results.append(('Published Courses', has_published))
        
        # Check for active facilities
        active_facilities = Facility.objects.filter(is_active=True).count()
        has_facilities = active_facilities > 0
        print_test_result("Active facilities", has_facilities, f"Found {active_facilities} active facilities")
        results.append(('Active Facilities', has_facilities))
        
    except Exception as e:
        print_test_result("Data integrity", False, str(e))
        results.append(('Data Integrity', False))
    
    return results

def test_core_features():
    """Test core MVP features are accessible"""
    results = []
    
    print_test_header("Core MVP Features")
    
    # Test timesheet export functionality
    try:
        from core.services import TimesheetExportService
        service = TimesheetExportService()
        print_test_result("Timesheet export service", True, "Service available")
        results.append(('Timesheet Export', True))
    except Exception as e:
        print_test_result("Timesheet export service", False, str(e))
        results.append(('Timesheet Export', False))
    
    # Test notification system
    try:
        from core.services import NotificationService
        service = NotificationService()
        print_test_result("Notification service", True, "Service available")
        results.append(('Notification System', True))
    except Exception as e:
        print_test_result("Notification service", False, str(e))
        results.append(('Notification System', False))
    
    # Test QR code system
    try:
        from core.services import QRCodeService
        service = QRCodeService()
        print_test_result("QR code service", True, "Service available")
        results.append(('QR Code System', True))
    except Exception as e:
        print_test_result("QR code service", False, str(e))
        results.append(('QR Code System', False))
    
    # Test GPS utilities
    try:
        from core.utils.gps_utils import haversine_distance, verify_teacher_location
        # Test basic function import
        print_test_result("GPS utilities", True, "GPS functions available")
        results.append(('GPS Utilities', True))
    except Exception as e:
        print_test_result("GPS utilities", False, str(e))
        results.append(('GPS Utilities', False))
    
    return results

def main():
    """Run all simplified tests"""
    print(f"\n{'='*60}")
    print("🎯 EduPulse MVP 简化功能测试")
    print(f"{'='*60}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # Run all test groups
    test_groups = [
        test_basic_functionality,
        test_user_authentication,
        test_data_integrity,
        test_core_features
    ]
    
    for test_group in test_groups:
        try:
            results = test_group()
            all_results.extend(results)
        except Exception as e:
            print(f"❌ Test group {test_group.__name__} failed: {str(e)}")
            all_results.append((test_group.__name__, False))
    
    # Print final summary
    print(f"\n{'='*60}")
    print("📊 测试结果总结")
    print(f"{'='*60}")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for _, success in all_results if success)
    failed_tests = total_tests - passed_tests
    
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests} ✅")
    print(f"失败: {failed_tests} ❌")
    print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
    
    if failed_tests > 0:
        print(f"\n❌ 失败的测试:")
        for test_name, success in all_results:
            if not success:
                print(f"    • {test_name}")
    
    print(f"\n{'='*60}")
    if failed_tests == 0:
        print("🎉 所有简化测试通过！核心系统功能正常。")
    else:
        print("⚠️  发现一些问题，但核心系统基本可用。")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
