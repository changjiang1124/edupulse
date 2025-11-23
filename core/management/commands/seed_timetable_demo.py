import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import Class, Course
from enrollment.models import Enrollment
from facilities.models import Classroom, Facility
from students.models import Student


class Command(BaseCommand):
    help = 'Seed demo data so the dashboard weekly timetable is populated'

    def handle(self, *args, **options):
        User = get_user_model()

        today = timezone.localdate()
        start_of_week = today - datetime.timedelta(days=today.weekday())

        teachers_data = [
            {
                'username': 'teacher_alice',
                'first_name': 'Alice',
                'last_name': 'Nguyen',
                'email': 'demo+alice@example.com',
            },
            {
                'username': 'teacher_ben',
                'first_name': 'Ben',
                'last_name': 'Taylor',
                'email': 'demo+ben@example.com',
            },
            {
                'username': 'teacher_carla',
                'first_name': 'Carla',
                'last_name': 'Singh',
                'email': 'demo+carla@example.com',
            },
        ]

        teachers = {}
        for data in teachers_data:
            teacher, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': data['email'],
                    'role': 'teacher',
                    'is_active': True,
                },
            )
            if created:
                teacher.set_password('Teacher123!')
                teacher.save()
            teachers[data['username']] = teacher

        facility_cbd, _ = Facility.objects.get_or_create(
            name='Perth CBD Studio',
            defaults={
                'address': '123 Art Lane, Perth WA',
                'phone': '08 6000 0000',
                'email': 'cbd@example.com',
                'is_active': True,
            },
        )

        facility_north, _ = Facility.objects.get_or_create(
            name='Northbridge Workshop',
            defaults={
                'address': '45 Creative Ave, Northbridge WA',
                'phone': '08 6111 1111',
                'email': 'north@example.com',
                'is_active': True,
            },
        )

        classroom_a, _ = Classroom.objects.get_or_create(
            facility=facility_cbd,
            name='Studio A',
            defaults={'capacity': 16, 'is_active': True},
        )
        classroom_b, _ = Classroom.objects.get_or_create(
            facility=facility_cbd,
            name='Studio B',
            defaults={'capacity': 14, 'is_active': True},
        )
        classroom_c, _ = Classroom.objects.get_or_create(
            facility=facility_north,
            name='Workshop C',
            defaults={'capacity': 18, 'is_active': True},
        )

        courses_info = [
            {
                'name': 'Drawing Fundamentals',
                'teacher': teachers['teacher_alice'],
                'facility': facility_cbd,
                'classroom': classroom_a,
                'start_time': datetime.time(9, 30),
                'duration_minutes': 90,
                'course_type': 'group',
                'category': 'term_courses',
                'price': Decimal('280.00'),
            },
            {
                'name': 'Watercolour Essentials',
                'teacher': teachers['teacher_ben'],
                'facility': facility_cbd,
                'classroom': classroom_b,
                'start_time': datetime.time(13, 30),
                'duration_minutes': 120,
                'course_type': 'group',
                'category': 'term_courses',
                'price': Decimal('320.00'),
            },
            {
                'name': 'Digital Illustration Lab',
                'teacher': teachers['teacher_carla'],
                'facility': facility_north,
                'classroom': classroom_c,
                'start_time': datetime.time(17, 30),
                'duration_minutes': 90,
                'course_type': 'group',
                'category': 'day_courses',
                'price': Decimal('300.00'),
            },
            {
                'name': 'Portfolio Coaching (1:1)',
                'teacher': teachers['teacher_carla'],
                'facility': facility_north,
                'classroom': classroom_c,
                'start_time': datetime.time(15, 0),
                'duration_minutes': 60,
                'course_type': 'private',
                'category': 'day_courses',
                'price': Decimal('180.00'),
            },
        ]

        courses = {}
        for info in courses_info:
            course, _ = Course.objects.get_or_create(
                name=info['name'],
                defaults={
                    'short_description': 'Demo timetable course',
                    'price': info['price'],
                    'course_type': info['course_type'],
                    'category': info['category'],
                    'status': 'published',
                    'teacher': info['teacher'],
                    'start_date': start_of_week,
                    'repeat_pattern': 'weekly',
                    'start_time': info['start_time'],
                    'duration_minutes': info['duration_minutes'],
                    'vacancy': 12,
                    'is_online_bookable': True,
                    'bookable_state': 'bookable',
                    'facility': info['facility'],
                    'classroom': info['classroom'],
                },
            )
            courses[info['name']] = course

        schedule_map = {
            'Drawing Fundamentals': [
                (0, datetime.time(9, 30)),
                (2, datetime.time(9, 30)),
            ],
            'Watercolour Essentials': [
                (1, datetime.time(13, 30)),
                (4, datetime.time(13, 30)),
            ],
            'Digital Illustration Lab': [
                (3, datetime.time(17, 30)),
                (5, datetime.time(10, 0)),
            ],
            'Portfolio Coaching (1:1)': [
                (2, datetime.time(15, 0)),
                (6, datetime.time(11, 0)),
            ],
        }

        classes_created = 0
        for course_name, slots in schedule_map.items():
            course = courses.get(course_name)
            if not course:
                continue
            for day_offset, slot_time in slots:
                class_date = start_of_week + datetime.timedelta(days=day_offset)
                _, created = Class.objects.get_or_create(
                    course=course,
                    date=class_date,
                    start_time=slot_time,
                    defaults={
                        'duration_minutes': course.duration_minutes,
                        'teacher': course.teacher,
                        'facility': course.facility,
                        'classroom': course.classroom,
                        'is_active': True,
                    },
                )
                if created:
                    classes_created += 1

        students_data = [
            {'first_name': 'Liam', 'last_name': 'Brown', 'contact_email': 'demo+liam@example.com'},
            {'first_name': 'Olivia', 'last_name': 'Lee', 'contact_email': 'demo+olivia@example.com'},
            {'first_name': 'Noah', 'last_name': 'Patel', 'contact_email': 'demo+noah@example.com'},
            {'first_name': 'Isla', 'last_name': 'Wong', 'contact_email': 'demo+isla@example.com'},
            {'first_name': 'Ethan', 'last_name': 'Smith', 'contact_email': 'demo+ethan@example.com'},
        ]

        students = []
        for data in students_data:
            student, _ = Student.objects.get_or_create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                defaults={
                    'contact_email': data['contact_email'],
                    'contact_phone': '0400000000',
                },
            )
            students.append(student)

        enrollments_created = 0
        course_list = list(courses.values())
        for idx, student in enumerate(students):
            for course in course_list[:3]:
                defaults = {
                    'status': 'confirmed',
                    'source_channel': 'staff',
                    'course_fee': course.price,
                    'registration_fee': Decimal('0.00'),
                }
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    course=course,
                    defaults=defaults,
                )
                if created:
                    class_instance = Class.objects.filter(course=course).order_by('date', 'start_time').first()
                    if class_instance:
                        enrollment.class_instance = class_instance
                        enrollment.save(update_fields=['class_instance'])
                    enrollments_created += 1

        self.stdout.write(self.style.SUCCESS('Timetable demo data ready.'))
        self.stdout.write(f"Teachers ensured: {len(teachers)}")
        self.stdout.write(f"Courses ensured: {len(courses)}")
        self.stdout.write(f"Classes created this run: {classes_created}")
        self.stdout.write(f"Enrollments created this run: {enrollments_created}")
        self.stdout.write('Demo teacher password for new accounts: Teacher123!')
