# Generated by Django 4.2.11 on 2024-04-21 14:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_remove_customuser_telegram_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customuser',
            old_name='use_api_key',
            new_name='use_sytsem_api_key',
        ),
    ]
