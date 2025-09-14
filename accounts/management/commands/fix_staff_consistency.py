"""
Django management command to fix staff role and Django auth field consistency
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Staff


class Command(BaseCommand):
    help = 'Fix inconsistencies between staff roles and Django auth fields'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Apply changes without confirmation',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS('Staff Role and Django Auth Fields Consistency Fixer')
        )
        self.stdout.write('=' * 60)
        
        # Get all staff members
        all_staff = Staff.objects.all()
        
        if not all_staff.exists():
            self.stdout.write(self.style.WARNING('No staff members found.'))
            return
        
        # Analyze current state
        self.stdout.write(f'\nAnalyzing {all_staff.count()} staff members...\n')
        
        admin_staff = []
        teacher_staff = []
        inconsistent_staff = []
        
        for staff in all_staff:
            if staff.role == 'admin':
                admin_staff.append(staff)
                if not staff.is_staff or not staff.is_superuser:
                    inconsistent_staff.append({
                        'staff': staff,
                        'issue': 'admin_missing_permissions',
                        'current': f'is_staff={staff.is_staff}, is_superuser={staff.is_superuser}',
                        'should_be': 'is_staff=True, is_superuser=True'
                    })
            elif staff.role == 'teacher':
                teacher_staff.append(staff)
                if staff.is_superuser:
                    inconsistent_staff.append({
                        'staff': staff,
                        'issue': 'teacher_has_superuser',
                        'current': f'is_staff={staff.is_staff}, is_superuser={staff.is_superuser}',
                        'should_be': 'is_staff=False, is_superuser=False'
                    })
        
        # Display analysis results
        self.stdout.write(f'📊 Analysis Results:')
        self.stdout.write(f'  • Total staff: {all_staff.count()}')
        self.stdout.write(f'  • Administrators: {len(admin_staff)}')
        self.stdout.write(f'  • Teachers: {len(teacher_staff)}')
        self.stdout.write(f'  • Inconsistent records: {len(inconsistent_staff)}')
        
        if not inconsistent_staff:
            self.stdout.write(self.style.SUCCESS('\n✅ All staff records are consistent!'))
            return
        
        # Display inconsistencies
        self.stdout.write(f'\n🔍 Found {len(inconsistent_staff)} inconsistent records:')
        for i, item in enumerate(inconsistent_staff, 1):
            staff = item['staff']
            self.stdout.write(f'\n{i}. {staff.first_name} {staff.last_name} ({staff.username})')
            self.stdout.write(f'   Role: {staff.get_role_display()}')
            self.stdout.write(f'   Issue: {item["issue"]}')
            self.stdout.write(f'   Current: {item["current"]}')
            self.stdout.write(f'   Should be: {item["should_be"]}')
        
        if dry_run:
            self.stdout.write(f'\n🔍 DRY RUN: No changes were made.')
            self.stdout.write(f'Run without --dry-run to apply fixes.')
            return
        
        # Confirm changes
        if not force:
            self.stdout.write(f'\n⚠️  This will update {len(inconsistent_staff)} staff records.')
            confirm = input('Do you want to proceed? [y/N]: ').lower().strip()
            if confirm != 'y':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return
        
        # Apply fixes
        self.stdout.write(f'\n🔧 Applying fixes...')
        
        with transaction.atomic():
            fixed_count = 0
            
            for item in inconsistent_staff:
                staff = item['staff']
                
                try:
                    if item['issue'] == 'admin_missing_permissions':
                        # Fix admin permissions
                        staff.is_staff = True
                        staff.is_superuser = True
                        staff.save()
                        self.stdout.write(f'  ✅ Fixed {staff.username}: Added admin permissions')
                        
                    elif item['issue'] == 'teacher_has_superuser':
                        # Fix teacher permissions
                        staff.is_staff = False
                        staff.is_superuser = False
                        staff.save()
                        self.stdout.write(f'  ✅ Fixed {staff.username}: Removed superuser permissions')
                    
                    fixed_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Failed to fix {staff.username}: {str(e)}')
                    )
        
        # Summary
        self.stdout.write(f'\n📈 Summary:')
        self.stdout.write(f'  • Records analyzed: {all_staff.count()}')
        self.stdout.write(f'  • Issues found: {len(inconsistent_staff)}')
        self.stdout.write(f'  • Records fixed: {fixed_count}')
        
        if fixed_count == len(inconsistent_staff):
            self.stdout.write(self.style.SUCCESS('\n🎉 All inconsistencies have been resolved!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  {len(inconsistent_staff) - fixed_count} issues remain. Please check the logs.'))
        
        # Recommendation
        self.stdout.write(f'\n💡 Recommendations:')
        self.stdout.write(f'  • Test login functionality for affected users')
        self.stdout.write(f'  • Verify admin panel access for administrators')
        self.stdout.write(f'  • Update user creation forms to maintain consistency')