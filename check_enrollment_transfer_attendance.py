#!/usr/bin/env python
"""
Script to exercise enrollment transfer and verify attendance window behaviour.
"""
import os
import sys
from datetime import timedelta, time

import django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.db.models.signals import post_save
from django.conf import settings

from accounts.models import Staff
from students.models import Student
from academics.models import Course, Class
from academics.signals import sync_course_to_woocommerce
from enrollment.models import Enrollment, Attendance


def _attendance_exists(student, class_instance):
    return Attendance.objects.filter(student=student, class_instance=class_instance).exists()


def _print_attendance(label, student, classes):
    print(f"\n{label}")
    for class_instance in classes:
        exists = _attendance_exists(student, class_instance)
        class_time = class_instance.get_class_datetime().strftime('%Y-%m-%d %H:%M')
        print(f"- {class_instance.course.name} | {class_time} | attendance={exists}")


def _ensure_admin():
    user, created = Staff.objects.get_or_create(
        username='transfer_admin',
        defaults={
            'first_name': 'Transfer',
            'last_name': 'Admin',
            'email': 'transfer.admin@example.com',
            'role': 'admin'
        }
    )
    if created:
        user.set_password('transfer_admin_pass')
    user.role = 'admin'
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


def _create_course(name, start_date, start_time):
    return Course.objects.create(
        name=name,
        price=100.00,
        status='published',
        start_date=start_date,
        start_time=start_time,
        repeat_pattern='once',
        duration_minutes=60,
        vacancy=20,
        is_online_bookable=False
    )

def _ensure_allowed_host(host):
    if '*' in settings.ALLOWED_HOSTS:
        return
    if not isinstance(settings.ALLOWED_HOSTS, list):
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS)
    if host not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append(host)


def run_transfer_check():
    keep_data = os.getenv('KEEP_TRANSFER_TEST_DATA') == '1'
    allowed_host = os.getenv('TRANSFER_TEST_HOST', 'testserver')
    _ensure_allowed_host(allowed_host)
    client = Client(HTTP_HOST=allowed_host)

    now_local = timezone.localtime(timezone.now())
    effective_at = (now_local.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1))
    before_date = (effective_at - timedelta(days=1)).date()
    after_date = (effective_at + timedelta(days=1)).date()

    post_save.disconnect(sync_course_to_woocommerce, sender=Course)
    try:
        admin = _ensure_admin()
        student = Student.objects.create(
            first_name='Transfer',
            last_name='Attendance',
            contact_email='transfer.attendance@example.com'
        )

        source_course = _create_course(
            name=f'Transfer Check Source {effective_at.strftime("%Y%m%d%H%M%S")}',
            start_date=before_date,
            start_time=time(9, 0)
        )
        target_course = _create_course(
            name=f'Transfer Check Target {effective_at.strftime("%Y%m%d%H%M%S")}',
            start_date=before_date,
            start_time=time(9, 0)
        )
    finally:
        post_save.connect(sync_course_to_woocommerce, sender=Course)

    source_before = Class.objects.create(
        course=source_course,
        date=before_date,
        start_time=time(9, 0),
        duration_minutes=60,
        is_active=True
    )
    source_after = Class.objects.create(
        course=source_course,
        date=after_date,
        start_time=time(9, 0),
        duration_minutes=60,
        is_active=True
    )
    target_before = Class.objects.create(
        course=target_course,
        date=before_date,
        start_time=time(14, 0),
        duration_minutes=60,
        is_active=True
    )
    target_after = Class.objects.create(
        course=target_course,
        date=after_date,
        start_time=time(14, 0),
        duration_minutes=60,
        is_active=True
    )

    source_enrollment = Enrollment.objects.create(
        student=student,
        course=source_course,
        status='confirmed',
        source_channel='staff'
    )

    _print_attendance(
        "Before transfer",
        student,
        [source_before, source_after, target_before, target_after]
    )

    client.force_login(admin)
    transfer_url = reverse('enrollment:enrollment_transfer', args=[source_enrollment.pk])
    transfer_effective_str = effective_at.replace(tzinfo=None).strftime('%Y-%m-%dT%H:%M')
    response = client.post(
        transfer_url,
        {
            'target_course': str(target_course.id),
            'price_handling': 'carry_over',
            'transfer_effective_at': transfer_effective_str,
            'force_transfer': 'on'
        },
        follow=True
    )

    if response.status_code not in [200, 302]:
        raise RuntimeError(f"Transfer request failed with status {response.status_code}")

    new_enrollment = Enrollment.objects.filter(
        form_data__transferred_from=source_enrollment.id
    ).order_by('-id').first()

    if not new_enrollment:
        raise RuntimeError("Transfer did not create a new enrollment. Check form errors or logs.")

    _print_attendance(
        "After transfer",
        student,
        [source_before, source_after, target_before, target_after]
    )

    checks = {
        'source_before_kept': _attendance_exists(student, source_before),
        'source_after_removed': not _attendance_exists(student, source_after),
        'target_before_empty': not _attendance_exists(student, target_before),
        'target_after_created': _attendance_exists(student, target_after),
    }

    print("\nChecks")
    for key, passed in checks.items():
        print(f"- {key}: {'OK' if passed else 'FAIL'}")

    if not keep_data:
        Attendance.objects.filter(student=student).delete()
        Enrollment.objects.filter(id__in=[source_enrollment.id, new_enrollment.id]).delete()
        Class.objects.filter(id__in=[
            source_before.id, source_after.id, target_before.id, target_after.id
        ]).delete()
        Course.objects.filter(id__in=[source_course.id, target_course.id]).delete()
        student.delete()

    success = all(checks.values())
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = run_transfer_check()
    sys.exit(exit_code)
