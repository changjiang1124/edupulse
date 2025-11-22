from django.test import TestCase
from unittest.mock import patch


class BatchSenderResolutionTest(TestCase):
    def test_prepare_email_uses_emailsettings_sender(self):
        from core.services.batch_email_service import BatchEmailService
        service = BatchEmailService()

        email_data = {
            'to': 'recipient@test.com',
            'subject': 'Subject',
            'context': {},
            'template_name': 'core/emails/enrollment_confirmation.html'
        }

        class Dummy:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        with patch('core.models.EmailSettings.get_active_config', return_value=Dummy(from_email='noreply@org.com', reply_to_email='reply@org.com')):
            email = service._prepare_email(email_data)
            self.assertEqual(email.from_email, 'noreply@org.com')
            self.assertEqual(email.reply_to, ['reply@org.com'])