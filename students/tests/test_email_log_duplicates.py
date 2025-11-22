from django.test import TestCase, override_settings
from unittest.mock import patch


class EmailLogDuplicateAvoidTest(TestCase):
    @override_settings(EMAIL_LOG_VIA_BACKEND_ONLY=True)
    def test_batch_service_skips_manual_logging(self):
        from core.services.batch_email_service import BatchEmailService

        service = BatchEmailService(batch_size=1, batch_delay=0)

        email_data = [{
            'to': 'recipient@test.com',
            'subject': 'Test',
            'context': {},
            'template_name': 'core/emails/enrollment_confirmation.html'
        }]

        with patch.object(BatchEmailService, '_log_email_success') as log_success:
            with patch.object(BatchEmailService, '_log_email_failure') as log_failure:
                with patch('django.core.mail.get_connection') as get_conn:
                    def run_test():
                        class DummyConn:
                            def __init__(self):
                                self.connection = self
                            def open(self):
                                return True
                            def close(self):
                                return True
                            def noop(self):
                                return (250, b'OK')
                            def send_messages(self, msgs):
                                return 1
                        get_conn.return_value = DummyConn()
                        stats = service.send_bulk_emails(email_data)
                        self.assertEqual(stats['sent'], 1)
                        log_success.assert_not_called()
                        log_failure.assert_not_called()
                    run_test()