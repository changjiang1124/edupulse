from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create sample data for teacher clock in/out testing'

    def handle(self, *args, **options):
        User = get_user_model()

        teacher_username = 'teacher'
        teacher_password = 'Teacher123!'
        teacher_email = 'changjiang1124+teacher@gmail.com'
        teacher_phone = '0401909771'

        teacher, created = User.objects.get_or_create(
            username=teacher_username,
            defaults={
                'first_name': 'Test',
                'last_name': 'Teacher',
                'email': teacher_email,
                'role': 'teacher',
                'is_active': True,
            }
        )
        if created:
            teacher.set_password(teacher_password)
            teacher.phone = teacher_phone
            teacher.save()

        from facilities.models import Facility, Classroom
        facility, _ = Facility.objects.get_or_create(
            name='Test Studio',
            defaults={
                'address': 'Anywhere for testing',
                'latitude': Decimal('0.0'),
                'longitude': Decimal('0.0'),
                'attendance_radius': 20000000,
                'is_active': True,
            }
        )

        classroom, _ = Classroom.objects.get_or_create(
            facility=facility,
            name='Room A',
            defaults={'capacity': 20, 'is_active': True}
        )

        from academics.models import Course, Class
        today = timezone.now().date()
        start_time = timezone.now().time().replace(second=0, microsecond=0)

        course, _ = Course.objects.get_or_create(
            name='Clock Test Course',
            start_date=today,
            defaults={
                'short_description': 'For teacher clock testing',
                'price': Decimal('100.00'),
                'course_type': 'group',
                'category': 'term_courses',
                'status': 'published',
                'repeat_pattern': 'once',
                'start_time': start_time,
                'duration_minutes': 60,
                'vacancy': 10,
                'is_online_bookable': True,
                'bookable_state': 'bookable',
                'teacher': teacher,
                'facility': facility,
                'classroom': classroom,
            }
        )

        Class.objects.get_or_create(
            course=course,
            date=today,
            start_time=start_time,
            defaults={
                'duration_minutes': 60,
                'teacher': teacher,
                'facility': facility,
                'classroom': classroom,
                'is_active': True,
            }
        )

        self.stdout.write(self.style.SUCCESS('Teacher clock test data created'))
        self.stdout.write(f"Login username: {teacher_username}")
        self.stdout.write(f"Login password: {teacher_password}")