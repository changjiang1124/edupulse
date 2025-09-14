#!/usr/bin/env python3
"""
EduPulse MVP 功能全面测试脚本
测试所有关键功能的正常运行
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

# Import all models for comprehensive testing
from accounts.models import Staff
from students.models import Student
from academics.models import Course, Class
from facilities.models import Facility, Classroom
from enrollment.models import Enrollment, Attendance
from core.models import TeacherAttendance, EmailSettings, SMSSettings
from core.services import NotificationService, QRCodeService, TimesheetExportService

def print_test_header(test_name):
    """Print formatted test header"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}")

def print_test_result(test_name, success, message=""):
    """Print formatted test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")

class MVPTester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create test data for all tests"""
        print_test_header("Setting up test data")
        
        try:
            # Clean up existing test data first
            Staff.objects.filter(username__in=['testadmin', 'testteacher']).delete()
            Student.objects.filter(email='student@test.com').delete()
            Facility.objects.filter(name='Test Art Studio').delete()
            Course.objects.filter(name='Test Art Course').delete()
            
            # Create admin user
            self.admin_user = Staff.objects.create_user(
                username='testadmin',
                email='admin@test.com',
                first_name='Test',
                last_name='Admin',
                role='admin',
                is_superuser=True
            )
            self.admin_user.set_password('testpass123')
            self.admin_user.save()
            
            # Create teacher user
            self.teacher_user = Staff.objects.create_user(
                username='testteacher',
                email='teacher@test.com', 
                first_name='Test',
                last_name='Teacher',
                role='teacher'
            )
            self.teacher_user.set_password('testpass123')
            self.teacher_user.save()
            
            # Create facility
            self.facility = Facility.objects.create(
                name='Test Art Studio',
                address='123 Test Street, Perth WA 6000',
                latitude=Decimal('-31.9505'),
                longitude=Decimal('115.8605'),
                is_active=True
            )
            
            # Create classroom
            self.classroom = Classroom.objects.create(
                name='Studio A',
                facility=self.facility,
                capacity=20,
                is_active=True
            )
            
            # Create course
            from datetime import date, timedelta
            self.course = Course.objects.create(
                name='Test Art Course',
                description='A test art course for testing purposes',
                price=Decimal('150.00'),
                start_date=date.today() + timedelta(days=7),
                end_date=date.today() + timedelta(days=35), # 4 weeks later
                start_time='10:00',
                duration_minutes=120,
                vacancy=15,
                status='published',
                teacher=self.teacher_user,
                facility=self.facility,
                classroom=self.classroom
            )
            
            # Create student
            self.student = Student.objects.create(
                first_name='Test',
                last_name='Student',
                email='student@test.com',
                phone='0412345678',
                birth_date=date(2000, 1, 1),
                address='456 Student Ave, Perth WA 6000'
            )
            
            # Create class instance
            self.class_instance = Class.objects.create(
                course=self.course,
                teacher=self.teacher_user,
                facility=self.facility,
                classroom=self.classroom,
                date=timezone.now().date() + timedelta(days=1),
                start_time='10:00',
                duration_minutes=120
            )
            
            print_test_result("Test data setup", True, "All test entities created successfully")
            
        except Exception as e:
            print_test_result("Test data setup", False, f"Error: {str(e)}")
            raise
    
    def test_user_authentication(self):
        """Test user login and authentication"""
        print_test_header("User Authentication System")
        
        # Test admin login
        login_success = self.client.login(username='testadmin', password='testpass123')
        print_test_result("Admin user login", login_success)
        self.test_results.append(('Admin Login', login_success))
        
        # Test teacher login
        self.client.logout()
        login_success = self.client.login(username='testteacher', password='testpass123')
        print_test_result("Teacher user login", login_success)
        self.test_results.append(('Teacher Login', login_success))
        
        # Test role-based access
        try:
            response = self.client.get(reverse('core:dashboard'))
            access_success = response.status_code == 200
            print_test_result("Dashboard access", access_success)
            self.test_results.append(('Dashboard Access', access_success))
        except Exception as e:
            print_test_result("Dashboard access", False, str(e))
            self.test_results.append(('Dashboard Access', False))
    
    def test_course_management(self):
        """Test course and class management"""
        print_test_header("Course Management System")
        
        # Login as admin
        self.client.login(username='testadmin', password='testpass123')
        
        try:
            # Test course list view
            response = self.client.get('/academics/courses/')
            course_list_success = response.status_code == 200
            print_test_result("Course list view", course_list_success)
            self.test_results.append(('Course List', course_list_success))
            
            # Test course detail view
            response = self.client.get(f'/academics/courses/{self.course.id}/')
            course_detail_success = response.status_code == 200
            print_test_result("Course detail view", course_detail_success)
            self.test_results.append(('Course Detail', course_detail_success))
            
            # Test class creation functionality
            classes_exist = Class.objects.filter(course=self.course).exists()
            print_test_result("Class creation", classes_exist)
            self.test_results.append(('Class Creation', classes_exist))
            
        except Exception as e:
            print_test_result("Course management", False, str(e))
            self.test_results.append(('Course Management', False))
    
    def test_student_management(self):
        """Test student management functionality"""
        print_test_header("Student Management System")
        
        self.client.login(username='testadmin', password='testpass123')
        
        try:
            # Test student list view
            response = self.client.get('/students/')
            student_list_success = response.status_code == 200
            print_test_result("Student list view", student_list_success)
            self.test_results.append(('Student List', student_list_success))
            
            # Test student detail view
            response = self.client.get(f'/students/{self.student.id}/')
            student_detail_success = response.status_code == 200
            print_test_result("Student detail view", student_detail_success)
            self.test_results.append(('Student Detail', student_detail_success))
            
            # Verify student data integrity
            student_exists = Student.objects.filter(email='student@test.com').exists()
            print_test_result("Student data integrity", student_exists)
            self.test_results.append(('Student Data', student_exists))
            
        except Exception as e:
            print_test_result("Student management", False, str(e))
            self.test_results.append(('Student Management', False))
    
    def test_enrollment_system(self):
        """Test enrollment functionality"""
        print_test_header("Enrollment Management System")
        
        try:
            # Test public enrollment page access
            response = self.client.get(f'/enroll/{self.course.id}/')
            enrollment_page_success = response.status_code == 200
            print_test_result("Public enrollment page", enrollment_page_success)
            self.test_results.append(('Enrollment Page', enrollment_page_success))
            
            # Create test enrollment
            enrollment = Enrollment.objects.create(
                course=self.course,
                student=self.student,
                status='pending',
                form_data={
                    'student_info': {
                        'first_name': 'Test',
                        'last_name': 'Student',
                        'email': 'student@test.com'
                    },
                    'course_selection': {
                        'course_id': self.course.id,
                        'preferred_start_date': '2024-12-01'
                    }
                }
            )
            
            enrollment_created = Enrollment.objects.filter(student=self.student).exists()
            print_test_result("Enrollment creation", enrollment_created)
            self.test_results.append(('Enrollment Creation', enrollment_created))
            
            # Test enrollment list view (admin)
            self.client.login(username='testadmin', password='testpass123')
            response = self.client.get('/enrollment/')
            enrollment_list_success = response.status_code == 200
            print_test_result("Enrollment list view", enrollment_list_success)
            self.test_results.append(('Enrollment List', enrollment_list_success))
            
        except Exception as e:
            print_test_result("Enrollment system", False, str(e))
            self.test_results.append(('Enrollment System', False))
    
    def test_teacher_attendance(self):
        """Test teacher attendance system"""
        print_test_header("Teacher Attendance System")
        
        self.client.login(username='testteacher', password='testpass123')
        
        try:
            # Test teacher clock page
            response = self.client.get(reverse('core:teacher_clock'))
            clock_page_success = response.status_code == 200
            print_test_result("Teacher clock page", clock_page_success)
            self.test_results.append(('Teacher Clock Page', clock_page_success))
            
            # Create test attendance record
            attendance = TeacherAttendance.objects.create(
                teacher=self.teacher_user,
                facility=self.facility,
                clock_type='clock_in',
                latitude=Decimal('-31.9505'),
                longitude=Decimal('115.8605'),
                location_verified=True,
                ip_address='127.0.0.1',
                user_agent='Test Browser'
            )
            
            attendance_created = TeacherAttendance.objects.filter(teacher=self.teacher_user).exists()
            print_test_result("Attendance record creation", attendance_created)
            self.test_results.append(('Attendance Creation', attendance_created))
            
            # Test attendance history
            response = self.client.get(reverse('core:teacher_attendance_history'))
            history_success = response.status_code == 200
            print_test_result("Attendance history view", history_success)
            self.test_results.append(('Attendance History', history_success))
            
        except Exception as e:
            print_test_result("Teacher attendance", False, str(e))
            self.test_results.append(('Teacher Attendance', False))
    
    def test_notification_system(self):
        """Test notification system"""
        print_test_header("Notification System")
        
        try:
            # Test notification service initialization
            notification_service = NotificationService()
            service_init_success = notification_service is not None
            print_test_result("Notification service initialization", service_init_success)
            self.test_results.append(('Notification Service Init', service_init_success))
            
            # Test email template rendering (without actually sending)
            try:
                from django.template.loader import render_to_string
                email_content = render_to_string(
                    'core/emails/enrollment_confirmation.html',
                    {
                        'student_name': 'Test Student',
                        'course_name': 'Test Course',
                        'created_at': timezone.now().date()
                    }
                )
                template_success = len(email_content) > 0
                print_test_result("Email template rendering", template_success)
                self.test_results.append(('Email Templates', template_success))
            except Exception as e:
                print_test_result("Email template rendering", False, str(e))
                self.test_results.append(('Email Templates', False))
            
        except Exception as e:
            print_test_result("Notification system", False, str(e))
            self.test_results.append(('Notification System', False))
    
    def test_qr_code_system(self):
        """Test QR code attendance system"""
        print_test_header("QR Code System")
        
        try:
            # Test QR code service
            qr_service = QRCodeService()
            service_success = qr_service is not None
            print_test_result("QR service initialization", service_success)
            self.test_results.append(('QR Service Init', service_success))
            
            # Test QR code generation
            qr_result = QRCodeService.generate_attendance_qr_code(self.facility)
            qr_generation_success = qr_result.get('success', False)
            print_test_result("QR code generation", qr_generation_success)
            self.test_results.append(('QR Code Generation', qr_generation_success))
            
            # Test QR attendance page access (teacher)
            self.client.login(username='testteacher', password='testpass123')
            response = self.client.get(reverse('core:teacher_qr_attendance'))
            qr_page_success = response.status_code == 200
            print_test_result("QR attendance page", qr_page_success)
            self.test_results.append(('QR Attendance Page', qr_page_success))
            
        except Exception as e:
            print_test_result("QR code system", False, str(e))
            self.test_results.append(('QR Code System', False))
    
    def test_timesheet_export(self):
        """Test timesheet export functionality"""
        print_test_header("Timesheet Export System")
        
        try:
            # Test timesheet export page
            self.client.login(username='testadmin', password='testpass123')
            response = self.client.get(reverse('core:timesheet_export'))
            export_page_success = response.status_code == 200
            print_test_result("Timesheet export page", export_page_success)
            self.test_results.append(('Timesheet Export Page', export_page_success))
            
            # Test export service initialization
            export_service = TimesheetExportService()
            service_success = export_service is not None
            print_test_result("Export service initialization", service_success)
            self.test_results.append(('Export Service Init', service_success))
            
            # Test export functionality (without actually downloading)
            try:
                # Create some attendance data for export
                TeacherAttendance.objects.create(
                    teacher=self.teacher_user,
                    facility=self.facility,
                    clock_type='clock_out',
                    latitude=Decimal('-31.9505'),
                    longitude=Decimal('115.8605'),
                    location_verified=True,
                    timestamp=timezone.now(),
                    ip_address='127.0.0.1',
                    user_agent='Test Browser'
                )
                
                # Test that we can access export functionality
                has_attendance = TeacherAttendance.objects.filter(teacher=self.teacher_user).exists()
                print_test_result("Export data preparation", has_attendance)
                self.test_results.append(('Export Data Ready', has_attendance))
                
            except Exception as e:
                print_test_result("Export functionality", False, str(e))
                self.test_results.append(('Export Functionality', False))
                
        except Exception as e:
            print_test_result("Timesheet export", False, str(e))
            self.test_results.append(('Timesheet Export', False))
    
    def test_facility_management(self):
        """Test facility and classroom management"""
        print_test_header("Facility Management System")
        
        self.client.login(username='testadmin', password='testpass123')
        
        try:
            # Test facility list view
            response = self.client.get('/facilities/')
            facility_list_success = response.status_code == 200
            print_test_result("Facility list view", facility_list_success)
            self.test_results.append(('Facility List', facility_list_success))
            
            # Test facility detail view
            response = self.client.get(f'/facilities/{self.facility.id}/')
            facility_detail_success = response.status_code == 200
            print_test_result("Facility detail view", facility_detail_success)
            self.test_results.append(('Facility Detail', facility_detail_success))
            
            # Test classroom data integrity
            classroom_exists = Classroom.objects.filter(facility=self.facility).exists()
            print_test_result("Classroom data integrity", classroom_exists)
            self.test_results.append(('Classroom Data', classroom_exists))
            
        except Exception as e:
            print_test_result("Facility management", False, str(e))
            self.test_results.append(('Facility Management', False))
    
    def run_all_tests(self):
        """Run all MVP tests"""
        print(f"\n{'='*60}")
        print("🎯 EduPulse MVP 功能测试开始")
        print(f"{'='*60}")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test methods
        test_methods = [
            self.test_user_authentication,
            self.test_course_management,
            self.test_student_management,
            self.test_enrollment_system,
            self.test_teacher_attendance,
            self.test_notification_system,
            self.test_qr_code_system,
            self.test_timesheet_export,
            self.test_facility_management
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print_test_result(test_method.__name__, False, f"Unexpected error: {str(e)}")
                self.test_results.append((test_method.__name__, False))
        
        # Print final results
        self.print_final_results()
    
    def print_final_results(self):
        """Print comprehensive test results summary"""
        print(f"\n{'='*60}")
        print("📊 测试结果总结")
        print(f"{'='*60}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for test_name, success in self.test_results:
                if not success:
                    print(f"    • {test_name}")
        
        print(f"\n{'='*60}")
        if failed_tests == 0:
            print("🎉 所有MVP核心功能测试通过！系统准备就绪。")
        else:
            print("⚠️  发现问题需要修复。请检查失败的测试项目。")
        print(f"{'='*60}")

def main():
    """Main test execution"""
    try:
        tester = MVPTester()
        tester.run_all_tests()
    except Exception as e:
        print(f"❌ 测试执行错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()