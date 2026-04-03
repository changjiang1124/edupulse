from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from students.models import Student
from students.views import StudentListView


class StudentListViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='pass123',
            role='admin',
        )
        self.factory = RequestFactory()

        self.active_student = Student.objects.create(
            first_name='Active',
            last_name='Student',
            is_active=True,
        )
        self.inactive_student = Student.objects.create(
            first_name='Inactive',
            last_name='Student',
            is_active=False,
        )
        self.inactive_test_student = Student.objects.create(
            first_name='Test',
            last_name='Hidden',
            is_active=False,
        )

    def test_student_list_defaults_to_active_students(self):
        request = self.factory.get(reverse('students:student_list'))
        request.user = self.user

        response = StudentListView.as_view()(request)
        students = list(response.context_data['students'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.active_student, students)
        self.assertNotIn(self.inactive_student, students)
        self.assertEqual(response.context_data['selected_status'], 'active')

    def test_student_list_can_filter_inactive_students(self):
        request = self.factory.get(reverse('students:student_list'), {'status': 'inactive'})
        request.user = self.user

        response = StudentListView.as_view()(request)
        students = list(response.context_data['students'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.inactive_student, students)
        self.assertIn(self.inactive_test_student, students)
        self.assertNotIn(self.active_student, students)
        self.assertEqual(response.context_data['selected_status'], 'inactive')

    def test_student_list_can_search_all_students_when_requested(self):
        request = self.factory.get(reverse('students:student_list'), {
            'status': 'all',
            'search': 'Test',
        })
        request.user = self.user

        response = StudentListView.as_view()(request)
        students = list(response.context_data['students'])

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.inactive_test_student, students)
        self.assertNotIn(self.active_student, students)
        self.assertEqual(response.context_data['selected_status'], 'all')
