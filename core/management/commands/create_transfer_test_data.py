from django.core.management.base import BaseCommand
from academics.models import Course, Class
from students.models import Student
from enrollment.models import Enrollment
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import Staff

class Command(BaseCommand):
    help = 'Create test data for Enrollment Transfer verification'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating test data...')
        
        # 1. Create Course A (Source)
        # Start 2 weeks ago to have past classes
        start_date = timezone.now().date() - timedelta(days=14)
        course_a, _ = Course.objects.get_or_create(
            name="Test Transfer Source: Drawing Basics",
            defaults={
                'description': "Source course for transfer test",
                'price': 200.00,
                'status': 'published',
                'vacancy': 20,
                'start_date': start_date,
                'end_date': start_date + timedelta(days=30),
                'start_time': '10:00:00',
                'duration_minutes': 60,
                'course_type': 'group',
                'repeat_pattern': 'weekly', # Ensure weekly classes generated
            }
        )
        # Ensure price is 200
        course_a.price = 200.00
        # Ensure dates are set correctly if retrieving existing
        course_a.start_date = start_date
        course_a.end_date = start_date + timedelta(days=30)
        course_a.save()
        # Regenerate classes to ensure past classes exist
        course_a.generate_classes()
        self.stdout.write(f'Created/Updated Course A: {course_a.name} ($200) - Starts {start_date}')

        # 2. Create Course B (Target - Standard)
        course_b, _ = Course.objects.get_or_create(
            name="Test Transfer Target: Painting Basics",
            defaults={
                'description': "Standard target course for transfer test",
                'price': 250.00,
                'status': 'published',
                'vacancy': 20,
                'start_date': start_date,
                'end_date': start_date + timedelta(days=30),
                'start_time': '12:00:00',
                'duration_minutes': 90,
                'course_type': 'group',
                'repeat_pattern': 'weekly',
            }
        )
        course_b.price = 250.00
        course_b.vacancy = 20
        course_b.start_date = start_date
        course_b.end_date = start_date + timedelta(days=30)
        course_b.save()
        course_b.generate_classes()
        self.stdout.write(f'Created/Updated Course B: {course_b.name} ($250, Vacancy 20) - Starts {start_date}')

        # 3. Create Course C (Target - Full)
        course_c, _ = Course.objects.get_or_create(
            name="Test Transfer Target: Pottery Masterclass (Full)",
            defaults={
                'description': "Full target course for transfer test",
                'price': 300.00,
                'status': 'published',
                'vacancy': 0,
                'start_date': start_date,
                'end_date': start_date + timedelta(days=30),
                'start_time': '14:00:00',
                'duration_minutes': 120,
                'course_type': 'group',
                'repeat_pattern': 'weekly',
            }
        )
        course_c.price = 300.00
        course_c.vacancy = 0 # Force 0 vacancy
        course_c.start_date = start_date
        course_c.end_date = start_date + timedelta(days=30)
        course_c.save()
        course_c.generate_classes()
        self.stdout.write(f'Created/Updated Course C: {course_c.name} ($300, Vacancy 0) - Starts {start_date}')
        
        # 4. Create Student
        student, _ = Student.objects.get_or_create(
            first_name="Test",
            last_name="TransferStudent",
            defaults={
                'birth_date': '2000-01-01',
                'contact_email': 'test.transfer@example.com'
            }
        )
        self.stdout.write(f'Created/Updated Student: {student.get_full_name()}')
        
        # 5. Enroll Student in Course A
        # Cancel any existing enrollments for this student in these courses to start fresh
        Enrollment.objects.filter(
            student=student, 
            course__in=[course_a, course_b, course_c]
        ).delete()
        
        enrollment = Enrollment.objects.create(
            student=student,
            course=course_a,
            status='confirmed',
            registration_status='new',
            course_fee=200.00,
            registration_fee=0,
            registration_fee_paid=True,
            source_channel='manual'
        )
        # Backdate enrollment to course start date
        enrollment.created_at = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        enrollment.save()
        
        self.stdout.write(f'Enrolled Student in Course A (ID: {enrollment.id}) - Backdated to {start_date}')
        
        self.stdout.write(self.style.SUCCESS('Test Data Creation Complete!'))
