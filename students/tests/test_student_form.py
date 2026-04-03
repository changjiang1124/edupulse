from django.test import TestCase

from students.forms import StudentForm
from students.models import Student


class StudentFormTest(TestCase):
    def test_create_form_preserves_active_default_for_new_students(self):
        form = StudentForm(data={
            'first_name': 'Test',
            'last_name': 'Student',
        })

        self.assertNotIn('is_active', form.fields)
        self.assertTrue(form.is_valid(), form.errors)

        student = form.save()

        self.assertTrue(student.is_active)

    def test_edit_form_keeps_active_toggle(self):
        student = Student.objects.create(first_name='Eva', last_name='Russell')

        form = StudentForm(instance=student)

        self.assertIn('is_active', form.fields)

    def test_minor_requires_guardian_name(self):
        form = StudentForm(data={
            'first_name': 'Eva',
            'last_name': 'Russell',
            'birth_date': '2012-04-03',
            'guardian_name': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('guardian_name', form.errors)

    def test_invalid_fields_are_marked_for_rendering(self):
        form = StudentForm(data={
            'first_name': 'Eva',
            'last_name': 'Russell',
            'contact_email': 'not-an-email',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('is-invalid', form.fields['contact_email'].widget.attrs['class'])
        self.assertEqual(form.fields['contact_email'].widget.attrs['aria-invalid'], 'true')
