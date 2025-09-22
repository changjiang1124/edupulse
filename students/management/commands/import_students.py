import csv
import re
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.exceptions import ValidationError
from students.models import Student, StudentActivity
from django.utils import timezone


class Command(BaseCommand):
    help = 'Import students from TSV file into the Student model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='students.tsv',
            help='Path to the TSV file to import (default: students.tsv)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without actually saving data'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.import_students(file, dry_run)
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')
        except Exception as e:
            raise CommandError(f'Error reading file: {str(e)}')

    def import_students(self, file, dry_run=False):
        """Import students from TSV file"""
        reader = csv.reader(file, delimiter='\t')

        # Skip header row
        next(reader, None)

        stats = {
            'total': 0,
            'success': 0,
            'skipped': 0,
            'errors': 0
        }

        errors = []

        for row_num, row in enumerate(reader, start=2):  # Start from 2 since we skipped header
            if not row or len(row) < 6:  # Skip empty or incomplete rows
                continue

            stats['total'] += 1

            try:
                student_name, dob, guardian_name, phone, address, email = row[:6]

                # Skip empty names
                if not student_name.strip():
                    stats['skipped'] += 1
                    continue

                # Parse student data
                parsed_data = self.parse_student_data(
                    student_name, dob, guardian_name, phone, address, email
                )

                if not parsed_data:
                    stats['skipped'] += 1
                    continue

                # Check for existing student
                existing_student = self.find_existing_student(parsed_data)
                if existing_student:
                    self.stdout.write(
                        f"第 {row_num} 行: 学生 {parsed_data['first_name']} {parsed_data['last_name']} 已存在，跳过"
                    )
                    stats['skipped'] += 1
                    continue

                if not dry_run:
                    # Create student
                    with transaction.atomic():
                        student = Student.objects.create(**parsed_data)

                        # Create activity record
                        StudentActivity.create_activity(
                            student=student,
                            activity_type='other',
                            title='Student imported from TSV',
                            description=f'Student data imported from TSV file on {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
                        )

                        self.stdout.write(
                            f"第 {row_num} 行: 成功导入学生 {student.get_full_name()}"
                        )
                else:
                    self.stdout.write(
                        f"第 {row_num} 行: 将导入学生 {parsed_data['first_name']} {parsed_data['last_name']}"
                    )

                stats['success'] += 1

            except Exception as e:
                error_msg = f"第 {row_num} 行错误: {str(e)}"
                errors.append(error_msg)
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(error_msg))

        # Print summary
        self.print_summary(stats, errors, dry_run)

    def parse_student_data(self, student_name, dob, guardian_name, phone, address, email):
        """Parse and validate student data from TSV row"""
        try:
            # Parse name
            first_name, last_name = self.parse_name(student_name)
            if not first_name or not last_name:
                return None

            # Parse birth date
            birth_date = self.parse_date(dob)

            # Clean phone
            clean_phone = self.clean_phone(phone)

            # Clean email
            clean_email = self.clean_email(email)

            return {
                'first_name': first_name,
                'last_name': last_name,
                'birth_date': birth_date,
                'guardian_name': guardian_name.strip() if guardian_name else '',
                'contact_phone': clean_phone,
                'address': address.strip() if address else '',
                'contact_email': clean_email,
                'enrollment_source': 'TSV Import',
                'is_active': True
            }

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"解析数据错误: {str(e)}"))
            return None

    def parse_name(self, full_name):
        """Parse full name into first and last name"""
        if not full_name or not full_name.strip():
            return None, None

        # Clean the name
        clean_name = full_name.strip()

        # Handle names with comma (LAST, FIRST format)
        if ',' in clean_name:
            parts = clean_name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ''
        else:
            # Handle normal format (FIRST LAST)
            parts = clean_name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
            elif len(parts) == 1:
                first_name = parts[0]
                last_name = ''
            else:
                return None, None

        # Capitalize names properly
        first_name = first_name.title() if first_name else ''
        last_name = last_name.title() if last_name else ''

        return first_name, last_name

    def parse_date(self, date_str):
        """Parse date string in DD/MM/YYYY format"""
        if not date_str or not date_str.strip() or date_str.strip() == ',':
            return None

        clean_date = date_str.strip()

        # Handle incomplete dates like "01/01/"
        if clean_date.endswith('/'):
            return None

        try:
            # Try DD/MM/YYYY format
            return datetime.strptime(clean_date, '%d/%m/%Y').date()
        except ValueError:
            try:
                # Try other common formats
                return datetime.strptime(clean_date, '%d/%m/%y').date()
            except ValueError:
                return None

    def clean_phone(self, phone):
        """Clean and validate phone number"""
        if not phone or not phone.strip():
            return ''

        # Remove all non-digit characters except + at the beginning
        clean_phone = re.sub(r'[^\d+]', '', phone.strip())

        # Remove leading + and country codes for Australian numbers
        if clean_phone.startswith('+61'):
            clean_phone = '0' + clean_phone[3:]
        elif clean_phone.startswith('61') and len(clean_phone) >= 10:
            clean_phone = '0' + clean_phone[2:]

        # Format Australian mobile numbers (add spaces)
        if len(clean_phone) == 10 and clean_phone.startswith('04'):
            return f"{clean_phone[:4]} {clean_phone[4:7]} {clean_phone[7:]}"
        elif len(clean_phone) == 10 and clean_phone.startswith('0'):
            return f"{clean_phone[:2]} {clean_phone[2:6]} {clean_phone[6:]}"

        return clean_phone

    def clean_email(self, email):
        """Clean and validate email"""
        if not email or not email.strip():
            return ''

        clean_email = email.strip().lower()

        # Basic email validation
        if '@' not in clean_email or '.' not in clean_email:
            return ''

        return clean_email

    def find_existing_student(self, data):
        """Check if student already exists"""
        try:
            # Try to find by exact name and birth date match
            if data['birth_date']:
                return Student.objects.filter(
                    first_name__iexact=data['first_name'],
                    last_name__iexact=data['last_name'],
                    birth_date=data['birth_date']
                ).first()

            # Try to find by exact name and email match
            if data['contact_email']:
                return Student.objects.filter(
                    first_name__iexact=data['first_name'],
                    last_name__iexact=data['last_name'],
                    contact_email__iexact=data['contact_email']
                ).first()

            # Try to find by exact name and phone match
            if data['contact_phone']:
                return Student.objects.filter(
                    first_name__iexact=data['first_name'],
                    last_name__iexact=data['last_name'],
                    contact_phone=data['contact_phone']
                ).first()

        except Exception:
            pass

        return None

    def print_summary(self, stats, errors, dry_run):
        """Print import summary"""
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING('预览导入结果'))
        else:
            self.stdout.write(self.style.SUCCESS('导入完成'))

        self.stdout.write(f"总计处理行数: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"成功: {stats['success']}"))
        self.stdout.write(self.style.WARNING(f"跳过: {stats['skipped']}"))
        self.stdout.write(self.style.ERROR(f"错误: {stats['errors']}"))

        if errors:
            self.stdout.write('\n错误详情:')
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run and stats['success'] > 0:
            self.stdout.write('\n' + self.style.WARNING('要实际导入数据，请运行命令时不带 --dry-run 参数'))