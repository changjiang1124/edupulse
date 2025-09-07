from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Create an admin user with specified username and password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the admin user')
        parser.add_argument('password', type=str, help='Password for the admin user')
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the admin user (optional)',
            default='admin@perthartschool.com.au'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='First name for the admin user (optional)',
            default='Admin'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Last name for the admin user (optional)',
            default='User'
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update existing user without confirmation prompt'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        password = options['password']
        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']

        try:
            # Check if user already exists
            existing_user = User.objects.filter(username=username).first()
            
            if existing_user:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists!')
                )
                self.stdout.write(f'Current details:')
                self.stdout.write(f'  Email: {existing_user.email}')
                self.stdout.write(f'  Name: {existing_user.first_name} {existing_user.last_name}')
                self.stdout.write(f'  Role: {existing_user.role}')
                self.stdout.write(f'  Is Staff: {existing_user.is_staff}')
                self.stdout.write(f'  Is Superuser: {existing_user.is_superuser}')
                
                # Ask for confirmation
                confirm = input('\nDo you want to update this user\'s password and admin settings? (yes/no): ')
                
                if confirm.lower() in ['yes', 'y']:
                    # Update password and admin settings
                    existing_user.set_password(password)
                    existing_user.role = 'admin'
                    existing_user.is_staff = True
                    existing_user.is_superuser = True
                    existing_user.is_active_staff = True
                    
                    # Optionally update other fields if provided
                    if email != 'admin@perthartschool.com.au':  # Only if email was explicitly provided
                        existing_user.email = email
                    if first_name != 'Admin':  # Only if first name was explicitly provided
                        existing_user.first_name = first_name
                    if last_name != 'User':  # Only if last name was explicitly provided
                        existing_user.last_name = last_name
                    
                    existing_user.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully updated user "{username}" with new password and admin privileges'
                        )
                    )
                    self.stdout.write(f'Updated details:')
                    self.stdout.write(f'  Email: {existing_user.email}')
                    self.stdout.write(f'  Name: {existing_user.first_name} {existing_user.last_name}')
                    self.stdout.write(f'  Role: {existing_user.role}')
                    
                else:
                    self.stdout.write(
                        self.style.WARNING('Operation cancelled. No changes made.')
                    )
                return
            
            # Create new admin user
            admin_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='admin',  # Set role to admin for Staff model
                is_staff=True,
                is_superuser=True,
                is_active_staff=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created admin user "{username}" with role "admin"'
                )
            )
            self.stdout.write(f'Details:')
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Name: {first_name} {last_name}')
            self.stdout.write(f'  Role: admin')
            
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing user: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Unexpected error: {e}')
            )