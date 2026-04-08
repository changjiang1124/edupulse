from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
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


class EnrollmentListFilterTemplateTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin-list',
            email='admin-list@test.com',
            password='testpass123',
            role='admin',
            is_staff=True,
        )
        self.client.login(username='admin-list', password='testpass123')

        self.student = Student.objects.create(
            first_name='Filter',
            last_name='Student',
            contact_email='filter@test.com',
        )
        today = timezone.now().date()
        start_time = time(10, 0)

        self.published_course = Course.objects.create(
            name='Published Course',
            price=100.00,
            status='published',
            start_date=today,
            start_time=start_time,
        )
        self.draft_course = Course.objects.create(
            name='Draft Course',
            price=100.00,
            status='draft',
            start_date=today,
            start_time=start_time,
        )
        self.expired_course = Course.objects.create(
            name='Expired Course',
            price=100.00,
            status='expired',
            start_date=today,
            start_time=start_time,
        )
        self.archived_course = Course.objects.create(
            name='Archived Course',
            price=100.00,
            status='archived',
            start_date=today,
            start_time=start_time,
        )

        for course in (
            self.published_course,
            self.draft_course,
            self.expired_course,
            self.archived_course,
        ):
            Enrollment.objects.create(
                student=self.student,
                course=course,
                status='confirmed',
            )

    def test_default_view_shows_published_courses_only(self):
        response = self.client.get(reverse('enrollment:enrollment_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_course_view'], 'current')
        self.assertEqual(response.context['current_course_status'], '')
        self.assertEqual(
            [course.name for course in response.context['courses']],
            ['Published Course'],
        )
        self.assertEqual(
            [enrollment.course.name for enrollment in response.context['enrollments']],
            ['Published Course'],
        )
        self.assertContains(response, 'Showing published courses only.')
        self.assertNotContains(response, 'Draft Course')
        self.assertNotContains(response, 'Expired Course')
        self.assertNotContains(response, 'Archived Course')

    def test_historical_view_shows_non_published_courses_only(self):
        response = self.client.get(
            reverse('enrollment:enrollment_list'),
            {'course_view': 'historical'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_course_view'], 'historical')
        self.assertEqual(response.context['current_course_status'], '')
        self.assertCountEqual(
            [course.name for course in response.context['courses']],
            ['Draft Course', 'Expired Course', 'Archived Course'],
        )
        self.assertCountEqual(
            [enrollment.course.name for enrollment in response.context['enrollments']],
            ['Draft Course', 'Expired Course', 'Archived Course'],
        )
        self.assertContains(response, 'Showing draft, expired, and archived courses.')
        self.assertNotContains(response, 'Published Course')

    def test_historical_status_filter_narrows_dropdown_and_results(self):
        response = self.client.get(
            reverse('enrollment:enrollment_list'),
            {'course_view': 'historical', 'course_status': 'expired'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_course_view'], 'historical')
        self.assertEqual(response.context['current_course_status'], 'expired')
        self.assertEqual(
            [course.name for course in response.context['courses']],
            ['Expired Course'],
        )
        self.assertEqual(
            [enrollment.course.name for enrollment in response.context['enrollments']],
            ['Expired Course'],
        )

    def test_selected_historical_course_auto_switches_view(self):
        response = self.client.get(
            reverse('enrollment:enrollment_list'),
            {'course': self.archived_course.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_course_view'], 'historical')
        self.assertEqual(response.context['current_course_status'], 'archived')
        self.assertEqual(response.context['selected_course_id'], str(self.archived_course.pk))
        self.assertEqual(
            [course.name for course in response.context['courses']],
            ['Archived Course'],
        )
        self.assertContains(
            response,
            'name="course_view" value="historical"',
            html=False,
        )

    def test_legacy_all_status_link_keeps_all_courses_visible(self):
        response = self.client.get(
            reverse('enrollment:enrollment_list'),
            {'course_status': 'all'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_course_view'], 'historical')
        self.assertEqual(response.context['course_scope_mode'], 'all')
        self.assertEqual(response.context['current_course_status'], 'all')
        self.assertTrue(response.context['is_legacy_all_course_status'])
        self.assertCountEqual(
            [course.name for course in response.context['courses']],
            ['Published Course', 'Draft Course', 'Expired Course', 'Archived Course'],
        )
        self.assertContains(response, 'Showing all course statuses via a legacy compatibility link.')
        self.assertContains(response, 'All Statuses (Legacy Link)')
        self.assertNotContains(response, 'Showing draft, expired, and archived courses.')

    def test_persisted_legacy_all_querystring_still_shows_all_courses(self):
        response = self.client.get(
            reverse('enrollment:enrollment_list'),
            {'course_view': 'historical', 'course_status': 'all'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['course_scope_mode'], 'all')
        self.assertEqual(response.context['filter_querystring'], 'course_view=historical&course_status=all')
        self.assertEqual(
            response.context['enrollment_export_url'],
            f"{reverse('enrollment:enrollment_export')}?course_view=historical&course_status=all",
        )
        self.assertCountEqual(
            [enrollment.course.name for enrollment in response.context['enrollments']],
            ['Published Course', 'Draft Course', 'Expired Course', 'Archived Course'],
        )
