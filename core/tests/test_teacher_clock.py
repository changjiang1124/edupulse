import base64
import json
from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from uuid import uuid4

from core.models import TeacherAttendance
from core.services.qr_service import QRCodeService


@override_settings(SECURE_SSL_REDIRECT=False)
class TeacherClockTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username='teacher',
            password='Teacher123!',
            first_name='Test',
            last_name='Teacher',
            email='changjiang1124+teacher@gmail.com',
            role='teacher',
            is_active=True
        )

        from facilities.models import Facility, Classroom
        self.facility = Facility.objects.create(
            name='Test Studio',
            address='Anywhere for testing',
            latitude=Decimal('0.0'),
            longitude=Decimal('0.0'),
            attendance_radius=20000000,
            is_active=True
        )
        self.classroom = Classroom.objects.create(
            facility=self.facility,
            name='Room A',
            capacity=20,
            is_active=True
        )

        from academics.models import Course, Class
        today = timezone.now().date()
        start_time = timezone.now().time().replace(second=0, microsecond=0)
        self.course = Course.objects.create(
            name='Clock Test Course',
            short_description='For teacher clock testing',
            price=Decimal('100.00'),
            course_type='group',
            category='term_courses',
            status='published',
            repeat_pattern='once',
            start_date=today,
            start_time=start_time,
            duration_minutes=60,
            vacancy=10,
            is_online_bookable=True,
            bookable_state='bookable',
            teacher=self.teacher,
            facility=self.facility,
            classroom=self.classroom,
        )
        self.class_instance = Class.objects.create(
            course=self.course,
            date=today,
            start_time=start_time,
            duration_minutes=60,
            teacher=self.teacher,
            facility=self.facility,
            classroom=self.classroom,
            is_active=True
        )

        self.client = Client()
        self.client.login(username='teacher', password='Teacher123!')

    def test_clock_page_access(self):
        url = reverse('clock')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_timesheet_page_access(self):
        resp = self.client.get(reverse('timesheet'))
        self.assertEqual(resp.status_code, 200)

    def _submit_clock(self, clock_type):
        submit_url = reverse('teacher_clock_submit')
        payload = {
            'clock_type': clock_type,
            'latitude': 0.0,
            'longitude': 0.0,
            'facility_id': self.facility.id,
            'class_ids': [self.class_instance.id],
            'notes': f'Test {clock_type}'
        }
        return self.client.post(
            submit_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

    def _build_qr_data(self, class_instance=None):
        issued_at = timezone.now()
        qr_data = {
            'facility_id': self.facility.id,
            'facility_name': self.facility.name,
            'class_id': class_instance.id if class_instance else None,
            'token': f'test-token-{uuid4().hex}',
            'expires_at': (issued_at + timedelta(minutes=60)).isoformat(),
            'generated_at': issued_at.isoformat(),
        }
        QRCodeService._store_qr_token(qr_data['token'], qr_data)
        return base64.urlsafe_b64encode(
            json.dumps(qr_data).encode('utf-8')
        ).decode('utf-8')

    def _submit_qr(self, clock_type, *, include_gps=True, classes=None, class_instance=None, client=None):
        payload = {
            'qr_data': self._build_qr_data(class_instance=class_instance),
            'clock_type': clock_type,
        }

        if include_gps:
            payload.update({
                'latitude': '0.0',
                'longitude': '0.0',
            })

        if classes:
            payload['classes'] = [str(class_id) for class_id in classes]

        qr_client = client or self.client
        return qr_client.post(
            reverse('teacher_qr_attendance'),
            data=payload,
            HTTP_ACCEPT='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def test_location_verify_and_clock_submit(self):
        verify_url = reverse('teacher_location_verify')
        payload = {'latitude': 0.0, 'longitude': 0.0}
        resp = self.client.post(verify_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('location_verified'))
        self.assertTrue(data.get('has_classes'))
        facility_id = data['facility']['id']

        submit_url = reverse('teacher_clock_submit')
        submit_payload = {
            'clock_type': 'clock_in',
            'latitude': 0.0,
            'longitude': 0.0,
            'facility_id': facility_id,
            'class_ids': [self.class_instance.id],
            'notes': 'Test clock in'
        }
        resp2 = self.client.post(submit_url, data=json.dumps(submit_payload), content_type='application/json')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertTrue(data2.get('success'))

        attendance = TeacherAttendance.objects.get(teacher=self.teacher, clock_type='clock_in')
        self.assertEqual(attendance.source, 'gps')
        self.assertEqual(attendance.created_by, self.teacher)
        self.assertEqual(attendance.updated_by, self.teacher)

    def test_clock_out_requires_active_clock_in(self):
        resp = self._submit_clock('clock_out')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('clock in', resp.json().get('error', '').lower())

    def test_double_clock_in_rejected(self):
        first = self._submit_clock('clock_in')
        self.assertEqual(first.status_code, 200)
        second = self._submit_clock('clock_in')
        self.assertEqual(second.status_code, 400)
        self.assertIn('already', second.json().get('error', '').lower())

    def test_clock_out_after_clock_in(self):
        first = self._submit_clock('clock_in')
        self.assertEqual(first.status_code, 200)
        second = self._submit_clock('clock_out')
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json().get('success'))

    def test_qr_clock_out_requires_active_clock_in(self):
        response = self._submit_qr('clock_out')

        self.assertEqual(response.status_code, 400)
        self.assertIn('clock in', response.json().get('message', '').lower())

    def test_qr_double_clock_in_rejected(self):
        first = self._submit_qr('clock_in')
        self.assertEqual(first.status_code, 200)

        second = self._submit_qr('clock_in')
        self.assertEqual(second.status_code, 400)
        self.assertIn('already', second.json().get('message', '').lower())

    def test_qr_invalid_clock_type_rejected(self):
        response = self._submit_qr('break_start')

        self.assertEqual(response.status_code, 400)
        self.assertIn('invalid clock type', response.json().get('message', '').lower())

    def test_qr_submission_only_attaches_current_teachers_classes(self):
        User = get_user_model()
        other_teacher = User.objects.create_user(
            username='other-teacher',
            password='Teacher123!',
            first_name='Other',
            last_name='Teacher',
            role='teacher',
            is_active=True,
            is_active_staff=True,
        )

        from academics.models import Course, Class
        other_course = Course.objects.create(
            name='Other Teacher Course',
            short_description='For QR clock testing',
            price=Decimal('100.00'),
            course_type='group',
            category='term_courses',
            status='published',
            repeat_pattern='once',
            start_date=timezone.localdate(),
            start_time=timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0),
            duration_minutes=60,
            vacancy=10,
            is_online_bookable=True,
            bookable_state='bookable',
            teacher=other_teacher,
            facility=self.facility,
            classroom=self.classroom,
        )
        other_class = Class.objects.create(
            course=other_course,
            date=timezone.localdate(),
            start_time=other_course.start_time,
            duration_minutes=60,
            teacher=other_teacher,
            facility=self.facility,
            classroom=self.classroom,
            is_active=True,
        )

        response = self._submit_qr(
            'clock_in',
            classes=[self.class_instance.id, other_class.id],
        )

        self.assertEqual(response.status_code, 200)
        attendance = TeacherAttendance.objects.get(teacher=self.teacher, clock_type='clock_in')
        self.assertQuerySetEqual(
            attendance.classes.order_by('id'),
            [self.class_instance],
            transform=lambda obj: obj,
        )

    def test_qr_submission_without_gps_is_not_location_verified(self):
        response = self._submit_qr(
            'clock_in',
            include_gps=False,
            class_instance=self.class_instance,
        )

        self.assertEqual(response.status_code, 200)

        attendance = TeacherAttendance.objects.get(teacher=self.teacher, clock_type='clock_in')
        self.assertEqual(attendance.source, 'qr')
        self.assertFalse(attendance.location_verified)
        self.assertIsNone(attendance.latitude)
        self.assertIsNone(attendance.longitude)
        self.assertIsNone(attendance.distance_from_facility)
        self.assertIn('gps not verified', attendance.notes.lower())
        self.assertEqual(attendance.classes.count(), 1)
        self.assertEqual(attendance.classes.first(), self.class_instance)

    def test_inactive_staff_json_endpoints_return_json_403(self):
        User = get_user_model()
        User.objects.create_user(
            username='inactive-teacher',
            password='Teacher123!',
            first_name='Inactive',
            last_name='Teacher',
            role='teacher',
            is_active=True,
            is_active_staff=False,
        )

        client = Client()
        client.login(username='inactive-teacher', password='Teacher123!')

        verify_response = client.post(
            reverse('teacher_location_verify'),
            data=json.dumps({'latitude': 0.0, 'longitude': 0.0}),
            content_type='application/json',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(verify_response.status_code, 403)
        self.assertEqual(verify_response.json()['error'], 'Access denied.')

        qr_response = self._submit_qr('clock_in', client=client)
        self.assertEqual(qr_response.status_code, 403)
        self.assertEqual(qr_response.json()['error'], 'Access denied.')
