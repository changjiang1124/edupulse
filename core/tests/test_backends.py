from django.test import TestCase, override_settings
from django.core.mail import EmailMessage
from django.core import mail
from unittest.mock import patch, MagicMock
from core.models import EmailSettings
from core.backends import DynamicEmailBackend


class DynamicEmailBackendTest(TestCase):
    """Test cases for DynamicEmailBackend"""
    
    def setUp(self):
        """Set up test data"""
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
    
    @patch('core.backends.logger')
    def test_backend_uses_database_config(self, mock_logger):
        """Test that backend uses database configuration when available"""
        backend = DynamicEmailBackend()
        
        # Check that database config is used
        self.assertEqual(backend.host, 'smtp.gmail.com')
        self.assertEqual(backend.port, 587)
        self.assertEqual(backend.username, 'test@gmail.com')
        self.assertEqual(backend.password, 'test_password')
        self.assertTrue(backend.use_tls)
        
        # Check logging
        mock_logger.info.assert_called_once()
        self.assertIn('Google Workspace', mock_logger.info.call_args[0][0])
    
    @patch('core.backends.logger')
    @patch.dict('os.environ', {
        'SMTP_SERVER': 'test.smtp.com',
        'SMTP_PORT': '25',
        'SMTP_USERNAME': 'env@test.com',
        'SMTP_PASSWORD': 'env_password'
    })
    def test_backend_fallback_to_environment(self, mock_logger):
        """Test backend fallback to environment variables"""
        # Disable database config
        self.email_settings.is_active = False
        self.email_settings.save()
        
        backend = DynamicEmailBackend()
        
        # Check that environment config is used
        self.assertEqual(backend.host, 'test.smtp.com')
        self.assertEqual(backend.port, 25)
        self.assertEqual(backend.username, 'env@test.com')
        self.assertEqual(backend.password, 'env_password')
        
        # Check logging
        mock_logger.info.assert_called_once()
        self.assertIn('fallback', mock_logger.info.call_args[0][0])
    
    def test_add_reply_to_headers_with_configured_reply_to(self):
        """Test adding reply-to headers with configured reply-to email"""
        backend = DynamicEmailBackend()
        
        # Create test email message
        message = EmailMessage(
            subject='Test Subject',
            body='Test Body',
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        
        # Add reply-to headers
        config = self.email_settings
        backend._add_reply_to_headers([message], config)
        
        # Check that reply-to was added
        self.assertEqual(message.reply_to, ['reply@perthartschool.com.au'])
    
    def test_add_reply_to_headers_fallback_to_from_email(self):
        """Test reply-to fallback to from_email when no reply-to configured"""
        # Clear reply_to_email
        self.email_settings.reply_to_email = ''
        self.email_settings.save()
        
        backend = DynamicEmailBackend()
        
        message = EmailMessage(
            subject='Test Subject',
            body='Test Body',
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        
        backend._add_reply_to_headers([message], self.email_settings)
        
        # Should use from_email as reply-to
        self.assertEqual(message.reply_to, ['noreply@perthartschool.com.au'])
    
    def test_add_reply_to_headers_preserves_existing(self):
        """Test that existing reply-to headers are preserved"""
        backend = DynamicEmailBackend()
        
        message = EmailMessage(
            subject='Test Subject',
            body='Test Body',
            from_email='test@example.com',
            to=['recipient@example.com'],
            reply_to=['existing@example.com']
        )
        
        backend._add_reply_to_headers([message], self.email_settings)
        
        # Should preserve existing reply-to
        self.assertEqual(message.reply_to, ['existing@example.com'])
    
    @patch('core.models.EmailLog')
    def test_log_email_creation(self, mock_email_log):
        """Test email logging functionality"""
        backend = DynamicEmailBackend()
        
        message = EmailMessage(
            subject='Test Enrollment Confirmation',
            body='Welcome to our course!',
            from_email='test@example.com',
            to=['student@example.com']
        )
        
        backend._log_email(message, 'sent', self.email_settings)
        
        # Check that EmailLog.objects.create was called
        mock_email_log.objects.create.assert_called_once()
        call_kwargs = mock_email_log.objects.create.call_args.kwargs
        
        self.assertEqual(call_kwargs['recipient_email'], 'student@example.com')
        self.assertEqual(call_kwargs['subject'], 'Test Enrollment Confirmation')
        self.assertEqual(call_kwargs['status'], 'sent')
        self.assertEqual(call_kwargs['email_type'], 'enrollment_confirm')
    
    @patch('core.models.EmailLog')
    @patch('core.backends.logger')
    def test_log_email_error_handling(self, mock_logger, mock_email_log):
        """Test email logging error handling"""
        # Make EmailLog.objects.create raise an exception
        mock_email_log.objects.create.side_effect = Exception('Database error')
        
        backend = DynamicEmailBackend()
        
        message = EmailMessage(
            subject='Test Subject',
            body='Test Body',
            from_email='test@example.com',
            to=['recipient@example.com']
        )
        
        # Should not raise exception
        backend._log_email(message, 'sent', self.email_settings)
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        self.assertIn('Failed to log email', mock_logger.warning.call_args[0][0])


class EmailSettingsModelTest(TestCase):
    """Test cases for EmailSettings model"""
    
    def setUp(self):
        """Set up test data"""
        self.email_settings = EmailSettings.objects.create(
            email_backend_type='google_workspace',
            smtp_host='smtp.gmail.com',
            smtp_port=587,
            smtp_username='test@gmail.com',
            smtp_password='test_password',
            use_tls=True,
            from_email='noreply@test.com',
            from_name='Test School',
            reply_to_email='reply@test.com',
            is_active=True
        )
    
    def test_singleton_behavior(self):
        """Test that only one configuration can be active"""
        # Create another configuration
        second_config = EmailSettings.objects.create(
            email_backend_type='custom_smtp',
            smtp_host='mail.example.com',
            smtp_port=25,
            smtp_username='admin@example.com',
            smtp_password='password',
            from_email='admin@example.com',
            from_name='Example School',
            is_active=True  # This should deactivate the first one
        )
        
        # Refresh first configuration
        self.email_settings.refresh_from_db()
        
        # First configuration should be inactive now
        self.assertFalse(self.email_settings.is_active)
        self.assertTrue(second_config.is_active)
    
    def test_get_active_config(self):
        """Test getting active configuration"""
        active_config = EmailSettings.get_active_config()
        self.assertEqual(active_config.pk, self.email_settings.pk)
        self.assertTrue(active_config.is_active)
    
    def test_get_active_config_none_exists(self):
        """Test getting active config when none exists"""
        # Deactivate all configurations
        EmailSettings.objects.all().update(is_active=False)
        
        active_config = EmailSettings.get_active_config()
        self.assertIsNone(active_config)
    
    def test_google_workspace_validation(self):
        """Test Google Workspace specific validation"""
        # Test invalid Gmail address
        self.email_settings.smtp_username = 'invalid_email'
        
        with self.assertRaises(Exception):
            self.email_settings.full_clean()
    
    def test_str_representation(self):
        """Test string representation"""
        expected = 'Google Workspace (test@gmail.com)'
        self.assertEqual(str(self.email_settings), expected)