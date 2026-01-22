from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from enrollment.models import Enrollment
from students.models import Student
from academics.models import Course
from accounts.models import Staff

class EnrollmentExportTest(TestCase):
    def setUp(self):
        # Create admin user
        self.user = Staff.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123',
            role='admin'
        )
        self.client = Client()
        self.client.force_login(self.user)

        # Create student
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            contact_email='test@example.com',
            birth_date=timezone.now().date()
        )

        # Create courses
        self.published_course = Course.objects.create(
            name='Published Course',
            status='published',
            price=100.00,
            start_date=timezone.now().date(),
            start_time=timezone.now().time()
        )
        
        self.draft_course = Course.objects.create(
            name='Draft Course',
            status='draft',
            price=100.00,
            start_date=timezone.now().date(),
            start_time=timezone.now().time()
        )

        # Create enrollments
        Enrollment.objects.create(
            student=self.student,
            course=self.published_course,
            status='confirmed'
        )
        
        Enrollment.objects.create(
            student=self.student,
            course=self.draft_course,
            status='confirmed'
        )

    def test_export_access(self):
        # Test that non-admin cannot access
        self.client.logout()
        url = reverse('enrollment:enrollment_export')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_export_default_filtering(self):
        """Test that default export only includes published courses"""
        url = reverse('enrollment:enrollment_export')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        
        content = response.content.decode('utf-8-sig')
        # Check content - should contain published course
        self.assertTrue('Published Course' in content)
        # Check content - should NOT contain draft course
        self.assertFalse('Draft Course' in content)

    def test_export_draft_filtering(self):
        """Test export with draft status filter"""
        url = reverse('enrollment:enrollment_export')
        response = self.client.get(url, {'course_status': 'draft'})
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        
        # Should contain draft course
        self.assertTrue('Draft Course' in content)
        # Should NOT contain published course
        self.assertFalse('Published Course' in content)

    def test_export_all_filtering(self):
        """Test export with all status filter"""
        url = reverse('enrollment:enrollment_export')
        response = self.client.get(url, {'course_status': 'all'})
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        
        # Should contain BOTH courses
        self.assertTrue('Published Course' in content)
        self.assertTrue('Draft Course' in content)
