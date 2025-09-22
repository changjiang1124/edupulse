import csv
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.exceptions import ValidationError
from academics.models import Course
from django.utils import timezone
from decimal import Decimal


class Command(BaseCommand):
    help = 'Generate term courses from TSV file with configurable term dates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='term4_enroll_2025/courses_term4_2025.tsv',
            help='Path to the TSV file containing course data (default: term4_enroll_2025/courses_term4_2025.tsv)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            default='2025-10-14',
            help='Term start date in YYYY-MM-DD format (default: 2025-10-14)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            default='2025-12-21',
            help='Term end date in YYYY-MM-DD format (default: 2025-12-21)'
        )
        parser.add_argument(
            '--term-name',
            type=str,
            default='Term 4 2025',
            help='Term name to include in course names (default: Term 4 2025)'
        )
        parser.add_argument(
            '--early-bird-days',
            type=int,
            default=14,
            help='Number of days before course start for early bird deadline (default: 14)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview courses without actually creating them'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing courses with the same term name before creating new ones'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        start_date = self.parse_date(options['start_date'])
        end_date = self.parse_date(options['end_date'])
        term_name = options['term_name']
        early_bird_days = options['early_bird_days']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No courses will be created'))

        # Validate dates
        if start_date >= end_date:
            raise CommandError('Start date must be before end date')

        self.stdout.write(f'Term: {term_name}')
        self.stdout.write(f'Date range: {start_date} to {end_date}')
        self.stdout.write(f'Early bird deadline: {early_bird_days} days before course start')

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.generate_courses(
                    file, start_date, end_date, term_name,
                    early_bird_days, dry_run, clear_existing
                )
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')
        except Exception as e:
            raise CommandError(f'Error reading file: {str(e)}')

    def parse_date(self, date_str):
        """Parse date string in YYYY-MM-DD format"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Invalid date format: {date_str}. Use YYYY-MM-DD format.')

    def generate_courses(self, file, start_date, end_date, term_name, early_bird_days, dry_run=False, clear_existing=False):
        """Generate courses from TSV file"""
        reader = csv.reader(file, delimiter='\t')

        # Skip header row
        header = next(reader, None)
        if not header:
            raise CommandError('Empty TSV file or missing header')

        self.stdout.write(f'Header: {header}')

        # Clear existing courses if requested
        if clear_existing and not dry_run:
            existing_count = Course.objects.filter(name__icontains=term_name).count()
            if existing_count > 0:
                self.stdout.write(f'Clearing {existing_count} existing courses containing "{term_name}"...')
                Course.objects.filter(name__icontains=term_name).delete()

        stats = {
            'total': 0,
            'success': 0,
            'skipped': 0,
            'errors': 0
        }

        errors = []

        for row_num, row in enumerate(reader, start=2):  # Start from 2 since we skipped header
            if not row or len(row) < 7:  # Skip empty or incomplete rows
                continue

            stats['total'] += 1

            try:
                # Parse TSV columns: Weekday, Course, Start Time, Duration (mins), Original Price, Early Bird Price, New Student Enrolment Fee
                weekday_str, course_name, start_time_str, duration_str, original_price_str, early_bird_price_str, registration_fee_str = row[:7]

                # Parse course data
                course_data = self.parse_course_data(
                    weekday_str, course_name, start_time_str, duration_str,
                    original_price_str, early_bird_price_str, registration_fee_str,
                    start_date, end_date, term_name, early_bird_days
                )

                if not course_data:
                    stats['skipped'] += 1
                    continue

                # Check for existing course with same name
                if Course.objects.filter(name=course_data['name']).exists():
                    self.stdout.write(
                        f"Row {row_num}: Course '{course_data['name']}' already exists, skipping"
                    )
                    stats['skipped'] += 1
                    continue

                if not dry_run:
                    # Create course
                    with transaction.atomic():
                        course = Course.objects.create(**course_data)
                        self.stdout.write(
                            self.style.SUCCESS(f"Row {row_num}: Created course '{course.name}'")
                        )
                else:
                    self.stdout.write(
                        f"Row {row_num}: Would create course '{course_data['name']}'"
                    )

                stats['success'] += 1

            except Exception as e:
                error_msg = f"Row {row_num} error: {str(e)}"
                errors.append(error_msg)
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(error_msg))

        # Print summary
        self.print_summary(stats, errors, dry_run)

    def parse_course_data(self, weekday_str, course_name, start_time_str, duration_str,
                         original_price_str, early_bird_price_str, registration_fee_str,
                         start_date, end_date, term_name, early_bird_days):
        """Parse and validate course data from TSV row"""
        try:
            # Parse weekday
            weekday_num = self.parse_weekday(weekday_str)
            if weekday_num is None:
                self.stdout.write(self.style.ERROR(f"Invalid weekday: {weekday_str}"))
                return None

            # Parse start time
            start_time = self.parse_time(start_time_str)
            if not start_time:
                self.stdout.write(self.style.ERROR(f"Invalid start time: {start_time_str}"))
                return None

            # Parse duration
            duration_minutes = self.parse_duration(duration_str)
            if not duration_minutes:
                self.stdout.write(self.style.ERROR(f"Invalid duration: {duration_str}"))
                return None

            # Parse prices
            original_price = self.parse_price(original_price_str)
            early_bird_price = self.parse_price(early_bird_price_str)
            registration_fee = self.parse_price(registration_fee_str)

            if original_price is None:
                self.stdout.write(self.style.ERROR(f"Invalid original price: {original_price_str}"))
                return None

            # Calculate course start date (first occurrence of weekday on or after term start)
            course_start_date = self.get_first_weekday_date(start_date, weekday_num)

            # Calculate early bird deadline
            early_bird_deadline = None
            if early_bird_price is not None and early_bird_price > 0:
                early_bird_deadline = course_start_date - timedelta(days=early_bird_days)

            # Generate unique course name
            full_course_name = f"{course_name} - {weekday_str} {start_time_str} ({term_name})"

            return {
                'name': full_course_name,
                'short_description': f"{course_name} class every {weekday_str} at {start_time_str}",
                'price': original_price,
                'early_bird_price': early_bird_price if early_bird_price and early_bird_price > 0 else None,
                'early_bird_deadline': early_bird_deadline,
                'registration_fee': registration_fee if registration_fee and registration_fee > 0 else None,
                'course_type': 'group',
                'category': 'term_courses',
                'status': 'draft',  # Create as draft for review
                'start_date': course_start_date,
                'end_date': end_date,
                'repeat_pattern': 'weekly',
                'repeat_weekday': weekday_num,
                'start_time': start_time,
                'duration_minutes': duration_minutes,
                'vacancy': 12,  # Default class capacity
                'is_online_bookable': False,  # Will be enabled when published
                'bookable_state': 'closed',  # Will be opened when published
            }

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error parsing course data: {str(e)}"))
            return None

    def parse_weekday(self, weekday_str):
        """Parse weekday string to weekday number (0=Monday, 6=Sunday)"""
        weekday_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        return weekday_map.get(weekday_str.lower().strip())

    def parse_time(self, time_str):
        """Parse time string in formats like '4:00PM', '10:00AM'"""
        try:
            # Clean the time string
            clean_time = time_str.strip().upper()

            # Handle AM/PM format
            if 'PM' in clean_time or 'AM' in clean_time:
                time_obj = datetime.strptime(clean_time, '%I:%M%p').time()
            else:
                # Handle 24-hour format
                time_obj = datetime.strptime(clean_time, '%H:%M').time()

            return time_obj
        except ValueError:
            return None

    def parse_duration(self, duration_str):
        """Parse duration in minutes"""
        try:
            # Extract numbers from string
            numbers = re.findall(r'\d+', duration_str)
            if numbers:
                return int(numbers[0])
        except (ValueError, IndexError):
            pass
        return None

    def parse_price(self, price_str):
        """Parse price string to Decimal"""
        try:
            # Remove currency symbols and spaces
            clean_price = re.sub(r'[^\d.]', '', price_str.strip())
            if clean_price:
                return Decimal(clean_price)
        except (ValueError, TypeError):
            pass
        return None

    def get_first_weekday_date(self, start_date, target_weekday):
        """Get the first occurrence of target_weekday on or after start_date"""
        days_ahead = target_weekday - start_date.weekday()
        if days_ahead < 0:  # Target day already happened this week
            days_ahead += 7
        return start_date + timedelta(days=days_ahead)

    def print_summary(self, stats, errors, dry_run):
        """Print generation summary"""
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('COURSE GENERATION PREVIEW'))
        else:
            self.stdout.write(self.style.SUCCESS('COURSE GENERATION COMPLETED'))

        self.stdout.write(f"Total rows processed: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"Successfully processed: {stats['success']}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {stats['skipped']}"))
        self.stdout.write(self.style.ERROR(f"Errors: {stats['errors']}"))

        if errors:
            self.stdout.write('\nError details:')
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run and stats['success'] > 0:
            self.stdout.write('\n' + self.style.WARNING(
                'To actually create the courses, run the command without --dry-run'
            ))
        elif not dry_run and stats['success'] > 0:
            self.stdout.write('\n' + self.style.SUCCESS(
                'Courses created as DRAFT status. Review them in Django admin before publishing.'
            ))