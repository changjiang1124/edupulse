import os
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image


class TinyMCEUploadTests(TestCase):
    """Tests for the TinyMCE image upload endpoint."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='uploader',
            password='pass1234',
            email='uploader@example.com'
        )
        self.client.force_login(self.user)
        self.temp_media_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)

    def _make_image_file(self, fmt='JPEG'):
        """Create a small in-memory image file."""
        file_obj = BytesIO()
        Image.new('RGB', (10, 10), 'red').save(file_obj, fmt)
        file_obj.seek(0)
        return SimpleUploadedFile(f'test.{fmt.lower()}', file_obj.read(), content_type='image/jpeg')

    def test_upload_requires_post(self):
        url = reverse('core:tinymce_upload')
        with override_settings(
            DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
            STORAGES={
                'default': {
                    'BACKEND': 'django.core.files.storage.FileSystemStorage',
                },
                'staticfiles': {
                    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
                },
            },
            MEDIA_ROOT=self.temp_media_dir,
            MEDIA_URL='/media/'
        ):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_upload_rejects_non_image(self):
        url = reverse('core:tinymce_upload')
        bad_file = SimpleUploadedFile('bad.txt', b'not an image', content_type='text/plain')
        with override_settings(
            DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
            STORAGES={
                'default': {
                    'BACKEND': 'django.core.files.storage.FileSystemStorage',
                },
                'staticfiles': {
                    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
                },
            },
            MEDIA_ROOT=self.temp_media_dir,
            MEDIA_URL='/media/'
        ):
            response = self.client.post(url, {'file': bad_file})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_upload_saves_file_and_returns_location(self):
        url = reverse('core:tinymce_upload')
        image_file = self._make_image_file()

        with override_settings(
            DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
            STORAGES={
                'default': {
                    'BACKEND': 'django.core.files.storage.FileSystemStorage',
                },
                'staticfiles': {
                    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
                },
            },
            MEDIA_ROOT=self.temp_media_dir,
            MEDIA_URL='/media/'
        ):
            response = self.client.post(url, {'file': image_file})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('location', data)

        location = data['location']
        self.assertTrue(location.startswith('/media/'))

        # Verify file exists on disk
        relative_path = location.replace('/media/', '', 1)
        stored_path = os.path.join(self.temp_media_dir, relative_path)
        self.assertTrue(os.path.exists(stored_path), f"Expected uploaded file at {stored_path}")
