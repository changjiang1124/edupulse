import re

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse

from .articles import ARTICLES


@override_settings(SECURE_SSL_REDIRECT=False)
class HelpCentreTests(TestCase):
    def setUp(self):
        self.teacher = get_user_model().objects.create_user(
            username='help-teacher', password='Teacher123!', first_name='Help', last_name='Teacher',
            role='teacher', is_active=True, is_active_staff=True,
        )

    def test_help_centre_requires_login(self):
        response = self.client.get(reverse('help_centre:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_index_lists_every_guide_in_order(self):
        self.client.login(username='help-teacher', password='Teacher123!')
        response = self.client.get(reverse('help_centre:index'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        positions = [content.index(article.title) for article in ARTICLES]
        self.assertEqual(positions, sorted(positions))

    def test_every_article_renders_and_its_screenshots_exist(self):
        self.client.login(username='help-teacher', password='Teacher123!')

        for article in ARTICLES:
            with self.subTest(article=article.slug):
                response = self.client.get(reverse('help_centre:article', args=[article.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, article.title)

                images = re.findall(r'src="/static/(help_centre/img/[^"]+)"', response.content.decode())
                self.assertTrue(images, 'each guide should include screenshots')
                for image in images:
                    self.assertIsNotNone(finders.find(image), f'missing screenshot {image}')

    def test_unknown_article_returns_404(self):
        self.client.login(username='help-teacher', password='Teacher123!')
        response = self.client.get(reverse('help_centre:article', args=['does-not-exist']))
        self.assertEqual(response.status_code, 404)

    def test_navigation_shows_help_link(self):
        self.client.login(username='help-teacher', password='Teacher123!')
        response = self.client.get(reverse('clock'))
        self.assertContains(response, f'href="{reverse("help_centre:index")}"')
