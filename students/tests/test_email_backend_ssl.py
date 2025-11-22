from django.test import TestCase, override_settings
from unittest.mock import patch


class EmailBackendSSLPortTest(TestCase):
    def test_port_465_enables_ssl_disables_tls(self):
        with patch('core.backends.DynamicEmailBackend._get_active_config', return_value=None):
            with patch('os.getenv') as getenv:
                def fake_getenv(key, default=None):
                    mapping = {
                        'SMTP_SERVER': 'gsydm1075.siteground.biz',
                        'SMTP_PORT': '465',
                        'SMTP_USERNAME': 'noreply@example.com',
                        'SMTP_PASSWORD': 'secret',
                        'EMAIL_USE_SSL': 'False',
                        'EMAIL_USE_TLS': 'True',
                    }
                    return mapping.get(key, default)

                getenv.side_effect = fake_getenv

                from core.backends import DynamicEmailBackend
                backend = DynamicEmailBackend()

                self.assertEqual(backend.port, 465)
                self.assertTrue(backend.use_ssl)
                self.assertFalse(backend.use_tls)

    @override_settings(EMAIL_USE_SSL=False, EMAIL_USE_TLS=True, EMAIL_PORT=587)
    def test_port_587_enables_tls(self):
        with patch('core.backends.DynamicEmailBackend._get_active_config', return_value=None):
            with patch('os.getenv') as getenv:
                def fake_getenv(key, default=None):
                    mapping = {
                        'SMTP_SERVER': 'smtp.gmail.com',
                        'SMTP_PORT': '587',
                        'SMTP_USERNAME': 'noreply@example.com',
                        'SMTP_PASSWORD': 'secret',
                        'EMAIL_USE_SSL': 'False',
                        'EMAIL_USE_TLS': 'True',
                    }
                    return mapping.get(key, default)

                getenv.side_effect = fake_getenv

                from core.backends import DynamicEmailBackend
                backend = DynamicEmailBackend()

                self.assertEqual(backend.port, 587)
                self.assertFalse(backend.use_ssl)
                self.assertTrue(backend.use_tls)