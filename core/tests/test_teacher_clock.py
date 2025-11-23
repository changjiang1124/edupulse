from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import json

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
        url = reverse('core:teacher_clock')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_location_verify_and_clock_submit(self):
        verify_url = reverse('core:teacher_location_verify')
        payload = {'latitude': 0.0, 'longitude': 0.0}
        resp = self.client.post(verify_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('location_verified'))
        self.assertTrue(data.get('has_classes'))
        facility_id = data['facility']['id']

        submit_url = reverse('core:teacher_clock_submit')
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