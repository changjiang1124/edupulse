from datetime import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academics.models import Course


@override_settings(SECURE_SSL_REDIRECT=False)
class CourseListTeacherFilterTests(TestCase):
    def setUp(self):
        patcher = patch('academics.signals.WooCommerceSyncService')
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='course-admin',
            password='Admin123!',
            first_name='Course',
            last_name='Admin',
            role='admin',
        )
        self.teacher = user_model.objects.create_user(
            username='filtered-teacher',
            password='Teacher123!',
            first_name='Filtered',
            last_name='Teacher',
            role='teacher',
        )
        self.other_teacher = user_model.objects.create_user(
            username='other-teacher',
            password='Teacher123!',
            first_name='Other',
            last_name='Teacher',
            role='teacher',
        )

        start_date = timezone.localdate()
        start_time = time(hour=10, minute=0)

        self.filtered_course = Course.objects.create(
            name='Filtered Teacher Course',
            start_date=start_date,
            start_time=start_time,
            duration_minutes=60,
            price=100.00,
            status='archived',
            teacher=self.teacher,
        )
        self.other_course = Course.objects.create(
            name='Other Teacher Course',
            start_date=start_date,
            start_time=start_time,
            duration_minutes=60,
            price=120.00,
            status='published',
            teacher=self.other_teacher,
        )

        self.client = Client()

    def test_course_list_filters_by_teacher_and_preserves_teacher_context(self):
        self.client.login(username='course-admin', password='Admin123!')

        response = self.client.get(
            reverse('academics:course_list'),
            {'teacher': str(self.teacher.pk), 'status': 'all'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher filter:')
        self.assertContains(response, 'Filtered Teacher Course')
        self.assertNotContains(response, 'Other Teacher Course')
        self.assertContains(response, f'name="teacher" value="{self.teacher.pk}"')
        self.assertContains(
            response,
            f"{reverse('academics:class_list')}?teacher={self.teacher.pk}",
        )
