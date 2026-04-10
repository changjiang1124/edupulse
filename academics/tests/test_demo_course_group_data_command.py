from datetime import time, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Staff
from academics.management.commands.create_course_group_demo_data import Command
from academics.models import Course, CourseGroup
from academics.services import CourseGroupCreationService
from facilities.models import Classroom, Facility


class CreateCourseGroupDemoDataCommandTests(TestCase):
    @override_settings(DEBUG=False)
    def test_command_requires_debug_or_force(self):
        with self.assertRaisesMessage(CommandError, 'create_course_group_demo_data only runs when DEBUG=True'):
            call_command('create_course_group_demo_data')

    @override_settings(DEBUG=True)
    def test_command_creates_non_login_demo_teachers_and_purges_stale_children(self):
        first_run_output = StringIO()
        second_run_output = StringIO()

        call_command('create_course_group_demo_data', stdout=first_run_output)

        teacher = Staff.objects.get(username='demo-course-teacher-anna')
        self.assertFalse(teacher.has_usable_password())
        self.assertFalse(teacher.is_active_staff)

        group = CourseGroup.objects.get(slug='demo-early-years-art-lab')
        facility = Facility.objects.get(name='Demo Campus North')
        classroom = Classroom.objects.get(facility=facility, name='Studio A')

        stale_course = Course(group=group)
        CourseGroupCreationService.apply_group_snapshot(stale_course, group)
        stale_course.start_date = timezone.localdate() + timedelta(days=180)
        stale_course.end_date = timezone.localdate() + timedelta(days=250)
        stale_course.repeat_pattern = 'weekly'
        stale_course.repeat_weekday = 4
        stale_course.start_time = time(20, 0)
        stale_course.duration_minutes = 120
        stale_course.status = 'draft'
        stale_course.bookable_state = 'closed'
        stale_course.is_online_bookable = False
        stale_course.vacancy = 4
        stale_course.teacher = teacher
        stale_course.facility = facility
        stale_course.classroom = classroom
        stale_course.save()

        self.assertTrue(Course.objects.filter(pk=stale_course.pk).exists())

        call_command('create_course_group_demo_data', stdout=second_run_output)

        self.assertFalse(Course.objects.filter(pk=stale_course.pk).exists())
        self.assertIn('Removed ', second_run_output.getvalue())
        self.assertIn('stale demo child course(s).', second_run_output.getvalue())

    @override_settings(DEBUG=True)
    def test_command_helper_uses_stable_child_keys(self):
        today = timezone.localdate()
        child_definition = {
            'start_date': today,
            'end_date': today + timedelta(days=70),
            'repeat_weekday': 2,
            'start_time': time(16, 0),
        }
        command = Command()

        self.assertEqual(
            command._get_child_definition_key(child_definition),
            (today, today + timedelta(days=70), 2, time(16, 0)),
        )
