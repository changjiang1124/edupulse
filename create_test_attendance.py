import os
import django
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from accounts.models import Staff
from core.models import TeacherAttendance
from facilities.models import Facility
from academics.models import Course, Class

def create_test_data():
    print("Creating test attendance data...")
    
    # Get teacher
    try:
        teacher = Staff.objects.get(username='teacher_test')
    except Staff.DoesNotExist:
        print("Teacher 'teacher_test' not found. Creating...")
        teacher = Staff.objects.create_user(
            username='teacher_test',
            password='Test1234!',
            first_name='Test',
            last_name='Teacher',
            email='teacher_test@example.com',
            role='teacher'
        )
    
    # Get facility
    facility = Facility.objects.first()
    if not facility:
        print("No facility found. Creating default...")
        facility = Facility.objects.create(
            name='Main Campus',
            address='123 Art Street',
            latitude=Decimal('-31.9505'),
            longitude=Decimal('115.8605'),
            attendance_radius=500
        )
        
    # Get course/class
    course = Course.objects.filter(teacher=teacher).first()
    if not course:
        # Create dummy course if needed or just use general
        pass

    # Clear existing recent records for this teacher to avoid clutter
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    print(f"Clearing records since {start_of_week}...")
    TeacherAttendance.objects.filter(
        teacher=teacher,
        timestamp__date__gte=start_of_week
    ).delete()

    # Create Session 1: Yesterday morning (complete)
    yesterday = today - timedelta(days=1)
    
    # Clock in 09:00
    t1_in = timezone.make_aware(datetime.combine(yesterday, datetime.strptime("09:00", "%H:%M").time()))
    TeacherAttendance.objects.create(
        teacher=teacher,
        clock_type='clock_in',
        timestamp=t1_in,
        facility=facility,
        latitude=Decimal('-31.9505'),
        longitude=Decimal('115.8605'),
        distance_from_facility=10,
        location_verified=True,
        ip_address='127.0.0.1'
    )
    
    # Clock out 12:00
    t1_out = timezone.make_aware(datetime.combine(yesterday, datetime.strptime("12:00", "%H:%M").time()))
    TeacherAttendance.objects.create(
        teacher=teacher,
        clock_type='clock_out',
        timestamp=t1_out,
        facility=facility,
        latitude=Decimal('-31.9505'),
        longitude=Decimal('115.8605'),
        distance_from_facility=10,
        location_verified=True,
        ip_address='127.0.0.1'
    )
    print("Created Session 1: Yesterday 09:00 - 12:00 (3h)")

    # Create Session 2: Today morning (complete)
    # Clock in 08:30
    t2_in = timezone.make_aware(datetime.combine(today, datetime.strptime("08:30", "%H:%M").time()))
    TeacherAttendance.objects.create(
        teacher=teacher,
        clock_type='clock_in',
        timestamp=t2_in,
        facility=facility,
        latitude=Decimal('-31.9505'),
        longitude=Decimal('115.8605'),
        distance_from_facility=15,
        location_verified=True,
        ip_address='127.0.0.1'
    )
    
    # Clock out 16:30
    t2_out = timezone.make_aware(datetime.combine(today, datetime.strptime("16:30", "%H:%M").time()))
    TeacherAttendance.objects.create(
        teacher=teacher,
        clock_type='clock_out',
        timestamp=t2_out,
        facility=facility,
        latitude=Decimal('-31.9505'),
        longitude=Decimal('115.8605'),
        distance_from_facility=15,
        location_verified=True,
        ip_address='127.0.0.1'
    )
    print("Created Session 2: Today 08:30 - 16:30 (8h)")
    
    # Create Session 3: Today evening (incomplete - currently clocked in?) or just missing clock out
    # If the teacher is currently clocked in for real, this might conflict.
    # Let's say they came back later.
    
    # Clock in 18:00
    # Only if current time is after 18:00
    now = timezone.localtime()
    if now.hour >= 18:
        t3_in = timezone.make_aware(datetime.combine(today, datetime.strptime("18:00", "%H:%M").time()))
        TeacherAttendance.objects.create(
            teacher=teacher,
            clock_type='clock_in',
            timestamp=t3_in,
            facility=facility,
            latitude=Decimal('-31.9505'),
            longitude=Decimal('115.8605'),
            distance_from_facility=5,
            location_verified=True,
            ip_address='127.0.0.1'
        )
        print("Created Session 3: Today 18:00 - ... (Active)")

    print("\nDone! Login as 'teacher_test' (password: Test1234!) to check /core/clock/timesheet/")

if __name__ == '__main__':
    create_test_data()
