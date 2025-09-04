# Generated manually on 2025-09-04 to fix registration_fee nullable constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0007_course_registration_fee_alter_course_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='registration_fee',
            field=models.DecimalField(
                blank=True,
                null=True,
                decimal_places=2, 
                default=None,
                help_text='Additional fee for new student registration. Leave blank if no registration fee required.',
                max_digits=10, 
                verbose_name='Registration Fee'
            ),
        ),
    ]