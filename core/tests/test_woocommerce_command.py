from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings


class TestWooCommerceCommandSafetyTests(TestCase):
    @override_settings(WOOCOMMERCE_SYNC_ENABLED=False)
    def test_create_test_course_requires_explicit_write_opt_in(self):
        with self.assertRaises(CommandError) as cm:
            call_command('test_woocommerce', '--create-test-course', stdout=StringIO())

        self.assertIn('--allow-write', str(cm.exception))

    @override_settings(WOOCOMMERCE_SYNC_ENABLED=False)
    def test_create_test_course_refuses_when_sync_is_disabled(self):
        with self.assertRaises(CommandError) as cm:
            call_command(
                'test_woocommerce',
                '--create-test-course',
                '--allow-write',
                stdout=StringIO(),
            )

        self.assertIn('WOOCOMMERCE_SYNC_ENABLED=True', str(cm.exception))
