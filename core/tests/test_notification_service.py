from decimal import Decimal

from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Staff
from academics.models import Course
from core.models import OrganisationSettings
from core.services.notification_service import NotificationService
from enrollment.models import Enrollment
from students.models import Student


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@perthartschool.com.au',
    SITE_DOMAIN='edupulse.perthartschool.com.au',
    SITE_PROTOCOL='https',
)
class NotificationServiceDomainResolutionTest(TestCase):
    def setUp(self):
        self.org_settings = OrganisationSettings.get_instance()
        self.org_settings.site_domain = 'perthartschool.com.au'
        self.org_settings.contact_email = 'info@perthartschool.com.au'
        self.org_settings.contact_phone = '(08) 9000 0000'
        self.org_settings.reply_to_email = 'info@perthartschool.com.au'
        self.org_settings.save()

        self.site = Site.objects.get_current()
        self.site.domain = 'example.com'
        self.site.name = 'example.com'
        self.site.save()

        self.course = Course.objects.create(
            name='Drawing Fundamentals',
            short_description='Introduction to drawing',
            price=Decimal('150.00'),
            status='draft',
            start_date=timezone.now().date(),
            start_time=timezone.now().time().replace(second=0, microsecond=0),
        )
        self.student = Student.objects.create(
            first_name='Ava',
            last_name='Jones',
            guardian_name='Casey Jones',
            contact_email='parent@test.com',
            contact_phone='0412345678',
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='confirmed',
            source_channel='website',
            course_fee=Decimal('150.00'),
            registration_fee=Decimal('25.00'),
        )
        self.expected_enrollment_url = (
            'https://edupulse.perthartschool.com.au'
            f"{reverse('enrollment:enrollment_detail', args=[self.enrollment.id])}"
        )
        self.expected_parent_portal_url = 'https://edupulse.perthartschool.com.au/students/'

    def test_admin_notification_uses_app_domain_for_enrollment_link(self):
        Staff.objects.create_user(
            username='admin',
            email='admin@perthartschool.com.au',
            password='testpass123',
            role='admin',
        )

        sent = NotificationService.send_new_enrollment_admin_notification(self.enrollment)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.expected_enrollment_url, mail.outbox[0].body)
        self.assertNotIn('https://example.com', mail.outbox[0].body)
        self.assertIn(self.expected_enrollment_url, mail.outbox[0].alternatives[0][0])

    def test_confirmation_email_uses_public_website_domain_for_footer_links(self):
        sent = NotificationService.send_enrollment_confirmation(self.enrollment)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"https://{self.org_settings.site_domain}", mail.outbox[0].body)
        self.assertNotIn('https://example.com', mail.outbox[0].body)
        self.assertIn(
            f'href="https://{self.org_settings.site_domain}"',
            mail.outbox[0].alternatives[0][0],
        )

    def test_welcome_email_uses_app_domain_for_parent_portal_link(self):
        sent = NotificationService.send_welcome_email(self.enrollment)

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.expected_parent_portal_url, mail.outbox[0].body)
        self.assertIn(self.expected_parent_portal_url, mail.outbox[0].alternatives[0][0])
