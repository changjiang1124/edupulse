"""Seed a throwaway database with fake staff and clock records for Help Centre screenshots.

Run against a fresh local database only:
    DEBUG=True python manage.py migrate
    DEBUG=True python manage.py shell < help_centre/screenshots/seed_demo.py

Dates are relative to today (Perth time), so screenshots can be regenerated on any day.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from academics.models import Class, Course
from accounts.models import Staff
from core.models import OrganisationSettings, TeacherAttendance
from facilities.models import Classroom, Facility
from students.models import Student

# Refuse to touch anything that looks like a real database.
if not settings.DEBUG or Student.objects.exists() or Staff.objects.exclude(email__endswith='@example.com').exists():
    raise SystemExit('Refusing to seed: use a fresh local database with DEBUG=True.')

PASSWORD = 'DemoPass-2026!'
LAT, LON = Decimal('-31.98160970'), Decimal('115.78837820')
PERTH = timezone.get_current_timezone()
NOW = timezone.localtime()
TODAY = NOW.date()

OrganisationSettings.get_instance()


def staff(username, first, last, role):
    user, _ = Staff.objects.get_or_create(username=username, defaults=dict(
        first_name=first, last_name=last, role=role, email=f'{username}@example.com',
        phone='' if role == 'admin' else '0400 000 000'))
    user.set_password(PASSWORD)
    user.save()
    return user


office = staff('office', 'Office', 'Admin', 'admin')
emma = staff('emma.wilson', 'Emma', 'Wilson', 'teacher')
liam = staff('liam.chen', 'Liam', 'Chen', 'teacher')
sophie = staff('sophie.nguyen', 'Sophie', 'Nguyen', 'teacher')

facility, _ = Facility.objects.get_or_create(name='Claremont Studio', defaults=dict(
    address='Claremont WA 6010', latitude=LAT, longitude=LON, attendance_radius=100))
room, _ = Classroom.objects.get_or_create(name='Studio 1', facility=facility, defaults=dict(capacity=12))


def todays_class(name, teacher, start):
    course = Course(name=name, price=Decimal('899.00'), start_date=TODAY - timedelta(days=60),
                    end_date=TODAY + timedelta(days=10), repeat_pattern='weekly', repeat_weekday=TODAY.weekday(),
                    start_time=start, duration_minutes=90, vacancy=10, teacher=teacher, facility=facility,
                    classroom=room, status='published')
    course._skip_woocommerce_sync_signal = True
    course.save()
    Class.objects.filter(course=course).delete()
    Class.objects.create(course=course, date=TODAY, start_time=start, duration_minutes=90,
                         teacher=teacher, facility=facility, classroom=room, is_active=True)


todays_class('Drawing & Painting (Ages 7-12)', emma, (NOW - timedelta(minutes=50)).time().replace(second=0, microsecond=0))
todays_class('Protege Studio (Ages 13-17)', liam, (NOW + timedelta(minutes=10)).time().replace(second=0, microsecond=0))


def record(teacher, clock_type, when, source='gps', reason='', distance=12.0):
    manual = source == 'manual'
    return TeacherAttendance.objects.create(
        teacher=teacher, clock_type=clock_type, source=source, timestamp=when, facility=facility,
        latitude=None if manual else LAT, longitude=None if manual else LON,
        distance_from_facility=None if manual else distance, location_verified=not manual,
        manual_reason=reason, created_by=office if manual else teacher, updated_by=office if manual else teacher)


def at(days_ago, hour, minute):
    return datetime.combine(TODAY - timedelta(days=days_ago), time(hour, minute), tzinfo=PERTH)


def session(teacher, days_ago, start, end, **kwargs):
    record(teacher, 'clock_in', at(days_ago, *start), **kwargs)
    record(teacher, 'clock_out', at(days_ago, *end), **kwargs)


session(emma, 9, (15, 18), (17, 12), distance=9.4)
session(emma, 7, (15, 22), (17, 6), distance=14.1)
session(emma, 2, (15, 20), (17, 10), distance=11.8)
session(liam, 8, (9, 25), (12, 40), distance=18.3)
session(liam, 7, (16, 20), (18, 5), distance=7.6)
session(liam, 1, (9, 24), (12, 41), distance=16.2)
session(sophie, 9, (16, 2), (18, 34), distance=21.5)
session(sophie, 5, (9, 30), (13, 0), source='manual', reason='Forgot to clock in. Hours confirmed with the office.')
session(sophie, 2, (16, 0), (18, 35), distance=12.9)
# Sophie forgot to clock out yesterday morning (shows as a missed clock-out).
record(sophie, 'clock_in', at(1, 7, 2), distance=13.4)
# Emma is clocked in now and clocks out during the walkthrough.
record(emma, 'clock_in', NOW - timedelta(hours=1), distance=10.2)

print(f'Seeded {Staff.objects.count()} staff and {TeacherAttendance.objects.count()} clock records for {TODAY}.')
