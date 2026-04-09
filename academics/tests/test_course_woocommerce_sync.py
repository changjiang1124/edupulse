from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academics.models import Course
from core.models import WooCommerceSyncLog


@override_settings(SECURE_SSL_REDIRECT=False, WOOCOMMERCE_SYNC_ENABLED=True)
class CourseWooCommerceSyncTests(TestCase):
    def setUp(self):
        signal_patcher = patch('academics.signals.WooCommerceSyncService')
        self.mock_signal_service = signal_patcher.start()
        self.addCleanup(signal_patcher.stop)

        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username='woo-admin',
            password='Admin123!',
            first_name='Woo',
            last_name='Admin',
            role='admin',
        )
        self.teacher = user_model.objects.create_user(
            username='woo-teacher',
            password='Teacher123!',
            first_name='Woo',
            last_name='Teacher',
            role='teacher',
        )

        self.client = Client()
        self.client.login(username='woo-admin', password='Admin123!')

    def create_course(self, **overrides):
        defaults = {
            'name': 'Woo Sync Course',
            'start_date': timezone.localdate(),
            'start_time': time(hour=10, minute=0),
            'duration_minutes': 60,
            'price': 120.00,
            'status': 'draft',
            'teacher': self.teacher,
        }
        defaults.update(overrides)
        return Course.objects.create(**defaults)

    def create_sync_log(self, course, **overrides):
        defaults = {
            'course': course,
            'sync_type': 'update',
            'status': 'success',
            'wc_product_id': course.external_id or '',
            'response_data': {'status': 'publish'},
            'request_data': {'status': course.status},
        }
        defaults.update(overrides)
        return WooCommerceSyncLog.objects.create(**defaults)

    def test_archive_view_warns_when_woocommerce_sync_fails(self):
        course = self.create_course(
            name='Archive Me',
            status='published',
            external_id='123',
        )
        self.mock_signal_service.reset_mock()

        with patch('academics.services.WooCommerceSyncService') as mock_sync_service:
            mock_sync_service.return_value.sync_course_to_woocommerce.return_value = {
                'status': 'error',
                'message': 'API unavailable',
            }

            response = self.client.post(
                reverse('academics:course_archive', kwargs={'pk': course.pk}),
                follow=True,
            )

        course.refresh_from_db()
        self.assertEqual(course.status, 'archived')
        self.assertEqual(mock_sync_service.return_value.sync_course_to_woocommerce.call_count, 1)
        self.mock_signal_service.assert_not_called()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn('Course "Archive Me" has been archived.', messages)
        self.assertIn(
            'WooCommerce sync failed: API unavailable. Local course changes were saved.',
            messages,
        )

    def test_archive_view_handles_woocommerce_service_initialisation_errors(self):
        course = self.create_course(
            name='Archive Init Error',
            status='published',
            external_id='321',
        )
        self.mock_signal_service.reset_mock()

        with patch('academics.services.WooCommerceSyncService', side_effect=ValueError('Missing WooCommerce API credentials')):
            response = self.client.post(
                reverse('academics:course_archive', kwargs={'pk': course.pk}),
                follow=True,
            )

        course.refresh_from_db()
        self.assertEqual(course.status, 'archived')
        self.mock_signal_service.assert_not_called()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn('Course "Archive Init Error" has been archived.', messages)
        self.assertIn(
            'WooCommerce sync failed: Missing WooCommerce API credentials. Local course changes were saved.',
            messages,
        )

    @override_settings(WOOCOMMERCE_SYNC_ENABLED=False)
    def test_archive_view_warns_when_woocommerce_sync_is_disabled(self):
        course = self.create_course(
            name='Archive Disabled Sync',
            status='published',
            external_id='654',
        )
        self.mock_signal_service.reset_mock()

        with patch('academics.services.WooCommerceSyncService') as mock_sync_service:
            response = self.client.post(
                reverse('academics:course_archive', kwargs={'pk': course.pk}),
                follow=True,
            )

        course.refresh_from_db()
        self.assertEqual(course.status, 'archived')
        mock_sync_service.assert_not_called()
        self.mock_signal_service.assert_not_called()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn('Course "Archive Disabled Sync" has been archived.', messages)
        self.assertIn(
            'WooCommerce sync failed: WooCommerce sync is disabled in this environment. Local course changes were saved.',
            messages,
        )

    def test_admin_bulk_publish_syncs_woocommerce(self):
        course_one = self.create_course(name='Draft Course One')
        course_two = self.create_course(name='Draft Course Two')
        self.mock_signal_service.reset_mock()

        with patch('academics.services.WooCommerceSyncService') as mock_sync_service:
            mock_sync_service.return_value.sync_course_to_woocommerce.return_value = {
                'status': 'success',
                'wc_product_id': '456',
            }

            response = self.client.post(
                reverse('admin:academics_course_changelist'),
                {
                    'action': 'publish_courses',
                    '_selected_action': [str(course_one.pk), str(course_two.pk)],
                    'index': '0',
                },
                follow=True,
            )

        course_one.refresh_from_db()
        course_two.refresh_from_db()
        self.assertEqual(course_one.status, 'published')
        self.assertEqual(course_two.status, 'published')
        self.assertEqual(mock_sync_service.return_value.sync_course_to_woocommerce.call_count, 2)
        self.mock_signal_service.assert_not_called()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn(
            '2 course(s) were successfully published. WooCommerce synced 2 course(s).',
            messages,
        )

    def test_admin_bulk_unpublish_reports_synced_and_skipped_courses(self):
        synced_course = self.create_course(
            name='Published Synced Course',
            status='published',
            external_id='789',
        )
        local_only_course = self.create_course(
            name='Published Local Course',
            status='published',
            external_id=None,
        )
        self.mock_signal_service.reset_mock()

        with patch('academics.services.WooCommerceSyncService') as mock_sync_service:
            mock_sync_service.return_value.sync_course_to_woocommerce.return_value = {
                'status': 'success',
                'wc_product_id': '789',
            }

            response = self.client.post(
                reverse('admin:academics_course_changelist'),
                {
                    'action': 'unpublish_courses',
                    '_selected_action': [str(synced_course.pk), str(local_only_course.pk)],
                    'index': '0',
                },
                follow=True,
            )

        synced_course.refresh_from_db()
        local_only_course.refresh_from_db()
        self.assertEqual(synced_course.status, 'draft')
        self.assertEqual(local_only_course.status, 'draft')
        self.assertEqual(mock_sync_service.return_value.sync_course_to_woocommerce.call_count, 1)
        self.mock_signal_service.assert_not_called()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn(
            '2 course(s) were successfully marked as draft. WooCommerce synced 1 course(s). WooCommerce sync was not required for 1 course(s).',
            messages,
        )

    def test_course_detail_shows_last_known_woocommerce_state_and_failed_sync(self):
        course = self.create_course(
            name='Detail Woo Course',
            status='published',
            external_id='991',
        )
        sync_time = timezone.now() - timedelta(hours=2)
        Course.objects.filter(pk=course.pk).update(woocommerce_last_synced_at=sync_time)
        course.refresh_from_db()
        self.create_sync_log(
            course,
            status='success',
            completed_at=sync_time,
            response_data={'status': 'publish'},
        )
        self.create_sync_log(
            course,
            status='failed',
            error_message='Request timed out',
            response_data={},
        )

        response = self.client.get(reverse('academics:course_detail', kwargs={'pk': course.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WooCommerce Sync')
        self.assertContains(response, 'Sync failed')
        self.assertContains(response, 'Last known WooCommerce status')
        self.assertContains(response, 'Published')
        self.assertContains(response, 'Last sync attempt failed')
        self.assertContains(response, 'Request timed out')
        self.assertContains(response, '991')

    def test_course_list_shows_woocommerce_sync_summary(self):
        course = self.create_course(
            name='List Woo Course',
            status='published',
            external_id='551',
        )
        sync_time = timezone.now() - timedelta(minutes=30)
        Course.objects.filter(pk=course.pk).update(woocommerce_last_synced_at=sync_time)
        course.refresh_from_db()
        self.create_sync_log(
            course,
            status='success',
            completed_at=sync_time,
            response_data={'status': 'publish'},
        )

        response = self.client.get(reverse('academics:course_list'), {'status': 'published'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Woo: Published')
        self.assertContains(response, 'Synced')
        self.assertContains(response, 'Last sync')
