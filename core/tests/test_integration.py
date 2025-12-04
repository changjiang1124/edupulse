from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from unittest.mock import patch, MagicMock

from core.models import NotificationQuota, EmailSettings, SMSSettings, EmailLog, SMSLog
from core.backends import DynamicEmailBackend
from students.models import Student
from enrollment.models import Enrollment
from academics.models import Course

User = get_user_model()


class NotificationSystemIntegrationTest(TransactionTestCase):
    """Integration tests for the complete notification system"""
    
    def setUp(self):
        """Set up test data"""
        # Create email settings
        self.email_settings = EmailSettings.objects.create(
            email_backend_type='google_workspace',
            smtp_host='smtp.gmail.com',
            smtp_port=587,
            smtp_username='test@gmail.com',
            smtp_password='test_password',
            use_tls=True,
            from_email='noreply@perthartschool.com.au',
            from_name='Perth Art School',
            reply_to_email='reply@perthartschool.com.au',
            is_active=True
        )
        
        # Create SMS settings
        self.sms_settings = SMSSettings.objects.create(
            sms_backend_type='twilio',
            account_sid='test_account_sid',
            auth_token='test_auth_token',
            from_number='+61400000000',
            sender_name='Perth Art School',
            is_active=True
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        
        # Create test course
        # Ensure required schedule fields are provided to satisfy model validation
        self.course = Course.objects.create(
            name='Test Art Course',
            short_description='A test art course',
            price=150.00,
            status='published',
            start_date=timezone.now().date(),
            start_time=timezone.now().time().replace(second=0, microsecond=0)
        )
        
        # Create students with different age scenarios
        self.adult_student = Student.objects.create(
            first_name='Adult',
            last_name='Student',
            contact_email='adult@test.com',
            contact_phone='0412345678'
        )
        
        self.minor_student = Student.objects.create(
            first_name='Minor',
            last_name='Student',
            guardian_name='Parent Guardian',
            contact_email='parent@test.com',
            contact_phone='0487654321'
        )
        
        # Create enrollments with proper contact info
        self.adult_enrollment = Enrollment.objects.create(
            student=self.adult_student,
            course=self.course,
            status='confirmed',
            source_channel='form',
            form_data={
                'contact_info': {
                    'primary_email': 'adult@test.com',
                    'primary_phone': '0412345678',
                    'contact_type': 'student',
                    'student_age': 25
                }
            }
        )
        
        self.minor_enrollment = Enrollment.objects.create(
            student=self.minor_student,
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
    
    def test_end_to_end_notification_flow(self):
        """Test complete notification flow from form submission to delivery"""
        # Test adult student notification
        from core.views import _get_student_contact_info
        
        contact_info = _get_student_contact_info(self.adult_student)
        
        self.assertEqual(contact_info['email'], 'adult@test.com')
        self.assertEqual(contact_info['phone'], '0412345678')
        self.assertEqual(contact_info['type'], 'student')
        
        # Test minor student notification
        minor_contact_info = _get_student_contact_info(self.minor_student)
        
        self.assertEqual(minor_contact_info['email'], 'parent@test.com')
        self.assertEqual(minor_contact_info['phone'], '0487654321')
        self.assertEqual(minor_contact_info['type'], 'guardian')
    
    @patch('core.backends.EmailBackend.send_messages')
    def test_email_backend_with_reply_to(self, mock_send):
        """Test email backend integration with reply-to headers"""
        mock_send.return_value = 1
        
        backend = DynamicEmailBackend()
        
        from django.core.mail import EmailMessage
        message = EmailMessage(
            subject='Test Integration Subject',
            body='Test integration message',
            from_email='noreply@perthartschool.com.au',
            to=['recipient@test.com']
        )
        
        # Send message through backend
        backend.send_messages([message])
        
        # Check that reply-to header was added
        self.assertEqual(message.reply_to, ['reply@perthartschool.com.au'])
        
        # Check that send_messages was called
        mock_send.assert_called_once_with([message])
    
    def test_quota_system_integration(self):
        """Test quota system integration across multiple operations"""
        # Initial state
        email_quota = NotificationQuota.get_current_quota('email')
        sms_quota = NotificationQuota.get_current_quota('sms')
        
        initial_email_used = email_quota.used_count
        initial_sms_used = sms_quota.used_count
        
        # Test multiple quota consumptions
        NotificationQuota.consume_quota('email', 5)
        NotificationQuota.consume_quota('sms', 3)
        NotificationQuota.consume_quota('email', 2)
        
        # Refresh quotas
        email_quota.refresh_from_db()
        sms_quota.refresh_from_db()
        
        # Verify consumption
        self.assertEqual(email_quota.used_count, initial_email_used + 7)
        self.assertEqual(sms_quota.used_count, initial_sms_used + 3)
        
        # Test quota checking
        self.assertTrue(NotificationQuota.check_quota_available('email', 10))
        self.assertFalse(NotificationQuota.check_quota_available('email', 2000))
    
    def test_quota_system_monthly_reset_behavior(self):
        """Test quota system behavior across different months"""
        # Create quota for previous month
        prev_quota = NotificationQuota.objects.create(
            notification_type='email',
            year=2025,
            month=8,  # Previous month
            monthly_limit=100,
            used_count=90
        )
        
        # Get current month quota (should be different)
        current_quota = NotificationQuota.get_current_quota('email')
        
        # Should be a different quota object
        self.assertNotEqual(prev_quota.pk, current_quota.pk)
        self.assertEqual(current_quota.used_count, 0)  # Should start fresh
        self.assertEqual(current_quota.month, timezone.now().month)
    
    @patch('core.views._send_email_notification')
    @patch('core.views._send_sms_notification')
    def test_notification_api_integration(self, mock_sms, mock_email):
        """Test notification API integration with all components"""
        # Login as admin
        self.client.login(username='testadmin', password='testpass123')
        
        # Send notification to both students
        student_ids = [self.adult_student.pk, self.minor_student.pk]
        
        response = self.client.post('/core/notifications/send/', {
            'student_ids': ','.join(map(str, student_ids)),
            'notification_type': 'both',
            'message_type': 'general',
            'subject': 'Integration Test Subject',
            'message': 'Integration test message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['results']['email_sent'], 2)
        self.assertEqual(data['results']['sms_sent'], 2)
        
        # Verify helper functions were called correctly
        self.assertEqual(mock_email.call_count, 2)
        self.assertEqual(mock_sms.call_count, 2)
        
        # Check quota consumption
        email_quota = NotificationQuota.get_current_quota('email')
        sms_quota = NotificationQuota.get_current_quota('sms')
        
        self.assertEqual(email_quota.used_count, 2)
        self.assertEqual(sms_quota.used_count, 2)


class DatabaseConsistencyTest(TestCase):
    """Test database consistency and constraint enforcement"""
    
    def test_notification_quota_unique_constraint(self):
        """Test that notification quota unique constraint is enforced"""
        NotificationQuota.objects.create(
            notification_type='email',
            year=2025,
            month=9,
            monthly_limit=100
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):  # Should raise IntegrityError
            NotificationQuota.objects.create(
                notification_type='email',
                year=2025,
                month=9,
                monthly_limit=200
            )
    
    def test_email_settings_singleton_enforcement(self):
        """Test that email settings singleton behavior works correctly"""
        # Create first configuration
        config1 = EmailSettings.objects.create(
            email_backend_type='google_workspace',
            smtp_username='test1@gmail.com',
            smtp_password='password1',
            from_email='test1@test.com',
            from_name='Test 1',
            is_active=True
        )
        
        # Create second configuration (should deactivate first)
        config2 = EmailSettings.objects.create(
            email_backend_type='custom_smtp',
            smtp_username='test2@test.com',
            smtp_password='password2',
            from_email='test2@test.com',
            from_name='Test 2',
            is_active=True
        )
        
        # Refresh first config
        config1.refresh_from_db()
        
        # First should now be inactive
        self.assertFalse(config1.is_active)
        self.assertTrue(config2.is_active)
        
        # Only one should be returned as active
        active_config = EmailSettings.get_active_config()
        self.assertEqual(active_config.pk, config2.pk)
    
    def test_quota_property_calculations(self):
        """Test that quota property calculations are accurate"""
        quota = NotificationQuota.objects.create(
            notification_type='sms',
            year=2025,
            month=9,
            monthly_limit=100,
            used_count=75
        )
        
        # Test all properties
        self.assertEqual(quota.remaining_quota, 25)
        self.assertEqual(quota.usage_percentage, 75.0)
        self.assertFalse(quota.is_quota_exceeded)
        
        # Test exceeded scenario
        quota.used_count = 100
        quota.save()
        
        self.assertEqual(quota.remaining_quota, 0)
        self.assertEqual(quota.usage_percentage, 100.0)
        self.assertTrue(quota.is_quota_exceeded)
        
        # Test over-limit scenario
        quota.used_count = 110
        quota.save()
        
        self.assertEqual(quota.remaining_quota, 0)  # Should not be negative
        self.assertTrue(quota.is_quota_exceeded)


class ErrorHandlingIntegrationTest(TestCase):
    """Test error handling across the notification system"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='admin',
            is_staff=True
        )
        
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            contact_email='student@test.com'
        )
    
    def test_notification_with_invalid_student_ids(self):
        """Test notification handling with invalid student IDs"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/core/notifications/send/', {
            'student_ids': '999999,888888',  # Non-existent IDs
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'No valid students found')
    
    def test_quota_exceeded_handling(self):
        """Test proper handling when quotas are exceeded"""
        # Create quota at limit
        NotificationQuota.objects.create(
            notification_type='email',
            year=timezone.now().year,
            month=timezone.now().month,
            monthly_limit=1,
            used_count=1
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/core/notifications/send/', {
            'student_ids': str(self.student.pk),
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertIn('Email quota exceeded', data['error'])
    
    @patch('core.views._send_email_notification', side_effect=Exception('SMTP Error'))
    def test_notification_sending_error_handling(self, mock_send):
        """Test error handling when notification sending fails"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post('/core/notifications/send/', {
            'student_ids': str(self.student.pk),
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message'
        })
        
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])  # Should still succeed overall
        self.assertEqual(data['results']['email_sent'], 0)
        self.assertEqual(len(data['results']['errors']), 1)
        self.assertIn('SMTP Error', data['results']['errors'][0])
        
        # Quota should not be consumed for failed sends
        email_quota = NotificationQuota.get_current_quota('email')
        self.assertEqual(email_quota.used_count, 0)
