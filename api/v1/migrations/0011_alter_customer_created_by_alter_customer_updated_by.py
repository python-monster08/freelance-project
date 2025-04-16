# Generated by Django 5.1.5 on 2025-04-16 10:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v1', '0010_customer_created_by_customer_created_on_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_cutomer_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='customer',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='updated_cutomer_user', to=settings.AUTH_USER_MODEL),
        ),
    ]
