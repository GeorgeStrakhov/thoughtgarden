# Generated by Django 4.2.11 on 2024-05-23 22:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thoughts', '0011_snippet_start_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='seed',
            name='is_youtube',
            field=models.BooleanField(default=False),
        ),
    ]
