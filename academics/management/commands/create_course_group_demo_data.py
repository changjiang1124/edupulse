from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Staff
from academics.models import Course, CourseGroup
from academics.services import CourseGroupCreationService
from facilities.models import Classroom, Facility


class Command(BaseCommand):
    help = 'Create reusable demo Course Group data for local UI review.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        teachers = self._get_demo_teachers()
        locations = self._get_demo_locations()

        demo_groups = [
            {
                'slug': 'demo-early-years-art-lab',
                'name': 'Demo Early Years Art Lab',
                'status': 'published',
                'short_description': 'A recurring term programme for younger students, with multiple weekday options.',
                'description': (
                    '<p><strong>Demo content:</strong> A colourful course group used to test the new Course Group UI.</p>'
                    '<p>It includes a mix of published, draft, fully booked, and expired child courses.</p>'
                ),
                'price': 780,
                'registration_fee': 140,
                'early_bird_price': 720,
                'early_bird_deadline': today + timedelta(days=10),
                'children': [
                    {
                        'start_date': today + timedelta(days=14),
                        'end_date': today + timedelta(days=84),
                        'repeat_weekday': 0,
                        'start_time': time(15, 30),
                        'duration_minutes': 120,
                        'status': 'published',
                        'bookable_state': 'bookable',
                        'is_online_bookable': True,
                        'vacancy': 12,
                        'teacher_index': 0,
                        'location_index': 0,
                        'enrollment_deadline': today + timedelta(days=12),
                    },
                    {
                        'start_date': today + timedelta(days=15),
                        'end_date': today + timedelta(days=85),
                        'repeat_weekday': 1,
                        'start_time': time(16, 0),
                        'duration_minutes': 120,
                        'status': 'published',
                        'bookable_state': 'fully_booked',
                        'is_online_bookable': True,
                        'vacancy': 10,
                        'teacher_index': 1,
                        'location_index': 1,
                        'enrollment_deadline': today + timedelta(days=13),
                    },
                    {
                        'start_date': today + timedelta(days=19),
                        'end_date': today + timedelta(days=89),
                        'repeat_weekday': 5,
                        'start_time': time(10, 0),
                        'duration_minutes': 150,
                        'status': 'draft',
                        'bookable_state': 'closed',
                        'is_online_bookable': False,
                        'vacancy': 8,
                        'teacher_index': 0,
                        'location_index': 0,
                        'enrollment_deadline': None,
                    },
                    {
                        'start_date': today - timedelta(days=84),
                        'end_date': today - timedelta(days=14),
                        'repeat_weekday': 2,
                        'start_time': time(15, 30),
                        'duration_minutes': 120,
                        'status': 'expired',
                        'bookable_state': 'closed',
                        'is_online_bookable': False,
                        'vacancy': 12,
                        'teacher_index': 1,
                        'location_index': 1,
                        'enrollment_deadline': today - timedelta(days=30),
                    },
                ],
            },
            {
                'slug': 'demo-teen-portfolio-studio',
                'name': 'Demo Teen Portfolio Studio',
                'status': 'published',
                'short_description': 'A portfolio-focused group for older students preparing for exhibitions and applications.',
                'description': (
                    '<p>This demo group is designed to show how a long-running template can hold multiple term instances.</p>'
                    '<p>Use it to review archived and active child rows together.</p>'
                ),
                'price': 980,
                'registration_fee': 160,
                'early_bird_price': 920,
                'early_bird_deadline': today + timedelta(days=7),
                'children': [
                    {
                        'start_date': today + timedelta(days=16),
                        'end_date': today + timedelta(days=93),
                        'repeat_weekday': 3,
                        'start_time': time(16, 30),
                        'duration_minutes': 150,
                        'status': 'published',
                        'bookable_state': 'bookable',
                        'is_online_bookable': True,
                        'vacancy': 10,
                        'teacher_index': 2,
                        'location_index': 1,
                        'enrollment_deadline': today + timedelta(days=14),
                    },
                    {
                        'start_date': today + timedelta(days=18),
                        'end_date': today + timedelta(days=95),
                        'repeat_weekday': 5,
                        'start_time': time(13, 0),
                        'duration_minutes': 180,
                        'status': 'published',
                        'bookable_state': 'bookable',
                        'is_online_bookable': True,
                        'vacancy': 6,
                        'teacher_index': 2,
                        'location_index': 0,
                        'enrollment_deadline': today + timedelta(days=16),
                    },
                    {
                        'start_date': today - timedelta(days=170),
                        'end_date': today - timedelta(days=90),
                        'repeat_weekday': 3,
                        'start_time': time(16, 30),
                        'duration_minutes': 150,
                        'status': 'archived',
                        'bookable_state': 'closed',
                        'is_online_bookable': False,
                        'vacancy': 10,
                        'teacher_index': 2,
                        'location_index': 1,
                        'enrollment_deadline': today - timedelta(days=120),
                    },
                ],
            },
            {
                'slug': 'demo-adult-oil-painting',
                'name': 'Demo Adult Oil Painting',
                'status': 'published',
                'short_description': 'An adult evening studio with two recurring weekly options.',
                'description': (
                    '<p>Built for layout review with longer descriptions, alternate times, and different room combinations.</p>'
                ),
                'price': 860,
                'registration_fee': None,
                'early_bird_price': 810,
                'early_bird_deadline': today + timedelta(days=12),
                'children': [
                    {
                        'start_date': today + timedelta(days=21),
                        'end_date': today + timedelta(days=91),
                        'repeat_weekday': 2,
                        'start_time': time(18, 30),
                        'duration_minutes': 150,
                        'status': 'published',
                        'bookable_state': 'bookable',
                        'is_online_bookable': True,
                        'vacancy': 14,
                        'teacher_index': 1,
                        'location_index': 0,
                        'enrollment_deadline': today + timedelta(days=18),
                    },
                    {
                        'start_date': today + timedelta(days=23),
                        'end_date': today + timedelta(days=93),
                        'repeat_weekday': 4,
                        'start_time': time(18, 30),
                        'duration_minutes': 150,
                        'status': 'published',
                        'bookable_state': 'bookable',
                        'is_online_bookable': True,
                        'vacancy': 14,
                        'teacher_index': 0,
                        'location_index': 1,
                        'enrollment_deadline': today + timedelta(days=20),
                    },
                ],
            },
            {
                'slug': 'demo-private-mentoring-series',
                'name': 'Demo Private Mentoring Series',
                'status': 'draft',
                'short_description': 'A draft-only group to test unpublished template states.',
                'description': (
                    '<p>This draft group helps verify hidden public links and empty-state handling before publication.</p>'
                ),
                'price': 1200,
                'registration_fee': None,
                'early_bird_price': None,
                'early_bird_deadline': None,
                'children': [
                    {
                        'start_date': today + timedelta(days=28),
                        'end_date': today + timedelta(days=98),
                        'repeat_weekday': 6,
                        'start_time': time(11, 0),
                        'duration_minutes': 90,
                        'status': 'draft',
                        'bookable_state': 'closed',
                        'is_online_bookable': False,
                        'vacancy': 1,
                        'teacher_index': 0,
                        'location_index': 0,
                        'enrollment_deadline': None,
                    },
                ],
            },
        ]

        group_count = 0
        child_count = 0

        for group_definition in demo_groups:
            group_defaults = {
                'name': group_definition['name'],
                'status': group_definition['status'],
                'short_description': group_definition['short_description'],
                'description': group_definition['description'],
                'category': 'term_courses',
                'course_type': 'group',
                'repeat_pattern': 'weekly',
                'price': group_definition['price'],
                'registration_fee': group_definition['registration_fee'],
                'early_bird_price': group_definition['early_bird_price'],
                'early_bird_deadline': group_definition['early_bird_deadline'],
            }
            group, _ = CourseGroup.objects.update_or_create(
                slug=group_definition['slug'],
                defaults=group_defaults,
            )
            group_count += 1

            for child_definition in group_definition['children']:
                course = Course.objects.filter(
                    group=group,
                    start_date=child_definition['start_date'],
                    start_time=child_definition['start_time'],
                ).first()
                if course is None:
                    course = Course(group=group)

                CourseGroupCreationService.apply_group_snapshot(course, group)
                course.start_date = child_definition['start_date']
                course.end_date = child_definition['end_date']
                course.repeat_pattern = 'weekly'
                course.repeat_weekday = child_definition['repeat_weekday']
                course.start_time = child_definition['start_time']
                course.duration_minutes = child_definition['duration_minutes']
                course.status = child_definition['status']
                course.bookable_state = child_definition['bookable_state']
                course.is_online_bookable = child_definition['is_online_bookable']
                course.vacancy = child_definition['vacancy']
                course.enrollment_deadline = child_definition['enrollment_deadline']
                course.teacher = teachers[child_definition['teacher_index'] % len(teachers)]
                facility, classroom = locations[child_definition['location_index'] % len(locations)]
                course.facility = facility
                course.classroom = classroom
                course.save()
                course.generate_classes(replace_existing=True)
                child_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created or updated {group_count} demo course groups and {child_count} child courses.'
        ))

    def _get_demo_teachers(self):
        teacher_specs = [
            ('demo-course-teacher-anna', 'Anna', 'Liu'),
            ('demo-course-teacher-marcus', 'Marcus', 'Tran'),
            ('demo-course-teacher-sofia', 'Sofia', 'Nguyen'),
        ]
        teachers = []
        for username, first_name, last_name in teacher_specs:
            teacher, created = Staff.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f'{username}@example.com',
                    'role': 'teacher',
                    'is_active_staff': True,
                },
            )
            if created:
                teacher.set_password('DemoTeacher123!')
                teacher.save()
            teachers.append(teacher)
        return teachers

    def _get_demo_locations(self):
        facility_specs = [
            ('Demo Campus North', '100 Demo Street, Perth WA'),
            ('Demo Campus South', '200 Example Avenue, Perth WA'),
        ]
        classroom_specs = [
            ('Studio A', 14),
            ('Studio B', 10),
        ]
        locations = []

        for facility_name, address in facility_specs:
            facility, _ = Facility.objects.get_or_create(
                name=facility_name,
                defaults={
                    'address': address,
                    'phone': '08 6111 0000',
                    'email': 'demo-campus@example.com',
                    'is_active': True,
                },
            )
            for classroom_name, capacity in classroom_specs:
                classroom, _ = Classroom.objects.get_or_create(
                    facility=facility,
                    name=classroom_name,
                    defaults={
                        'capacity': capacity,
                        'is_active': True,
                    },
                )
                locations.append((facility, classroom))

        return locations
