# Generated by Django 4.2.11 on 2024-04-21 12:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('thoughts', '0009_remove_seed_reserve_url_seed_reserve_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='Garden',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_gardens', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='GardenMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_edit', models.BooleanField(default=False)),
                ('garden', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='thoughts.garden')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('garden', 'user')},
            },
        ),
        migrations.AddField(
            model_name='garden',
            name='visitors',
            field=models.ManyToManyField(related_name='visited_gardens', through='thoughts.GardenMembership', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='seed',
            name='garden',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, related_name='seeds', to='thoughts.garden'),
            preserve_default=False,
        ),
    ]
