from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academics.models import Class, Course
from core.models import TeacherAttendance
from facilities.models import Classroom, Facility


@override_settings(SECURE_SSL_REDIRECT=False)
class StaffAttendanceManualEntryViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='admin-user',
            password='Admin123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True,
            is_active_staff=True,
        )
        self.teacher = user_model.objects.create_user(
            username='manual-teacher',
            password='Teacher123!',
            first_name='Manual',
            last_name='Teacher',
            role='teacher',
            is_active=True,
            is_active_staff=True,
        )
        self.office_admin = user_model.objects.create_user(
            username='office-admin',
            password='Office123!',
            first_name='Office',
            last_name='Admin',
            role='admin',
            is_active=True,
            is_active_staff=True,
        )

        self.facility = Facility.objects.create(
            name='Manual Entry Studio',
            address='1 Testing Street',
            latitude=Decimal('0.0'),
            longitude=Decimal('0.0'),
            attendance_radius=500,
            is_active=True,
        )
        self.classroom = Classroom.objects.create(
            facility=self.facility,
            name='Room One',
            capacity=20,
            is_active=True,
        )

        start_time = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
        today = timezone.localdate()
        self.course = Course.objects.create(
            name='Manual Attendance Course',
            short_description='Manual attendance coverage',
            price=Decimal('120.00'),
            course_type='group',
            category='term_courses',
            status='published',
            repeat_pattern='once',
            start_date=today,
            start_time=start_time,
            duration_minutes=90,
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
            duration_minutes=90,
            teacher=self.teacher,
            facility=self.facility,
            classroom=self.classroom,
            is_active=True,
        )

        self.client = Client()

    def _full_session_payload(self, start, end, **overrides):
        payload = {
            'entry_mode': 'full_session',
            'work_date': timezone.localtime(start).strftime('%Y-%m-%d'),
            'session_start_time': timezone.localtime(start).strftime('%H:%M'),
            'session_end_time': timezone.localtime(end).strftime('%H:%M'),
        }
        payload.update(overrides)
        return payload

    def _create_manual_session(self, start, end):
        clock_in = TeacherAttendance.objects.create(
            teacher=self.teacher,
            clock_type='clock_in',
            source='manual',
            timestamp=start,
            created_by=self.admin,
            updated_by=self.admin,
        )
        clock_out = TeacherAttendance.objects.create(
            teacher=self.teacher,
            clock_type='clock_out',
            source='manual',
            timestamp=end,
            created_by=self.admin,
            updated_by=self.admin,
        )
        return clock_in, clock_out

    def test_admin_can_view_manual_entry_page(self):
        self.client.login(username='admin-user', password='Admin123!')

        response = self.client.get(
            reverse('accounts:staff_attendance_manual_entry', args=[self.teacher.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Timesheet Entry')
        self.assertContains(response, 'only the work date and time are required')

    def test_admin_can_use_manual_entry_for_non_teacher_staff(self):
        self.client.login(username='admin-user', password='Admin123!')

        response = self.client.get(
            reverse('accounts:staff_attendance_manual_entry', args=[self.office_admin.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Office Admin')

    def test_admin_can_create_full_session_with_only_date_and_time(self):
        self.client.login(username='admin-user', password='Admin123!')

        start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) - timedelta(hours=3)
        end = start + timedelta(hours=2)

        response = self.client.post(
            reverse('accounts:staff_attendance_manual_entry', args=[self.teacher.pk]),
            data=self._full_session_payload(start, end),
        )

        self.assertEqual(response.status_code, 302)

        records = list(
            TeacherAttendance.objects.filter(teacher=self.teacher).order_by('timestamp')
        )
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].clock_type, 'clock_in')
        self.assertEqual(records[1].clock_type, 'clock_out')
        self.assertEqual(records[0].source, 'manual')
        self.assertIsNone(records[0].facility)
        self.assertEqual(records[0].classes.count(), 0)
        self.assertTrue(records[0].manual_reason.startswith('Manual timesheet entry created by'))
        self.assertFalse(records[0].location_verified)
        self.assertIsNone(records[0].latitude)
        self.assertIsNone(records[0].ip_address)

    def test_admin_can_edit_existing_full_session(self):
        self.client.login(username='admin-user', password='Admin123!')

        start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) - timedelta(hours=5)
        end = start + timedelta(hours=2)
        clock_in, clock_out = self._create_manual_session(start, end)

        updated_start = start + timedelta(minutes=30)
        updated_end = end + timedelta(minutes=45)
        payload = self._full_session_payload(
            updated_start,
            updated_end,
            facility=str(self.facility.pk),
            classes=[str(self.class_instance.pk)],
        )

        response = self.client.post(
            f"{reverse('accounts:staff_attendance_manual_edit', args=[self.teacher.pk, clock_in.pk])}?clock_out={clock_out.pk}",
            data=payload,
        )

        self.assertEqual(response.status_code, 302)

        clock_in.refresh_from_db()
        clock_out.refresh_from_db()
        self.assertEqual(timezone.localtime(clock_in.timestamp), updated_start)
        self.assertEqual(timezone.localtime(clock_out.timestamp), updated_end)
        self.assertEqual(clock_in.facility, self.facility)
        self.assertEqual(clock_in.classes.first(), self.class_instance)
        self.assertTrue(clock_in.manual_reason.startswith('Manual timesheet entry updated by'))

    def test_admin_can_delete_existing_timesheet_entry(self):
        self.client.login(username='admin-user', password='Admin123!')

        start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) - timedelta(hours=4)
        end = start + timedelta(hours=2)
        clock_in, clock_out = self._create_manual_session(start, end)

        response = self.client.post(
            f"{reverse('accounts:staff_attendance_manual_edit', args=[self.teacher.pk, clock_in.pk])}?clock_out={clock_out.pk}",
            data={
                'form_action': 'delete',
                'clock_out': str(clock_out.pk),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(TeacherAttendance.objects.filter(pk=clock_in.pk).exists())
        self.assertFalse(TeacherAttendance.objects.filter(pk=clock_out.pk).exists())

    def test_overlapping_session_is_rejected(self):
        self.client.login(username='admin-user', password='Admin123!')

        start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) - timedelta(hours=6)
        end = start + timedelta(hours=2)
        self._create_manual_session(start, end)

        overlapping_start = start + timedelta(hours=1)
        overlapping_end = end + timedelta(hours=1)
        response = self.client.post(
            reverse('accounts:staff_attendance_manual_entry', args=[self.teacher.pk]),
            data=self._full_session_payload(overlapping_start, overlapping_end),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'overlaps an existing attendance entry')
        self.assertEqual(TeacherAttendance.objects.filter(teacher=self.teacher).count(), 2)

    def test_teacher_cannot_access_manual_entry_page(self):
        self.client.login(username='manual-teacher', password='Teacher123!')

        response = self.client.get(
            reverse('accounts:staff_attendance_manual_entry', args=[self.teacher.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard'))

    def test_staff_detail_shows_edit_link_for_existing_timesheet(self):
        self.client.login(username='admin-user', password='Admin123!')

        start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) - timedelta(hours=5)
        end = start + timedelta(hours=2)
        clock_in, clock_out = self._create_manual_session(start, end)

        response = self.client.get(
            reverse('accounts:staff_detail', args=[self.teacher.pk]),
            {
                'timesheet_start': timezone.localtime(start).strftime('%Y-%m-%d'),
                'timesheet_end': timezone.localtime(end).strftime('%Y-%m-%d'),
            },
        )

        edit_url = (
            f"{reverse('accounts:staff_attendance_manual_edit', args=[self.teacher.pk, clock_in.pk])}"
            f"?clock_out={clock_out.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, edit_url)

    def test_timesheet_overview_supports_staff_filter_and_edit_links(self):
        self.client.login(username='admin-user', password='Admin123!')

        start = timezone.localtime(timezone.now()).replace(second=0, microsecond=0) - timedelta(hours=5)
        end = start + timedelta(hours=2)
        clock_in, clock_out = self._create_manual_session(start, end)

        response = self.client.get(
            reverse('accounts:staff_timesheet_overview'),
            {
                'staff': str(self.teacher.pk),
                'start_date': timezone.localtime(start).strftime('%Y-%m-%d'),
                'end_date': timezone.localtime(end).strftime('%Y-%m-%d'),
            },
        )

        edit_url = (
            f"{reverse('accounts:staff_attendance_manual_edit', args=[self.teacher.pk, clock_in.pk])}"
            f"?clock_out={clock_out.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Timesheet')
        self.assertContains(response, 'name="staff"')
        self.assertContains(response, 'Manual Teacher Entries')
        self.assertContains(response, edit_url)
