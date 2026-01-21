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

    def test_export_content(self):
        url = reverse('enrollment:enrollment_export')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        
        content = response.content.decode('utf-8-sig')
        lines = content.strip().split('\n')
        
        # Check header
        self.assertTrue('Enrollment ID' in lines[0])
        self.assertTrue('Student Name' in lines[0])
        
        # Check content - should contain published course
        self.assertTrue('Published Course' in content)
        
        # Check content - should NOT contain draft course
        self.assertFalse('Draft Course' in content)
