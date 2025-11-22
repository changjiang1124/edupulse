from django.test import TestCase
from unittest.mock import patch

class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class SenderResolutionTest(TestCase):
    def test_uses_emailsettings_when_available(self):
        with patch('core.models.EmailSettings.get_active_config', return_value=Dummy(from_email='noreply@org.com', reply_to_email='reply@org.com')):
            from core.services.notification_service import NotificationService
            sender_from, sender_reply = NotificationService._get_sender()
            self.assertEqual(sender_from, 'noreply@org.com')
            self.assertEqual(sender_reply, 'reply@org.com')

    def test_fallback_to_settings_and_org_reply(self):
        with patch('core.models.EmailSettings.get_active_config', return_value=None):
            from django.conf import settings
            from core.services.notification_service import NotificationService
            sender_from, sender_reply = NotificationService._get_sender()
            self.assertEqual(sender_from, settings.DEFAULT_FROM_EMAIL)
            self.assertTrue(len(sender_reply) > 0)