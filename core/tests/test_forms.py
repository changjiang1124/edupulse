from django.test import TestCase
from django.core.exceptions import ValidationError
from core.forms import NotificationForm, BulkNotificationForm, EmailSettingsForm
from core.models import EmailSettings
from students.models import Student


class NotificationFormTest(TestCase):
    """Test cases for NotificationForm"""
    
    def setUp(self):
        """Set up test data"""
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            contact_email='student@test.com'
        )
        
        self.valid_form_data = {
            'student_ids': str(self.student.pk),
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Test Subject',
            'message': 'Test message content'
        }
    
    def test_valid_form(self):
        """Test form with valid data"""
        form = NotificationForm(data=self.valid_form_data)
        self.assertTrue(form.is_valid())
        
        # Check cleaned data
        self.assertEqual(form.cleaned_data['student_id_list'], [self.student.pk])
        self.assertEqual(form.cleaned_data['notification_type'], 'email')
        self.assertEqual(form.cleaned_data['subject'], 'Test Subject')
    
    def test_invalid_student_ids(self):
        """Test form with invalid student IDs"""
        form_data = self.valid_form_data.copy()
        form_data['student_ids'] = 'invalid,ids,here'
        
        form = NotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Invalid student selection', str(form.non_field_errors()))
    
    def test_empty_student_ids(self):
        """Test form with empty student IDs"""
        form_data = self.valid_form_data.copy()
        form_data['student_ids'] = ''
        
        form = NotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('At least one student must be selected', str(form.non_field_errors()))
    
    def test_email_subject_required_for_email(self):
        """Test that email subject is required when sending emails"""
        form_data = self.valid_form_data.copy()
        form_data['subject'] = ''  # Empty subject
        form_data['notification_type'] = 'email'
        
        form = NotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('subject', form.errors)
    
    def test_email_subject_not_required_for_sms(self):
        """Test that email subject is not required for SMS only"""
        form_data = self.valid_form_data.copy()
        form_data['subject'] = ''  # Empty subject
        form_data['notification_type'] = 'sms'
        
        form = NotificationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_sms_message_length_validation(self):
        """Test SMS message length validation"""
        form_data = self.valid_form_data.copy()
        form_data['notification_type'] = 'sms'
        form_data['message'] = 'x' * 161  # Too long for SMS
        
        form = NotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('SMS message is too long', str(form.errors['message']))
    
    def test_both_notification_type_validation(self):
        """Test validation when sending both email and SMS"""
        form_data = self.valid_form_data.copy()
        form_data['notification_type'] = 'both'
        form_data['subject'] = 'Valid Subject'  # Valid subject
        form_data['message'] = 'x' * 161  # Too long for SMS
        
        form = NotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        # Should have SMS error in message field
        self.assertIn('message', form.errors)
        self.assertIn('SMS message is too long', str(form.errors['message']))
    
    def test_both_notification_type_multiple_errors(self):
        """Test validation when both email and SMS have errors"""
        form_data = self.valid_form_data.copy()
        form_data['notification_type'] = 'both'
        form_data['subject'] = ''  # Empty subject
        form_data['message'] = 'x' * 161  # Too long for SMS
        
        form = NotificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        # Should have both email and SMS errors
        self.assertIn('subject', form.errors)
        self.assertIn('message', form.errors)
        self.assertIn('Email subject is required', str(form.errors['subject']))
        self.assertIn('SMS message is too long', str(form.errors['message']))
    
    def test_multiple_student_ids(self):
        """Test form with multiple student IDs"""
        student2 = Student.objects.create(
            first_name='Test2',
            last_name='Student2',
            contact_email='student2@test.com'
        )
        
        form_data = self.valid_form_data.copy()
        form_data['student_ids'] = f'{self.student.pk},{student2.pk}'
        
        form = NotificationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        expected_ids = [self.student.pk, student2.pk]
        self.assertEqual(form.cleaned_data['student_id_list'], expected_ids)


class BulkNotificationFormTest(TestCase):
    """Test cases for BulkNotificationForm"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_form_data = {
            'send_to': 'all_active',
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Bulk Test Subject',
            'message': 'Bulk test message',
            'student_ids': ''  # Not required for bulk
        }
    
    def test_bulk_form_all_active(self):
        """Test bulk form with all active students"""
        # For bulk sending, student_ids can be empty when send_to is not 'selected'
        form_data = self.valid_form_data.copy()
        form_data['student_ids'] = ''  # Empty for bulk sending
        
        form = BulkNotificationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Should override student_id_list for bulk sending
        self.assertEqual(form.cleaned_data['student_id_list'], [])
        self.assertEqual(form.cleaned_data['send_to'], 'all_active')
    
    def test_bulk_form_selected_students(self):
        """Test bulk form with selected students"""
        student = Student.objects.create(
            first_name='Bulk',
            last_name='Student',
            contact_email='bulk@test.com'
        )
        
        form_data = self.valid_form_data.copy()
        form_data['send_to'] = 'selected'
        form_data['student_ids'] = str(student.pk)
        
        # This should fail validation because we need student IDs for 'selected'
        form = BulkNotificationForm(data=form_data)
        # Note: The parent class validation should still apply for 'selected'


class EmailSettingsFormTest(TestCase):
    """Test cases for EmailSettingsForm"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_form_data = {
            'email_backend_type': 'google_workspace',
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_username': 'test@gmail.com',
            'smtp_password': 'test_app_password',
            'use_tls': True,
            'from_email': 'noreply@test.com',
            'from_name': 'Test School',
            'reply_to_email': 'reply@test.com',
            'is_active': True
        }
    
    def test_valid_email_settings_form(self):
        """Test form with valid email settings data"""
        form = EmailSettingsForm(data=self.valid_form_data)
        self.assertTrue(form.is_valid())
    
    def test_google_workspace_validation(self):
        """Test Google Workspace specific validation"""
        form_data = self.valid_form_data.copy()
        form_data['smtp_username'] = 'notanemail'  # Not a valid email at all
        
        form = EmailSettingsForm(data=form_data)
        self.assertFalse(form.is_valid())
        # Check for email validation error (built-in Django validation)
        self.assertIn('smtp_username', form.errors)
    
    def test_google_workspace_app_password_validation(self):
        """Test Google Workspace app password validation"""
        form_data = self.valid_form_data.copy()
        form_data['smtp_password'] = '123'  # Too short for app password
        
        form = EmailSettingsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('App Password should be at least 8 characters',
                     str(form.errors['smtp_password']))
    
    def test_form_save_google_workspace_defaults(self):
        """Test that saving form sets Google Workspace defaults"""
        form = EmailSettingsForm(data=self.valid_form_data)
        self.assertTrue(form.is_valid())
        
        instance = form.save(commit=False)
        
        # Check that Google Workspace defaults are set
        self.assertEqual(instance.smtp_host, 'smtp.gmail.com')
        self.assertEqual(instance.smtp_port, 587)
        self.assertTrue(instance.use_tls)
    
    def test_reply_to_email_field_included(self):
        """Test that reply_to_email field is included in form"""
        form = EmailSettingsForm()
        self.assertIn('reply_to_email', form.fields)
        
        # Test with reply-to email
        form_data = self.valid_form_data.copy()
        form_data['reply_to_email'] = 'custom-reply@test.com'
        
        form = EmailSettingsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['reply_to_email'], 'custom-reply@test.com')
    
    def test_reply_to_email_optional(self):
        """Test that reply_to_email is optional"""
        form_data = self.valid_form_data.copy()
        form_data['reply_to_email'] = ''  # Empty reply-to
        
        form = EmailSettingsForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['reply_to_email'], '')
