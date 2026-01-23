from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from students.models import Student
from unittest.mock import patch


class BulkNotificationFlowTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', password='pass123', role='admin')
        self.client.login(username='admin', password='pass123')

        # Create two students with contact emails
        self.s1 = Student.objects.create(
            first_name='Test', last_name='One', contact_email='changjiang1124+1@gmail.com'
        )
        self.s2 = Student.objects.create(
            first_name='Test', last_name='Two', contact_email='changjiang1124+2@gmail.com'
        )

    def test_start_execute_progress_email_only(self):
        start_url = reverse('students:bulk_notification_start')
        payload = {
            'send_to': 'selected',
            'student_ids': f'{self.s1.id},{self.s2.id}',
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Bulk Test',
            'message': 'Hello students',
        }

        # Start task
        resp = self.client.post(start_url, data=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        task_id = data['task_id']
        self.assertEqual(data['total_recipients'], 2)

        # Progress should exist and be in 'created' state initially
        progress_url = reverse('students:bulk_notification_progress', kwargs={'task_id': task_id})
        prog = self.client.get(progress_url)
        self.assertEqual(prog.status_code, 200)
        self.assertEqual(prog.json()['status'], 'created')

        # Execute with patched batch email sending (no real SMTP)
        execute_url = reverse('students:bulk_notification_execute', kwargs={'task_id': task_id})
        with patch('core.services.batch_email_service.BatchEmailService.send_bulk_emails', return_value={'sent': 2, 'failed': 0, 'batches': 1}):
            exec_resp = self.client.post(execute_url)
            self.assertEqual(exec_resp.status_code, 200)
            self.assertTrue(exec_resp.json()['success'])

        # Final progress should be completed
        final_prog = self.client.get(progress_url)
        self.assertEqual(final_prog.status_code, 200)
        self.assertEqual(final_prog.json()['status'], 'completed')
        self.assertEqual(final_prog.json()['sent_emails'], 2)
