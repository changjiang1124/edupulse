from django.core.management.base import BaseCommand
from students.models import StudentTag


class Command(BaseCommand):
    help = 'Create default student tags for batch operations'

    def handle(self, *args, **options):
        default_tags = [
            {
                'name': 'New Student',
                'colour': '#28a745',
                'description': 'Recently enrolled students who need follow-up'
            },
            {
                'name': 'Active Student',
                'colour': '#007bff',
                'description': 'Students actively attending classes'
            },
            {
                'name': 'Needs Follow-up',
                'colour': '#ffc107',
                'description': 'Students requiring additional attention'
            },
            {
                'name': 'VIP Student',
                'colour': '#6f42c1',
                'description': 'High-priority or special attention students'
            },
            {
                'name': 'Waitlist',
                'colour': '#fd7e14',
                'description': 'Students on course waitlists'
            },
            {
                'name': 'Alumni',
                'colour': '#6c757d',
                'description': 'Former students who completed courses'
            },
        ]

        created_count = 0
        for tag_data in default_tags:
            tag, created = StudentTag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'colour': tag_data['colour'],
                    'description': tag_data['description'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created tag: {tag.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tag already exists: {tag.name}')
                )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created_count} default student tags!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('All default tags already exist.')
            )