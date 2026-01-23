from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import TeacherAttendance
from core.services.staff_timesheet_service import StaffTimesheetService
from facilities.models import Facility


class StaffTimesheetServiceTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.teacher = self.User.objects.create_user(
            username='timesheet-teacher',
            password='Teacher123!',
            first_name='Timesheet',
            last_name='Tester',
            email='changjiang1124+timesheet@gmail.com',
            role='teacher',
            is_active=True
        )

        self.facility = Facility.objects.create(
            name='Timesheet Studio',
            address='Timesheet Road',
            latitude=Decimal('0.0'),
            longitude=Decimal('0.0'),
            attendance_radius=20000000,
            is_active=True
        )

    def _create_attendance(self, clock_type):
        return TeacherAttendance.objects.create(
            teacher=self.teacher,
            clock_type=clock_type,
            facility=self.facility,
            latitude=Decimal('0.0'),
            longitude=Decimal('0.0'),
            distance_from_facility=0,
            location_verified=True,
            ip_address='127.0.0.1',
            user_agent='tests'
        )

    def test_overview_handles_incomplete_sessions(self):
        attendance = self._create_attendance('clock_in')
        attendance_date = timezone.localdate(attendance.timestamp)

        overview = StaffTimesheetService.get_all_staff_timesheet_data(
            self.User.objects.filter(id=self.teacher.id),
            start_date=attendance_date,
            end_date=attendance_date
        )

        self.assertEqual(overview['overall_summary']['total_hours'], 0)
        self.assertEqual(overview['overall_summary']['total_sessions'], 1)
        self.assertEqual(overview['staff_summaries'][0]['total_hours'], 0)

    def test_pairs_across_midnight(self):
        clock_in = self._create_attendance('clock_in')
        clock_out = self._create_attendance('clock_out')

        tz = timezone.get_current_timezone()
        day_one = timezone.now().date()
        clock_in_time = timezone.make_aware(
            datetime.combine(day_one, time(23, 0)), tz
        )
        clock_out_time = clock_in_time + timedelta(hours=1)

        TeacherAttendance.objects.filter(id=clock_in.id).update(timestamp=clock_in_time)
        TeacherAttendance.objects.filter(id=clock_out.id).update(timestamp=clock_out_time)

        clock_in.refresh_from_db()
        clock_out.refresh_from_db()

        timesheet_data = StaffTimesheetService.get_staff_timesheet_data(
            self.teacher, day_one, clock_out_time.date()
        )
        paired_records = timesheet_data['paired_records']

        self.assertEqual(len(paired_records), 1)
        record = paired_records[0]
        self.assertTrue(record['is_complete'])
        self.assertEqual(record['date'], day_one)
        self.assertAlmostEqual(record['duration_hours'], 1.0, places=2)
