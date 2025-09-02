"""
Django management command to test WooCommerce API connection and sync courses
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.woocommerce_api import WooCommerceSyncService, WooCommerceAPI
from academics.models import Course
import json


class Command(BaseCommand):
    help = 'Test WooCommerce API connection and sync courses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test WooCommerce API connection only',
        )
        parser.add_argument(
            '--sync-course',
            type=int,
            help='Sync specific course by ID',
        )
        parser.add_argument(
            '--sync-all',
            action='store_true',
            help='Sync all published courses',
        )
        parser.add_argument(
            '--list-products',
            action='store_true',
            help='List WooCommerce products',
        )
        parser.add_argument(
            '--create-test-course',
            action='store_true',
            help='Create a test course and sync to WooCommerce',
        )

    def handle(self, *args, **options):
        sync_service = WooCommerceSyncService()

        if options['test_connection']:
            self.test_connection(sync_service)
        elif options['sync_course']:
            self.sync_single_course(sync_service, options['sync_course'])
        elif options['sync_all']:
            self.sync_all_courses(sync_service)
        elif options['list_products']:
            self.list_products(sync_service)
        elif options['create_test_course']:
            self.create_test_course(sync_service)
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action. Use --help for options.')
            )

    def test_connection(self, sync_service):
        """Test WooCommerce API connection"""
        self.stdout.write('Testing WooCommerce API connection...')
        
        result = sync_service.test_api_connection()
        
        if result['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS('✓ WooCommerce API connection successful!')
            )
            if result.get('data'):
                self.stdout.write(f"WooCommerce version: {result['data'].get('environment', {}).get('version', 'Unknown')}")
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ WooCommerce API connection failed: {result["message"]}')
            )

    def sync_single_course(self, sync_service, course_id):
        """Sync a single course by ID"""
        try:
            course = Course.objects.get(id=course_id)
            self.stdout.write(f'Syncing course: {course.name}')
            
            result = sync_service.sync_course_to_woocommerce(course)
            
            if result['status'] == 'success':
                wc_product_id = result.get('wc_product_id') or course.external_id
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully synced course to WooCommerce (Product ID: {wc_product_id})')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to sync course: {result["message"]}')
                )
                
        except Course.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Course with ID {course_id} does not exist')
            )

    def sync_all_courses(self, sync_service):
        """Sync all published courses"""
        courses = Course.objects.filter(status='published')
        
        if not courses:
            self.stdout.write(
                self.style.WARNING('No published courses found to sync')
            )
            return

        self.stdout.write(f'Syncing {courses.count()} published courses...')
        
        success_count = 0
        for course in courses:
            self.stdout.write(f'Syncing: {course.name}')
            result = sync_service.sync_course_to_woocommerce(course)
            
            if result['status'] == 'success':
                success_count += 1
                wc_product_id = result.get('wc_product_id') or course.external_id
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Success (Product ID: {wc_product_id})')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed: {result["message"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Completed: {success_count}/{courses.count()} courses synced successfully')
        )

    def list_products(self, sync_service):
        """List WooCommerce products"""
        self.stdout.write('Fetching WooCommerce products...')
        
        result = sync_service.api.list_products(per_page=20)
        
        if result['status'] == 'success':
            products = result['data']
            if products:
                self.stdout.write(f'Found {len(products)} products:')
                for product in products:
                    status = product.get('status', 'unknown')
                    external_url = product.get('external_url', 'N/A')
                    self.stdout.write(
                        f'  - ID: {product["id"]} | Name: {product["name"]} | Status: {status} | URL: {external_url}'
                    )
            else:
                self.stdout.write('No products found')
        else:
            self.stdout.write(
                self.style.ERROR(f'Failed to fetch products: {result["message"]}')
            )

    def create_test_course(self, sync_service):
        """Create a test course and sync to WooCommerce"""
        from accounts.models import Staff
        
        # Try to get an admin staff member
        try:
            teacher = Staff.objects.filter(is_superuser=True).first()
        except:
            teacher = None

        # Create test course
        test_course = Course.objects.create(
            name=f'Test Course {timezone.now().strftime("%Y%m%d_%H%M%S")}',
            description='<p>This is a test course created for WooCommerce API testing.</p>',
            short_description='Test course for WooCommerce integration prototype',
            price=99.00,
            course_type='group',
            status='published',  # Published so it syncs to WooCommerce
            teacher=teacher,
            start_date=timezone.now().date(),
            start_time='10:00',
            duration_minutes=60,
            vacancy=10,
            is_online_bookable=True
        )

        self.stdout.write(f'Created test course: {test_course.name} (ID: {test_course.id})')

        # Sync to WooCommerce
        result = sync_service.sync_course_to_woocommerce(test_course)

        if result['status'] == 'success':
            wc_product_id = result.get('wc_product_id')
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully synced test course to WooCommerce (Product ID: {wc_product_id})')
            )
            self.stdout.write(f'Course enrollment URL will be: /enroll/?course={test_course.id}')
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed to sync test course: {result["message"]}')
            )

        return test_course