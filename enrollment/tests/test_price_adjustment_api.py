from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time, timedelta
from decimal import Decimal
from accounts.models import Staff
from students.models import Student
from academics.models import Course, Class
from enrollment.models import Enrollment


class PriceAdjustmentAPITests(TestCase):
    def setUp(self):
        Staff.objects.create_user(username='admin2', password='pass', role='admin', is_staff=True, is_superuser=True)
        Staff.objects.create_user(username='teacher', password='pass', is_staff=False)
        self.client = Client()
        self.client.login(username='admin2', password='pass')
        self.secure_client = Client(enforce_csrf_checks=True)
        self.secure_client.login(username='admin2', password='pass')

        self.student = Student.objects.create(first_name='Price', last_name='Tester', contact_email='changjiang1124+2@gmail.com', contact_phone='0401909771')
        self.course = Course.objects.create(
            name='Price Course',
            price=Decimal('150.00'),
            early_bird_price=Decimal('120.00'),
            early_bird_deadline=date.today() - timedelta(days=1),
            start_date=date.today() + timedelta(days=10),
            start_time=time(hour=9, minute=0),
            repeat_pattern='once',
            status='published'
        )
        self.class_instance = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=5),
            start_time=time(hour=10, minute=0),
            duration_minutes=60,
            is_active=True
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='website',
            course_fee=Decimal('120.00'),
            is_early_bird=True,
            original_price=Decimal('150.00')
        )

    def test_check_price_adjustment_requires_staff(self):
        client_nonstaff = Client()
        client_nonstaff.login(username='teacher', password='pass')
        url = reverse('enrollment:check_price_adjustment_api', args=[self.enrollment.id])
        resp = client_nonstaff.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_apply_price_adjustment_csrf_enforced(self):
        url = reverse('enrollment:apply_price_adjustment_api', args=[self.enrollment.id])

        resp_no_csrf = self.secure_client.post(url, data={"adjustment_type": "apply_regular"}, content_type='application/json')
        self.assertEqual(resp_no_csrf.status_code, 403)

        # Get CSRF token from a page that sets it
        self.secure_client.get(reverse('enrollment:public_enrollment'), follow=True, secure=True)
        csrf = self.secure_client.cookies['csrftoken'].value

        resp_with_csrf = self.secure_client.post(
            url,
            data={"adjustment_type": "apply_regular"},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_REFERER='https://testserver/enrollment/'
        , secure=True)
        self.assertEqual(resp_with_csrf.status_code, 200)

    def test_apply_regular_updates_enrollment(self):
        url = reverse('enrollment:apply_price_adjustment_api', args=[self.enrollment.id])
        self.secure_client.get(reverse('enrollment:public_enrollment'), follow=True, secure=True)
        csrf = self.secure_client.cookies['csrftoken'].value
        resp = self.secure_client.post(
            url,
            data={"adjustment_type": "apply_regular"},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_REFERER='https://testserver/enrollment/'
        , secure=True)
        self.assertEqual(resp.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.course_fee, self.course.price)
        self.assertFalse(self.enrollment.is_early_bird)

    def test_keep_early_bird_updates_enrollment(self):
        url = reverse('enrollment:apply_price_adjustment_api', args=[self.enrollment.id])
        self.secure_client.get(reverse('enrollment:public_enrollment'), follow=True, secure=True)
        csrf = self.secure_client.cookies['csrftoken'].value
        resp = self.secure_client.post(
            url,
            data={"adjustment_type": "keep_early_bird"},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_REFERER='https://testserver/enrollment/'
        , secure=True)
        self.assertEqual(resp.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.course_fee, self.course.early_bird_price)
        self.assertTrue(self.enrollment.is_early_bird)
