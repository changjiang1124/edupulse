from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from unittest.mock import patch, MagicMock
import json

from core.models import NotificationQuota, OrganisationSettings
from students.models import Student
from enrollment.models import Enrollment
from academics.models import Course

User = get_user_model()


class NotificationViewTest(TestCase):
    """Test cases for notification views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user (staff member)
        self.user = User.objects.create_user(
            username='teststaff',
            email='staff@test.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        
        # Create test student
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            contact_email='student@test.com',
            contact_phone='0412345678'
        )
        
        # Create test course for enrollment
        from datetime import date, timedelta, time
        self.course = Course.objects.create(
            name='Test Course',
            short_description='Test course description',
            price=100.00,
            status='published',
            start_time=time(10, 0),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )
        
        # Create test enrollment with contact info
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='form',
            form_data={
                'contact_info': {
                    'primary_email': 'parent@test.com',
                    'primary_phone': '0487654321',
                    'contact_type': 'guardian',
                    'student_age': 16
                }
            }
        )
        
        # Create notification quotas
        NotificationQuota.objects.create(
            notification_type='email',
            year=timezone.now().year,
            month=timezone.now().month,
            monthly_limit=100,
            used_count=10
        )
        
        NotificationQuota.objects.create(
            notification_type='sms',
            year=timezone.now().year,
            month=timezone.now().month,
            monthly_limit=50,
            used_count=5
        )
    
    def test_send_notification_requires_login(self):
        """Test that send notification requires authentication"""
        url = reverse('core:send_notification')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_send_notification_requires_staff(self):
        """Test that send notification requires staff privileges"""
        # Create non-staff user
        non_staff_user = User.objects.create_user(
            username='nonstaffuser',
            email='nonstaff@test.com',
            password='testpass123',
            is_staff=False
        )
        
        self.client.login(username='nonstaffuser', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 403)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Unauthorized')
    
    def test_send_notification_invalid_form(self):
        """Test send notification with invalid form data"""
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url, data={
            'student_ids': '',  # Empty student IDs
            'notification_type': 'email',
            'message_type': 'general',
            'message': 'Test message'
            # Missing subject for email
        })
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
    
    @patch('core.views._send_email_notification')
    def test_send_email_notification_success(self, mock_send_email):
        """Test successful email notification sending"""
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url, data={
            'student_ids': str(self.student.pk),
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message content'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['results']['email_sent'], 1)
        self.assertEqual(data['results']['sms_sent'], 0)
        
        # Check that email function was called
        mock_send_email.assert_called_once()
        
        # Check quota was consumed
        email_quota = NotificationQuota.get_current_quota('email')
        self.assertEqual(email_quota.used_count, 11)  # Was 10, now 11
    
    @patch('core.views._send_sms_notification')
    def test_send_sms_notification_success(self, mock_send_sms):
        """Test successful SMS notification sending"""
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url, data={
            'student_ids': str(self.student.pk),
            'notification_type': 'sms',
            'message_type': 'general',
            'message': 'Test SMS message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['results']['email_sent'], 0)
        self.assertEqual(data['results']['sms_sent'], 1)
        
        # Check that SMS function was called
        mock_send_sms.assert_called_once()
        
        # Check quota was consumed
        sms_quota = NotificationQuota.get_current_quota('sms')
        self.assertEqual(sms_quota.used_count, 6)  # Was 5, now 6
    
    @patch('core.views._send_email_notification')
    @patch('core.views._send_sms_notification')
    def test_send_both_notifications_success(self, mock_send_sms, mock_send_email):
        """Test successful both email and SMS notification sending"""
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url, data={
            'student_ids': str(self.student.pk),
            'notification_type': 'both',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message content'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['results']['email_sent'], 1)
        self.assertEqual(data['results']['sms_sent'], 1)
        
        # Check both functions were called
        mock_send_email.assert_called_once()
        mock_send_sms.assert_called_once()
    
    def test_send_notification_quota_exceeded(self):
        """Test notification sending when quota is exceeded"""
        # Set email quota to exceeded
        email_quota = NotificationQuota.get_current_quota('email')
        email_quota.used_count = email_quota.monthly_limit
        email_quota.save()
        
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url, data={
            'student_ids': str(self.student.pk),
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Email quota exceeded', data['error'])
    
    def test_send_notification_no_students_found(self):
        """Test notification sending with invalid student IDs"""
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:send_notification')
        response = self.client.post(url, data={
            'student_ids': '99999',  # Non-existent student
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'No valid students found')
    
    def test_get_notification_quotas(self):
        """Test getting notification quotas"""
        self.client.login(username='teststaff', password='testpass123')
        
        url = reverse('core:get_notification_quotas')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('quotas', data)
        
        # Check email quota data
        email_quota = data['quotas']['email']
        self.assertEqual(email_quota['used'], 10)
        self.assertEqual(email_quota['limit'], 100)
        self.assertEqual(email_quota['remaining'], 90)
        
        # Check SMS quota data
        sms_quota = data['quotas']['sms']
        self.assertEqual(sms_quota['used'], 5)
        self.assertEqual(sms_quota['limit'], 50)
        self.assertEqual(sms_quota['remaining'], 45)
    
    def test_get_notification_quotas_requires_staff(self):
        """Test that getting quotas requires staff privileges"""
        # Create non-staff user
        non_staff_user = User.objects.create_user(
            username='nonstaffuser2',
            email='nonstaff2@test.com',
            password='testpass123',
            is_staff=False
        )
        
        self.client.login(username='nonstaffuser2', password='testpass123')
        
        url = reverse('core:get_notification_quotas')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Unauthorized')


class ContactInfoExtractionTest(TestCase):
    """Test cases for contact information extraction logic"""
    
    def setUp(self):
        """Set up test data"""
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            contact_email='student@test.com',
            contact_phone='0412345678'
        )
        
        from datetime import date, timedelta, time
        self.course = Course.objects.create(
            name='Test Course',
            short_description='Test course description',
            price=100.00,
            status='published',
            start_time=time(10, 0),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )
    
    def test_get_student_contact_info_from_enrollment(self):
        """Test getting contact info from enrollment data"""
        from core.views import _get_student_contact_info
        
        # Create enrollment with contact info
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='form',
            form_data={
                'contact_info': {
                    'primary_email': 'guardian@test.com',
                    'primary_phone': '0487654321',
                    'contact_type': 'guardian',
                    'student_age': 16
                }
            }
        )
        
        contact_info = _get_student_contact_info(self.student)
        
        self.assertEqual(contact_info['email'], 'guardian@test.com')
        self.assertEqual(contact_info['phone'], '0487654321')
        self.assertEqual(contact_info['type'], 'guardian')
    
    def test_get_student_contact_info_fallback_to_student_model(self):
        """Test fallback to student model when no enrollment data"""
        from core.views import _get_student_contact_info
        
        contact_info = _get_student_contact_info(self.student)
        
        # Should use student model data
        self.assertEqual(contact_info['name'], 'Test Student')
        self.assertEqual(contact_info['email'], 'student@test.com')
        self.assertEqual(contact_info['phone'], '0412345678')
        self.assertEqual(contact_info['type'], 'student')
    
    def test_get_student_contact_info_guardian_fallback(self):
        """Test guardian contact detection from student model"""
        from core.views import _get_student_contact_info
        
        # Add guardian name and set minor birth date to indicate minor status
        from datetime import timedelta
        self.student.guardian_name = 'Parent Guardian'
        self.student.birth_date = timezone.now().date() - timedelta(days=16*365)
        self.student.save()
        
        contact_info = _get_student_contact_info(self.student)
        
        # Should detect guardian type when student is minor with guardian
        self.assertEqual(contact_info['type'], 'guardian')
        # Fallback uses student contact details when no enrollment override
        self.assertEqual(contact_info['email'], 'student@test.com')
        self.assertEqual(contact_info['phone'], '0412345678')


class EmailSMSHelperFunctionsTest(TestCase):
    """Test cases for email and SMS helper functions"""
    
    @patch('django.core.mail.EmailMessage')
    def test_send_email_notification(self, mock_email_message):
        """Test email notification sending helper"""
        from core.views import _send_email_notification
        org_settings = OrganisationSettings.get_instance()
        org_settings.organisation_name = 'Creative Hub'
        org_settings.save()

        email_instance = MagicMock()
        mock_email_message.return_value = email_instance
        
        _send_email_notification(
            recipient_email='test@example.com',
            recipient_name='Test User',
            subject='Test Subject',
            message='Test message content',
            message_type='general',
            recipient_type='student'
        )
        
        mock_email_message.assert_called_once()
        _, kwargs = mock_email_message.call_args
        self.assertIn('Creative Hub', kwargs['body'])
        email_instance.send.assert_called_once()
    
    @patch('core.sms_backends.send_sms')
    def test_send_sms_notification(self, mock_send_sms):
        """Test SMS notification sending helper"""
        from core.views import _send_sms_notification
        org_settings = OrganisationSettings.get_instance()
        org_settings.organisation_name = 'Creative Hub'
        org_settings.save()
        
        _send_sms_notification(
            recipient_phone='+61412345678',
            recipient_name='Test User',
            message='Test message',
            message_type='general',
            recipient_type='student'
        )
        
        # Check that SMS send was called
        mock_send_sms.assert_called_once()
        
        # Check message formatting
        call_args = mock_send_sms.call_args
        sms_content = call_args[0][1]  # Second argument is the message
        self.assertIn('Hi Test User', sms_content)
        self.assertIn('Test message', sms_content)
        self.assertIn('Creative Hub', sms_content)
    
    @patch('core.sms_backends.send_sms')
    def test_send_sms_notification_truncation(self, mock_send_sms):
        """Test SMS message truncation for long messages"""
        from core.views import _send_sms_notification
        
        long_message = 'x' * 200  # Very long message
        
        _send_sms_notification(
            recipient_phone='+61412345678',
            recipient_name='Test User',
            message=long_message,
            message_type='general',
            recipient_type='student'
        )
        
        # Check that message was truncated
        call_args = mock_send_sms.call_args
        sms_content = call_args[0][1]
        self.assertLessEqual(len(sms_content), 160)
        self.assertIn('...', sms_content)  # Should end with ellipsis
