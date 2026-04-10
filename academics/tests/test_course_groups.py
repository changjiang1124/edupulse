from datetime import date, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from academics.models import Class, Course, CourseGroup
from academics.services import CourseGroupCreationService, CourseStatusService, CourseWooCommerceService
from facilities.models import Classroom, Facility


@override_settings(SECURE_SSL_REDIRECT=False)
class CourseGroupTests(TestCase):
    def setUp(self):
        signal_patcher = patch('academics.signals.WooCommerceSyncService')
        self.mock_signal_service = signal_patcher.start()
        self.addCleanup(signal_patcher.stop)

        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='group-admin',
            password='Admin123!',
            first_name='Group',
            last_name='Admin',
            role='admin',
        )
        self.teacher = user_model.objects.create_user(
            username='group-teacher',
            password='Teacher123!',
            first_name='Template',
            last_name='Teacher',
            role='teacher',
        )
        self.client = Client()
        self.client.login(username='group-admin', password='Admin123!')

    def create_group(self, **overrides):
        defaults = {
            'name': 'Protege Studio',
            'slug': 'protege-studio',
            'status': 'published',
            'short_description': 'Shared course group copy.',
            'description': '<p>Shared group description.</p>',
            'category': 'term_courses',
            'course_type': 'group',
            'repeat_pattern': 'weekly',
            'price': 899,
            'registration_fee': 160,
            'early_bird_price': 799,
            'early_bird_deadline': date(2026, 5, 1),
        }
        defaults.update(overrides)
        return CourseGroup.objects.create(**defaults)

    def create_standalone_course(self, **overrides):
        defaults = {
            'name': 'Standalone Course',
            'start_date': date(2026, 5, 5),
            'end_date': date(2026, 6, 30),
            'repeat_pattern': 'weekly',
            'repeat_weekday': 1,
            'start_time': time(15, 0),
            'duration_minutes': 120,
            'price': 500,
            'status': 'published',
            'teacher': self.teacher,
        }
        defaults.update(overrides)
        return Course.objects.create(**defaults)

    def create_child_course(self, group, **overrides):
        defaults = {
            'group': group,
            'short_description': group.short_description,
            'description': group.description,
            'category': group.category,
            'course_type': group.course_type,
            'repeat_pattern': group.repeat_pattern,
            'price': group.price,
            'registration_fee': group.registration_fee,
            'early_bird_price': group.early_bird_price,
            'early_bird_deadline': group.early_bird_deadline,
            'start_date': date(2026, 5, 6),
            'end_date': date(2026, 7, 1),
            'repeat_weekday': 2,
            'start_time': time(16, 0),
            'duration_minutes': 120,
            'status': 'draft',
            'teacher': self.teacher,
        }
        defaults.update(overrides)
        return Course.objects.create(**defaults)

    def build_group_update_payload(self, group, **overrides):
        payload = {
            'name': group.name,
            'slug': group.slug,
            'status': group.status,
            'short_description': group.short_description,
            'description': group.description,
            'course_type': group.course_type,
            'price': str(group.price),
            'registration_fee': '' if group.registration_fee is None else str(group.registration_fee),
            'early_bird_price': '' if group.early_bird_price is None else str(group.early_bird_price),
            'early_bird_deadline': (
                group.early_bird_deadline.isoformat() if group.early_bird_deadline else ''
            ),
            'sync_published_children': '0',
        }
        payload.update(overrides)
        return payload

    def test_teacher_cannot_access_course_group_management_views(self):
        group = self.create_group()
        teacher_client = Client()
        teacher_client.login(username='group-teacher', password='Teacher123!')

        group_list_response = teacher_client.get(reverse('academics:course_group_list'))
        group_detail_response = teacher_client.get(reverse('academics:course_group_detail', kwargs={'pk': group.pk}))
        create_child_response = teacher_client.get(reverse('academics:course_add_from_group', kwargs={'group_pk': group.pk}))

        self.assertEqual(group_list_response.status_code, 403)
        self.assertEqual(group_detail_response.status_code, 403)
        self.assertEqual(create_child_response.status_code, 403)

    def test_standalone_course_list_excludes_group_children(self):
        group = self.create_group()
        child_course = self.create_child_course(group)
        standalone_course = self.create_standalone_course()

        response = self.client.get(reverse('academics:course_list'), {'status': 'all'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, standalone_course.name)
        self.assertNotContains(response, child_course.name)

    def test_course_group_list_displays_child_courses(self):
        group = self.create_group()
        child_course = self.create_child_course(group)

        response = self.client.get(reverse('academics:course_group_list'), {'status': 'all'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, group.name)
        self.assertContains(response, child_course.name)

    def test_create_child_course_from_group_copies_group_snapshot(self):
        group = self.create_group()

        response = self.client.post(
            reverse('academics:course_add_from_group', kwargs={'group_pk': group.pk}),
            {
                'start_date': '2026-05-06',
                'end_date': '2026-07-01',
                'repeat_pattern': 'weekly',
                'repeat_weekday': '2',
                'start_time': '16:00',
                'duration_minutes': '120',
                'vacancy': '10',
                'teacher': str(self.teacher.pk),
                'status': 'draft',
                'is_online_bookable': 'on',
                'generate_classes': 'on',
            },
            follow=True,
        )

        child_course = Course.objects.get(group=group)

        self.assertRedirects(response, reverse('academics:course_group_detail', kwargs={'pk': group.pk}))
        self.assertEqual(child_course.group_id, group.pk)
        self.assertEqual(child_course.price, group.price)
        self.assertEqual(child_course.registration_fee, group.registration_fee)
        self.assertEqual(child_course.short_description, group.short_description)
        self.assertTrue(child_course.name.startswith(group.name))
        self.assertFalse(CourseWooCommerceService.should_sync(child_course))

    def test_group_child_edit_form_renders_description_as_read_only(self):
        group = self.create_group(description='<p>Group content</p>')
        child_course = self.create_child_course(
            group,
            short_description='Frozen child short description.',
            description='<p>Frozen child content</p>',
        )

        response = self.client.get(reverse('academics:course_edit', kwargs={'pk': child_course.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shared Course Group Content')
        self.assertContains(response, 'Inherited from Course Group')
        self.assertContains(response, 'Frozen child short description.')
        self.assertContains(response, 'Frozen child content')
        self.assertNotContains(response, 'id="id_short_description"')
        self.assertNotContains(response, 'id="id_description"')

    def test_group_update_without_sync_keeps_current_child_snapshots_and_future_children_inherit_new_values(self):
        group = self.create_group(
            short_description='Original shared short description.',
            description='<p>Original shared description.</p>',
            price=899,
        )
        published_child = self.create_child_course(
            group,
            status='published',
            short_description='Original child short description.',
            description='<p>Original child description.</p>',
            price=899,
            is_online_bookable=True,
            bookable_state='bookable',
        )

        response = self.client.post(
            reverse('academics:course_group_edit', kwargs={'pk': group.pk}),
            self.build_group_update_payload(
                group,
                short_description='Updated group short description.',
                description='<p>Updated group description.</p>',
                price='950.00',
                sync_published_children='0',
            ),
            follow=True,
        )

        self.assertRedirects(response, reverse('academics:course_group_detail', kwargs={'pk': group.pk}))

        group.refresh_from_db()
        published_child.refresh_from_db()

        self.assertEqual(group.short_description, 'Updated group short description.')
        self.assertEqual(group.description, '<p>Updated group description.</p>')
        self.assertEqual(str(group.price), '950.00')

        self.assertEqual(published_child.short_description, 'Original child short description.')
        self.assertEqual(published_child.description, '<p>Original child description.</p>')
        self.assertEqual(str(published_child.price), '899.00')

        future_child = Course()
        CourseGroupCreationService.build_child_from_group(group=group, course=future_child)
        self.assertEqual(future_child.short_description, 'Updated group short description.')
        self.assertEqual(future_child.description, '<p>Updated group description.</p>')
        self.assertEqual(str(future_child.price), '950.00')

    def test_group_update_with_sync_updates_only_published_children(self):
        group = self.create_group(
            name='Original Group Name',
            short_description='Original shared short description.',
            description='<p>Original shared description.</p>',
            price=899,
        )
        published_child = self.create_child_course(
            group,
            status='published',
            short_description='Published child short description.',
            description='<p>Published child description.</p>',
            price=899,
            is_online_bookable=True,
            bookable_state='bookable',
        )
        draft_child = self.create_child_course(
            group,
            status='draft',
            repeat_weekday=4,
            start_time=time(17, 0),
            short_description='Draft child short description.',
            description='<p>Draft child description.</p>',
            price=899,
        )

        response = self.client.post(
            reverse('academics:course_group_edit', kwargs={'pk': group.pk}),
            self.build_group_update_payload(
                group,
                name='Updated Group Name',
                short_description='Updated group short description.',
                description='<p>Updated group description.</p>',
                price='960.00',
                sync_published_children='1',
            ),
            follow=True,
        )

        self.assertRedirects(response, reverse('academics:course_group_detail', kwargs={'pk': group.pk}))

        published_child.refresh_from_db()
        draft_child.refresh_from_db()

        self.assertEqual(published_child.short_description, 'Updated group short description.')
        self.assertEqual(published_child.description, '<p>Updated group description.</p>')
        self.assertEqual(str(published_child.price), '960.00')
        self.assertTrue(published_child.name.startswith('Updated Group Name | '))

        self.assertEqual(draft_child.short_description, 'Draft child short description.')
        self.assertEqual(draft_child.description, '<p>Draft child description.</p>')
        self.assertEqual(str(draft_child.price), '899.00')

    def test_group_update_with_sync_does_not_modify_existing_classes(self):
        group = self.create_group(
            name='Original Group Name',
            short_description='Original shared short description.',
            description='<p>Original shared description.</p>',
            price=899,
        )
        published_child = self.create_child_course(
            group,
            status='published',
            short_description='Published child short description.',
            description='<p>Published child description.</p>',
            price=899,
            is_online_bookable=True,
            bookable_state='bookable',
        )
        facility = Facility.objects.create(
            name='Review Facility',
            address='100 Review Street, Perth WA',
            phone='08 6111 1111',
            email='review-facility@example.com',
        )
        classroom = Classroom.objects.create(
            facility=facility,
            name='Room 1',
            capacity=12,
        )
        class_instance = Class.objects.create(
            course=published_child,
            date=date(2026, 5, 20),
            start_time=time(16, 0),
            duration_minutes=120,
            teacher=self.teacher,
            facility=facility,
            classroom=classroom,
        )

        response = self.client.post(
            reverse('academics:course_group_edit', kwargs={'pk': group.pk}),
            self.build_group_update_payload(
                group,
                name='Updated Group Name',
                short_description='Updated group short description.',
                description='<p>Updated group description.</p>',
                price='960.00',
                sync_published_children='1',
            ),
            follow=True,
        )

        self.assertRedirects(response, reverse('academics:course_group_detail', kwargs={'pk': group.pk}))

        published_child.refresh_from_db()
        class_instance.refresh_from_db()

        self.assertEqual(published_child.short_description, 'Updated group short description.')
        self.assertEqual(published_child.description, '<p>Updated group description.</p>')
        self.assertEqual(str(published_child.price), '960.00')
        self.assertEqual(class_instance.date, date(2026, 5, 20))
        self.assertEqual(class_instance.start_time, time(16, 0))
        self.assertEqual(class_instance.duration_minutes, 120)
        self.assertEqual(class_instance.teacher_id, self.teacher.pk)
        self.assertEqual(class_instance.facility_id, facility.pk)
        self.assertEqual(class_instance.classroom_id, classroom.pk)

    def test_group_edit_modal_explains_classes_are_not_changed(self):
        group = self.create_group(status='published')
        self.create_child_course(group, status='published')

        response = self.client.get(reverse('academics:course_group_edit', kwargs={'pk': group.pk}))

        self.assertContains(response, 'Existing classes will not be changed.')
        self.assertContains(response, 'edit the child course itself and use its class update controls')

    def test_group_detail_explains_child_course_owns_schedule_and_class_updates(self):
        group = self.create_group(status='published')
        self.create_child_course(group, status='published')

        response = self.client.get(reverse('academics:course_group_detail', kwargs={'pk': group.pk}))

        self.assertContains(response, 'Shared content is managed in the Course Group.')
        self.assertContains(response, 'Scheduling and existing class updates are managed from each child course.')

    def test_course_group_delete_post_is_blocked_when_children_exist(self):
        group = self.create_group()
        self.create_child_course(group)

        response = self.client.post(
            reverse('academics:course_group_delete', kwargs={'pk': group.pk}),
            follow=True,
        )

        self.assertRedirects(response, reverse('academics:course_group_detail', kwargs={'pk': group.pk}))
        self.assertTrue(CourseGroup.objects.filter(pk=group.pk).exists())

    def test_course_delete_post_still_blocks_published_courses(self):
        course = self.create_standalone_course(status='published')

        response = self.client.post(
            reverse('academics:course_delete', kwargs={'pk': course.pk}),
            follow=True,
        )

        self.assertRedirects(response, reverse('academics:course_list'))
        course.refresh_from_db()
        self.assertEqual(course.status, 'published')

    def test_public_group_detail_and_public_enrolment_hide_non_enrollable_courses(self):
        group = self.create_group(status='published')
        bookable_course = self.create_child_course(
            group,
            status='published',
            is_online_bookable=True,
            bookable_state='bookable',
            enrollment_deadline=timezone.localdate() + timedelta(days=7),
            start_date=timezone.localdate() + timedelta(days=14),
            end_date=timezone.localdate() + timedelta(days=70),
        )
        closed_course = self.create_child_course(
            group,
            status='published',
            is_online_bookable=True,
            bookable_state='closed',
            enrollment_deadline=timezone.localdate() + timedelta(days=7),
            start_date=timezone.localdate() + timedelta(days=14),
            end_date=timezone.localdate() + timedelta(days=70),
            repeat_weekday=3,
            start_time=time(17, 0),
        )
        deadline_passed_course = self.create_standalone_course(
            name='Deadline Passed Course',
            is_online_bookable=True,
            bookable_state='bookable',
            enrollment_deadline=timezone.localdate() - timedelta(days=1),
            start_date=timezone.localdate() + timedelta(days=14),
            end_date=timezone.localdate() + timedelta(days=70),
        )

        self.client.logout()
        group_public_response = self.client.get(
            reverse('academics:course_group_public_detail', kwargs={'slug': group.slug})
        )
        enrollment_response = self.client.get(reverse('enrollment:public_enrollment'))

        self.assertContains(group_public_response, bookable_course.get_instance_time_display())
        self.assertNotContains(group_public_response, closed_course.get_instance_time_display())

        public_courses = list(enrollment_response.context['courses'])
        self.assertIn(bookable_course, public_courses)
        self.assertNotIn(closed_course, public_courses)
        self.assertNotIn(deadline_passed_course, public_courses)

    def test_child_courses_are_included_in_expiry_updates(self):
        group = self.create_group(status='published')
        child_course = self.create_child_course(
            group,
            status='draft',
            start_date=timezone.localdate() - timedelta(days=70),
            end_date=timezone.localdate() - timedelta(days=7),
            enrollment_deadline=timezone.localdate() - timedelta(days=30),
        )
        Course.objects.filter(pk=child_course.pk).update(status='published')

        result = CourseStatusService.update_expired_courses()

        child_course.refresh_from_db()
        self.assertEqual(child_course.status, 'expired')
        self.assertEqual(result['updated'], 1)
