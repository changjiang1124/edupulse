from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.models import Staff
from accounts.views import StaffListView


@override_settings(SECURE_SSL_REDIRECT=False)
class StaffListViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='pass123',
            role='admin',
        )
        self.factory = RequestFactory()
        self.client = Client()

        self.active_staff = Staff.objects.create_user(
            username='active-teacher',
            password='pass123',
            first_name='Active',
            last_name='Teacher',
            role='teacher',
            is_active_staff=True,
        )
        self.inactive_staff = Staff.objects.create_user(
            username='inactive-teacher',
            password='pass123',
            first_name='Inactive',
            last_name='Teacher',
            role='teacher',
            is_active_staff=False,
        )

    def test_staff_list_defaults_to_active_staff(self):
        request = self.factory.get(reverse('accounts:staff_list'))
        request.user = self.user

        response = StaffListView.as_view()(request)
        staff_members = list(response.context_data['staff_list'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.active_staff, staff_members)
        self.assertNotIn(self.inactive_staff, staff_members)
        self.assertEqual(response.context_data['selected_status'], 'active')

    def test_staff_list_can_filter_inactive_staff(self):
        request = self.factory.get(reverse('accounts:staff_list'), {'status': 'inactive'})
        request.user = self.user

        response = StaffListView.as_view()(request)
        staff_members = list(response.context_data['staff_list'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.inactive_staff, staff_members)
        self.assertNotIn(self.active_staff, staff_members)
        self.assertEqual(response.context_data['selected_status'], 'inactive')

    def test_staff_list_can_search_all_staff_when_requested(self):
        request = self.factory.get(reverse('accounts:staff_list'), {
            'status': 'all',
            'search': 'Inactive',
        })
        request.user = self.user

        response = StaffListView.as_view()(request)
        staff_members = list(response.context_data['staff_list'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.inactive_staff, staff_members)
        self.assertNotIn(self.active_staff, staff_members)
        self.assertEqual(response.context_data['selected_status'], 'all')

    def test_staff_list_does_not_show_manual_timesheet_shortcut(self):
        self.client.login(username='admin', password='pass123')

        response = self.client.get(reverse('accounts:staff_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            reverse('accounts:staff_attendance_manual_entry', args=[self.active_staff.pk]),
        )
