from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import Staff
from academics.models import Class, Course
from enrollment.models import Enrollment
from students.models import Student


class ClassAddStudentsDeprecatedTests(TestCase):
    def setUp(self):
        self.admin = Staff.objects.create_user(
            username='deprecated-endpoint-admin',
            password='pass',
            is_staff=True,
            is_superuser=True,
            role='admin'
        )
        self.teacher_a = Staff.objects.create_user(
            username='makeup-teacher-a',
            password='pass',
            role='teacher'
        )
        self.teacher_a._preserve_is_staff = True
        self.teacher_a.is_staff = True
        self.teacher_a.save(update_fields=['is_staff'])
        self.teacher_b = Staff.objects.create_user(
            username='makeup-teacher-b',
            password='pass',
            role='teacher'
        )
        self.teacher_b._preserve_is_staff = True
        self.teacher_b.is_staff = True
        self.teacher_b.save(update_fields=['is_staff'])
        self.course = Course.objects.create(
            name='Deprecated Endpoint Course',
            price=100,
            start_date=date.today() + timedelta(days=1),
            start_time=time(hour=10, minute=0),
            repeat_pattern='once',
            status='draft',
            teacher=self.teacher_a,
        )
        self.class_instance = Class.objects.create(
            course=self.course,
            date=self.course.start_date,
            start_time=self.course.start_time,
            duration_minutes=60,
            is_active=True,
        )
        self.extra_class = Class.objects.create(
            course=self.course,
            date=self.course.start_date + timedelta(days=7),
            start_time=self.course.start_time,
            duration_minutes=60,
            is_active=True,
        )
        self.other_course = Course.objects.create(
            name='Other Teacher Course',
            price=120,
            start_date=date.today() + timedelta(days=2),
            start_time=time(hour=11, minute=0),
            repeat_pattern='once',
            status='draft',
            teacher=self.teacher_b,
        )
        self.other_class = Class.objects.create(
            course=self.other_course,
            date=self.other_course.start_date,
            start_time=self.other_course.start_time,
            duration_minutes=60,
            is_active=True,
        )
        self.student = Student.objects.create(
            first_name='Candidate',
            last_name='Student',
            contact_email='changjiang1124+candidate@student.test',
            contact_phone='0401909775',
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='staff',
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.other_course,
            status='confirmed',
            source_channel='staff',
        )

    def test_class_add_students_endpoint_returns_gone(self):
        self.client.force_login(self.admin)
        url = reverse('academics:class_add_students', kwargs={'pk': self.class_instance.pk})
        response = self.client.post(
            url,
            data='{"student_ids":[1]}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 410)
        payload = response.json()
        self.assertFalse(payload['success'])
        self.assertTrue(payload.get('deprecated'))

    def test_makeup_candidates_returns_course_rich_labels(self):
        self.client.force_login(self.admin)
        url = reverse('academics:class_makeup_candidates', kwargs={'pk': self.class_instance.pk})
        response = self.client.get(
            url,
            data={
                'student_id': self.student.id,
                'initiated_from': 'target',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertTrue(payload['candidates'])
        labels = [item['label'] for item in payload['candidates']]
        self.assertTrue(any(self.course.name in label for label in labels))

    def test_teacher_candidates_are_limited_to_owned_classes(self):
        self.client.force_login(self.teacher_a)
        url = reverse('academics:class_makeup_candidates', kwargs={'pk': self.class_instance.pk})
        response = self.client.get(
            url,
            data={
                'student_id': self.student.id,
                'initiated_from': 'target',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        labels = [item['label'] for item in payload['candidates']]
        self.assertTrue(any(self.course.name in label for label in labels))
        self.assertTrue(all(self.other_course.name not in label for label in labels))

    def test_source_mode_candidates_include_global_upcoming_classes(self):
        self.client.force_login(self.admin)
        url = reverse('academics:class_makeup_candidates', kwargs={'pk': self.class_instance.pk})
        response = self.client.get(
            url,
            data={
                'student_id': self.student.id,
                'initiated_from': 'source',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        labels = [item['label'] for item in payload['candidates']]
        self.assertTrue(any(self.other_course.name in label for label in labels))
