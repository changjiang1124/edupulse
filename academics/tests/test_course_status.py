from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from academics.models import Course, Class
from enrollment.models import Enrollment
from students.models import Student
from accounts.models import Staff
from unittest.mock import patch

class CourseStatusTests(TestCase):
    def setUp(self):
        patcher = patch('academics.signals.WooCommerceSyncService')
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)
        # Create a teacher
        self.teacher = Staff.objects.create_user(
            username='teacher',
            password='password'
        )
        
        # Create a course
        self.course = Course.objects.create(
            name='Test Course',
            start_date=timezone.now().date(),
            start_time='10:00',
            duration_minutes=60,
            price=100.00,
            status='published',
            teacher=self.teacher
        )
        
        # Create a student
        self.student = Student.objects.create(
            first_name='John',
            last_name='Doe',
            birth_date='2010-01-01'
        )

    def test_published_to_draft_without_enrollments(self):
        """Test that a published course without enrollments can be reverted to draft"""
        self.course.status = 'draft'
        self.course.full_clean() # Should pass
        self.course.save()
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, 'draft')

    def test_published_to_draft_with_enrollments(self):
        """Test that a published course with enrollments CANNOT be reverted to draft"""
        # Create enrollment
        Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        
        self.course.status = 'draft'
        with self.assertRaises(ValidationError) as cm:
            self.course.full_clean()
            
        self.assertIn('status', cm.exception.message_dict)

    def test_published_to_draft_with_enrollments_validation(self):
        """Test validation error when reverting to draft with enrollments"""
        Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        
        self.course.status = 'draft'
        with self.assertRaises(ValidationError) as cm:
            self.course.clean()
        
        self.assertIn('status', cm.exception.message_dict)

    def test_archive_course_auto_closes_booking(self):
        """Test that archiving a course automatically closes booking"""
        self.course.status = 'archived'
        self.course.bookable_state = 'bookable' # Ensure it starts open
        self.course.save()
        
        self.course.refresh_from_db()
        self.assertEqual(self.course.status, 'archived')
        self.assertEqual(self.course.bookable_state, 'closed')

    def test_delete_protection_with_enrollments(self):
        """Test that courses with enrollments cannot be deleted"""
        Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        
        with self.assertRaises(ValidationError):
            self.course.delete()

    def test_delete_allowed_without_enrollments(self):
        """Test that courses without enrollments can be deleted"""
        course_id = self.course.id
        self.course.delete()
        self.assertFalse(Course.objects.filter(id=course_id).exists())
