# Generated by Django 4.2.11 on 2024-07-16 23:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_customuser_max_chunk_size_setting'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='telegram_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
