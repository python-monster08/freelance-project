# Generated by Django 5.1.5 on 2025-03-24 18:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v1', '0003_supportsystem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supportsystem',
            name='dedicated_poc',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='supportsystem',
            name='staff_re_training',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='supportsystem',
            name='support',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='supportsystem',
            name='training',
            field=models.BooleanField(default=False),
        ),
    ]
