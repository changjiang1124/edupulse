from django.test import TestCase
from django.utils import timezone
from datetime import date, time, timedelta
from accounts.models import Staff
from students.models import Student
from academics.models import Course, Class
from enrollment.models import Enrollment, Attendance


class AttendanceAutomationTests(TestCase):
    def setUp(self):
        Staff.objects.create_user(username='admin', password='pass', is_staff=True, is_superuser=True)
        self.student = Student.objects.create(first_name='Test', last_name='Student', contact_email='changjiang1124@gmail.com', contact_phone='0401909771')
        self.course = Course.objects.create(
            name='Test Course',
            price=100,
            early_bird_price=80,
            early_bird_deadline=date.today() + timedelta(days=7),
            start_date=date.today() + timedelta(days=10),
            start_time=time(hour=9, minute=0),
            repeat_pattern='once',
            status='published'
        )
        self.class_active_1 = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=1),
            start_time=time(hour=10, minute=0),
            duration_minutes=60,
            is_active=True
        )
        self.class_active_2 = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=2),
            start_time=time(hour=10, minute=0),
            duration_minutes=60,
            is_active=True
        )
        self.class_inactive = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=3),
            start_time=time(hour=10, minute=0),
            duration_minutes=60,
            is_active=False
        )

    def test_attendance_created_on_confirm_enrollment(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='pending',
            source_channel='website'
        )

        enrollment.status = 'confirmed'
        enrollment.save()

        a1 = Attendance.objects.filter(student=self.student, class_instance=self.class_active_1).count()
        a2 = Attendance.objects.filter(student=self.student, class_instance=self.class_active_2).count()
        a3 = Attendance.objects.filter(student=self.student, class_instance=self.class_inactive).count()

        self.assertEqual(a1, 1)
        self.assertEqual(a2, 1)
        self.assertEqual(a3, 0)

        rec = Attendance.objects.get(student=self.student, class_instance=self.class_active_1)
        self.assertEqual(rec.status, 'absent')

    def test_attendance_created_on_new_active_class(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='website'
        )

        new_class = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=4),
            start_time=time(hour=11, minute=0),
            duration_minutes=60,
            is_active=True
        )

        exists = Attendance.objects.filter(student=self.student, class_instance=new_class).exists()
        self.assertTrue(exists)
