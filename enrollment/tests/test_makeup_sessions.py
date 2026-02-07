from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Staff
from academics.models import Class, Course
from enrollment.models import Attendance, Enrollment
from enrollment.services import ClassAttendanceService, MakeupSessionService
from students.models import Student


class MakeupSessionServiceTests(TestCase):
    def setUp(self):
        self.admin = Staff.objects.create_user(
            username='makeup-admin',
            password='pass',
            is_staff=True,
            is_superuser=True,
            role='admin'
        )
        self.student = Student.objects.create(
            first_name='Makeup',
            last_name='Student',
            contact_email='changjiang1124+makeup@student.test',
            contact_phone='0401909771',
        )
        self.course = Course.objects.create(
            name='Makeup Course',
            price=100,
            early_bird_price=90,
            early_bird_deadline=date.today() - timedelta(days=1),
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=14),
            start_time=time(hour=16, minute=0),
            repeat_pattern='weekly',
            repeat_weekday=(date.today() + timedelta(days=1)).weekday(),
            status='published',
        )
        self.source_class = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=1),
            start_time=time(hour=16, minute=0),
            duration_minutes=120,
            is_active=True,
        )
        self.target_class = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=8),
            start_time=time(hour=16, minute=0),
            duration_minutes=120,
            is_active=True,
        )
        self.cross_course = Course.objects.create(
            name='Cross Course',
            price=110,
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=15),
            start_time=time(hour=18, minute=0),
            repeat_pattern='weekly',
            repeat_weekday=(date.today() + timedelta(days=2)).weekday(),
            status='published',
        )
        self.cross_target_class = Class.objects.create(
            course=self.cross_course,
            date=date.today() + timedelta(days=9),
            start_time=time(hour=18, minute=0),
            duration_minutes=120,
            is_active=True,
        )
        self.global_target_course = Course.objects.create(
            name='Global Target Course',
            price=130,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=30),
            start_time=time(hour=11, minute=0),
            repeat_pattern='weekly',
            repeat_weekday=(date.today() + timedelta(days=3)).weekday(),
            status='published',
        )
        self.global_future_class = Class.objects.create(
            course=self.global_target_course,
            date=date.today() + timedelta(days=3),
            start_time=time(hour=11, minute=0),
            duration_minutes=90,
            is_active=True,
        )
        self.global_past_class = Class.objects.create(
            course=self.global_target_course,
            date=date.today() - timedelta(days=3),
            start_time=time(hour=11, minute=0),
            duration_minutes=90,
            is_active=True,
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='staff',
        )

    def test_schedule_makeup_creates_records_and_audit_link(self):
        result = MakeupSessionService.schedule_session(
            student=self.student,
            source_class=self.source_class,
            target_class=self.target_class,
            initiated_from='source',
            reason_type='student_request',
            notes='Family event',
            actor=self.admin,
        )

        makeup = result['makeup_session']
        self.assertEqual(makeup.course_id, self.course.id)
        self.assertEqual(makeup.status, 'scheduled')
        self.assertEqual(makeup.snapshot_json['source_class']['id'], self.source_class.id)
        self.assertEqual(makeup.snapshot_json['target_class']['id'], self.target_class.id)

        source_attendance = Attendance.objects.get(
            student=self.student,
            class_instance=self.source_class
        )
        target_attendance = Attendance.objects.get(
            student=self.student,
            class_instance=self.target_class
        )

        self.assertEqual(source_attendance.status, 'unmarked')
        self.assertEqual(target_attendance.status, 'unmarked')

    def test_schedule_makeup_marks_absent_for_past_source_class(self):
        past_source_class = Class.objects.create(
            course=self.course,
            date=date.today() - timedelta(days=1),
            start_time=time(hour=15, minute=0),
            duration_minutes=120,
            is_active=True,
        )

        MakeupSessionService.schedule_session(
            student=self.student,
            source_class=past_source_class,
            target_class=self.target_class,
            initiated_from='source',
            reason_type='student_request',
            actor=self.admin,
        )

        source_attendance = Attendance.objects.get(
            student=self.student,
            class_instance=past_source_class
        )
        self.assertEqual(source_attendance.status, 'absent')

    def test_target_sync_keeps_makeup_attendance_for_non_enrolled_student(self):
        visitor = Student.objects.create(
            first_name='Visitor',
            last_name='Student',
            contact_email='changjiang1124+visitor@student.test',
            contact_phone='0401909772',
        )
        Attendance.objects.create(
            student=visitor,
            class_instance=self.source_class,
            status='absent',
            attendance_time=self.source_class.get_class_datetime(),
        )

        MakeupSessionService.schedule_session(
            student=visitor,
            source_class=self.source_class,
            target_class=self.target_class,
            initiated_from='source',
            reason_type='admin_adjustment',
            actor=self.admin,
        )

        Attendance.objects.filter(
            student=visitor,
            class_instance=self.target_class
        ).delete()

        result = ClassAttendanceService.sync_class_attendance(self.target_class)
        self.assertEqual(result['status'], 'success')
        self.assertTrue(
            Attendance.objects.filter(
                student=visitor,
                class_instance=self.target_class
            ).exists()
        )

    def test_schedule_makeup_rejects_same_class(self):
        with self.assertRaises(ValidationError):
            MakeupSessionService.schedule_session(
                student=self.student,
                source_class=self.source_class,
                target_class=self.source_class,
                initiated_from='source',
                reason_type='student_request',
                actor=self.admin,
            )

    def test_schedule_makeup_allows_cross_course_target(self):
        result = MakeupSessionService.schedule_session(
            student=self.student,
            source_class=self.source_class,
            target_class=self.cross_target_class,
            initiated_from='source',
            reason_type='admin_adjustment',
            actor=self.admin,
        )

        makeup = result['makeup_session']
        self.assertEqual(makeup.course_id, self.source_class.course_id)
        self.assertEqual(makeup.target_class_id, self.cross_target_class.id)

    def test_schedule_makeup_rejects_inactive_target(self):
        inactive_target = Class.objects.create(
            course=self.course,
            date=date.today() + timedelta(days=10),
            start_time=time(hour=19, minute=0),
            duration_minutes=120,
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            MakeupSessionService.schedule_session(
                student=self.student,
                source_class=self.source_class,
                target_class=inactive_target,
                initiated_from='source',
                reason_type='student_request',
                actor=self.admin,
            )

    def test_schedule_makeup_rejects_past_target(self):
        past_target = Class.objects.create(
            course=self.course,
            date=date.today() - timedelta(days=1),
            start_time=time(hour=9, minute=0),
            duration_minutes=120,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            MakeupSessionService.schedule_session(
                student=self.student,
                source_class=self.source_class,
                target_class=past_target,
                initiated_from='source',
                reason_type='student_request',
                actor=self.admin,
            )

    def test_sync_status_from_target_attendance_marks_completed(self):
        result = MakeupSessionService.schedule_session(
            student=self.student,
            source_class=self.source_class,
            target_class=self.target_class,
            initiated_from='source',
            reason_type='student_request',
            actor=self.admin,
        )
        makeup = result['makeup_session']

        updated_count = MakeupSessionService.sync_status_from_target_attendance(
            student=self.student,
            target_class=self.target_class,
            attendance_status='present',
            actor=self.admin,
        )

        self.assertEqual(updated_count, 1)
        makeup.refresh_from_db()
        self.assertEqual(makeup.status, 'completed')

    def test_sync_status_from_target_attendance_marks_no_show(self):
        result = MakeupSessionService.schedule_session(
            student=self.student,
            source_class=self.source_class,
            target_class=self.target_class,
            initiated_from='source',
            reason_type='student_request',
            actor=self.admin,
        )
        makeup = result['makeup_session']

        updated_count = MakeupSessionService.sync_status_from_target_attendance(
            student=self.student,
            target_class=self.target_class,
            attendance_status='absent',
            actor=self.admin,
        )

        self.assertEqual(updated_count, 1)
        makeup.refresh_from_db()
        self.assertEqual(makeup.status, 'no_show')

    def test_candidate_classes_include_course_name(self):
        Enrollment.objects.create(
            student=self.student,
            course=self.cross_course,
            status='pending',
            source_channel='staff',
        )
        payload = MakeupSessionService.get_candidate_classes(
            student=self.student,
            current_class=self.source_class,
            initiated_from='target',
        )

        labels = [item['label'] for item in payload['candidates']]
        self.assertTrue(any(self.course.name in label for label in labels))
        self.assertTrue(any(self.cross_course.name in label for label in labels))

    def test_source_mode_candidates_include_global_upcoming_and_exclude_past(self):
        payload = MakeupSessionService.get_candidate_classes(
            student=self.student,
            current_class=self.source_class,
            initiated_from='source',
        )

        candidate_ids = {item['id'] for item in payload['candidates']}
        self.assertIn(self.global_future_class.id, candidate_ids)
        self.assertNotIn(self.global_past_class.id, candidate_ids)
