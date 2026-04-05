import os
import shutil
import tempfile
from pathlib import Path
import time
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from students.models import Student
from unittest.mock import patch


class BulkNotificationFlowTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', password='pass123', role='admin')
        self.client.login(username='admin', password='pass123')
        self.temp_media_dir = tempfile.mkdtemp()
        self.media_override = self.settings(
            MEDIA_ROOT=self.temp_media_dir,
            SECURE_SSL_REDIRECT=False,
            SESSION_COOKIE_SECURE=False,
            CSRF_COOKIE_SECURE=False,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(lambda: shutil.rmtree(self.temp_media_dir, ignore_errors=True))

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
            'email_content': '<p>Hello students</p>',
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

    def test_start_execute_progress_with_pdf_attachments(self):
        start_url = reverse('students:bulk_notification_start')
        payload = {
            'send_to': 'selected',
            'student_ids': f'{self.s1.id},{self.s2.id}',
            'notification_type': 'email',
            'message_type': 'general',
            'subject': 'Bulk Test With PDF',
            'email_content': '<p>Hello with attachment</p>',
            'pdf_attachments': [
                SimpleUploadedFile(
                    'family-info.pdf',
                    b'%PDF-1.4 test pdf',
                    content_type='application/pdf'
                ),
                SimpleUploadedFile(
                    'pricing-sheet.pdf',
                    b'%PDF-1.4 pricing pdf',
                    content_type='application/pdf'
                ),
            ],
        }

        resp = self.client.post(start_url, data=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        task_id = data['task_id']

        captured = {}

        def fake_send(email_data_list):
            captured['emails'] = email_data_list
            return {'sent': 2, 'failed': 0, 'batches': 1}

        execute_url = reverse('students:bulk_notification_execute', kwargs={'task_id': task_id})
        with patch('core.services.batch_email_service.BatchEmailService.send_bulk_emails', side_effect=fake_send):
            exec_resp = self.client.post(execute_url)
            self.assertEqual(exec_resp.status_code, 200)
            self.assertTrue(exec_resp.json()['success'])

        self.assertEqual(len(captured['emails']), 2)
        attachments = captured['emails'][0]['attachments']
        self.assertEqual(len(attachments), 2)
        self.assertEqual(attachments[0]['filename'], 'family-info.pdf')
        self.assertEqual(attachments[0]['mimetype'], 'application/pdf')
        self.assertEqual(attachments[0]['content'], b'%PDF-1.4 test pdf')
        self.assertEqual(attachments[1]['filename'], 'pricing-sheet.pdf')
        self.assertEqual(attachments[1]['content'], b'%PDF-1.4 pricing pdf')

        attachment_dir = Path(self.temp_media_dir) / 'notification_attachments'
        if attachment_dir.exists():
            self.assertEqual(list(attachment_dir.iterdir()), [])

    def test_start_cleans_up_stale_notification_attachments(self):
        from students.views import _cleanup_stale_notification_attachments

        attachment_dir = Path(self.temp_media_dir) / 'notification_attachments'
        attachment_dir.mkdir(parents=True, exist_ok=True)
        stale_file = attachment_dir / 'stale.pdf'
        stale_file.write_bytes(b'%PDF-1.4 stale')

        old_timestamp = time.time() - (7 * 60 * 60)
        os.utime(stale_file, (old_timestamp, old_timestamp))

        _cleanup_stale_notification_attachments()

        self.assertFalse(stale_file.exists())
