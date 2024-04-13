# Generated by Django 3.2.25 on 2024-04-01 18:01

from django.db import migrations, models
import django.db.models.deletion  # Added for ForeignKey

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Idea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('content_url', models.URLField(blank=True, max_length=1024, null=True)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='thumbnails/')),
                ('transcript', models.TextField(blank=True, null=True)),
                ('embedding', models.JSONField(blank=True, null=True)),  # Assume you'll change this later
                ('author', models.CharField(blank=True, max_length=255, null=True)),
                ('language', models.CharField(blank=True, max_length=50, null=True)),
                ('topics', models.CharField(blank=True, max_length=255, null=True)),
                ('tags', models.CharField(blank=True, max_length=255, null=True)),
                ('year', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='IdeaPart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                # Temporarily use a TextField for embedding; plan to change to VectorField later
                ('embedding', models.TextField(blank=True, null=True)),
                ('idea', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parts', to='thoughts.idea')),
            ],
        ),
    ]
