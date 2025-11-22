from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time

from students.models import Student
from academics.models import Course
from enrollment.models import Enrollment


class EnrollmentDetailTemplateTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role='admin',
            is_staff=True,
        )
        self.client.login(username='admin', password='testpass123')

        self.student = Student.objects.create(first_name='Test', last_name='Student')
        today = timezone.now().date()
        start_time = time(9, 0)
        self.course = Course.objects.create(
            name='Test Course',
            price=100.00,
            status='published',
            start_date=today,
            start_time=start_time,
            duration_minutes=60,
            vacancy=10,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='pending',
            source_channel='form',
        )

    def test_detail_view_renders(self):
        response = self.client.get(f'/enroll/enrollments/{self.enrollment.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enrollment Information')
