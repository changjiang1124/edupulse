from django.test import TestCase
from datetime import date, time, timedelta
from students.models import Student
from academics.models import Course, Class
from enrollment.models import Enrollment, Attendance
from enrollment.services import AttendanceSyncService, EnrollmentAttendanceService


class AttendanceSyncServiceTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(first_name='Sync', last_name='User', contact_email='changjiang1124+1@gmail.com', contact_phone='0401909771')
        self.course = Course.objects.create(
            name='Sync Course',
            price=120,
            early_bird_price=90,
            early_bird_deadline=date.today() - timedelta(days=1),
            start_date=date.today() + timedelta(days=10),
            start_time=time(hour=9, minute=0),
            repeat_pattern='once',
            status='published'
        )
        self.class_active = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=1),
            start_time=time(hour=9, minute=0),
            duration_minutes=60,
            is_active=True
        )
        self.class_inactive = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=2),
            start_time=time(hour=9, minute=0),
            duration_minutes=60,
            is_active=False
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='website'
        )

    def test_course_sync_creates_and_removes_attendance(self):
        stray = Attendance.objects.create(student=self.student, class_instance=self.class_inactive, status='present')

        result = AttendanceSyncService.sync_all_course_attendance(self.course)

        created_active = Attendance.objects.filter(student=self.student, class_instance=self.class_active).count()
        exists_inactive = Attendance.objects.filter(pk=stray.pk).exists()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(created_active, 1)
        self.assertFalse(exists_inactive)

    def test_enrollment_sync_respects_active_until(self):
        future_class = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=3),
            start_time=time(hour=9, minute=0),
            duration_minutes=60,
            is_active=True
        )
        exists_before = Attendance.objects.filter(student=self.student, class_instance=future_class).exists()
        self.assertTrue(exists_before)

        self.enrollment.active_until = future_class.get_class_datetime()
        self.enrollment.save(update_fields=['active_until'])

        result = EnrollmentAttendanceService.sync_enrollment_attendance(self.enrollment)
        exists_after = Attendance.objects.filter(student=self.student, class_instance=future_class).exists()
        exists_active = Attendance.objects.filter(student=self.student, class_instance=self.class_active).exists()

        self.assertEqual(result['status'], 'success')
        self.assertTrue(exists_active)
        self.assertFalse(exists_after)
