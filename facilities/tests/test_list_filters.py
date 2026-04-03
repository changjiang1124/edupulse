from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from facilities.models import Classroom, Facility
from facilities.views import ClassroomListView, FacilityListView


class FacilityListViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='pass123',
            role='admin',
        )
        self.factory = RequestFactory()

        self.active_facility = Facility.objects.create(
            name='Active Studio',
            address='123 Active St',
            is_active=True,
        )
        self.inactive_facility = Facility.objects.create(
            name='Inactive Studio',
            address='456 Quiet St',
            is_active=False,
        )

    def test_facility_list_defaults_to_active_facilities(self):
        request = self.factory.get(reverse('facilities:facility_list'))
        request.user = self.user

        response = FacilityListView.as_view()(request)
        facilities = list(response.context_data['facilities'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.active_facility, facilities)
        self.assertNotIn(self.inactive_facility, facilities)
        self.assertEqual(response.context_data['selected_status'], 'active')

    def test_facility_list_can_filter_inactive_facilities(self):
        request = self.factory.get(reverse('facilities:facility_list'), {'status': 'inactive'})
        request.user = self.user

        response = FacilityListView.as_view()(request)
        facilities = list(response.context_data['facilities'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.inactive_facility, facilities)
        self.assertNotIn(self.active_facility, facilities)
        self.assertEqual(response.context_data['selected_status'], 'inactive')


class ClassroomListViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='pass123',
            role='admin',
        )
        self.factory = RequestFactory()

        self.active_facility = Facility.objects.create(
            name='North Campus',
            address='1 North Rd',
            is_active=True,
        )
        self.inactive_facility = Facility.objects.create(
            name='South Campus',
            address='2 South Rd',
            is_active=False,
        )
        self.active_classroom = Classroom.objects.create(
            facility=self.active_facility,
            name='Room A',
            capacity=12,
            is_active=True,
        )
        self.inactive_classroom = Classroom.objects.create(
            facility=self.inactive_facility,
            name='Room B',
            capacity=10,
            is_active=False,
        )

    def test_classroom_list_defaults_to_active_classrooms(self):
        request = self.factory.get(reverse('facilities:classroom_list'))
        request.user = self.user

        response = ClassroomListView.as_view()(request)
        classrooms = list(response.context_data['classrooms'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.active_classroom, classrooms)
        self.assertNotIn(self.inactive_classroom, classrooms)
        self.assertEqual(response.context_data['selected_status'], 'active')

    def test_classroom_list_can_filter_inactive_classrooms(self):
        request = self.factory.get(reverse('facilities:classroom_list'), {'status': 'inactive'})
        request.user = self.user

        response = ClassroomListView.as_view()(request)
        classrooms = list(response.context_data['classrooms'])
        facilities = list(response.context_data['facilities'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.inactive_classroom, classrooms)
        self.assertNotIn(self.active_classroom, classrooms)
        self.assertIn(self.inactive_facility, facilities)
        self.assertEqual(response.context_data['selected_status'], 'inactive')
