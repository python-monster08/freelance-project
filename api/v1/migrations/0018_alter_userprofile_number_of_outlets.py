# Generated by Django 5.1.5 on 2025-03-10 17:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v1', '0017_alter_userprofile_number_of_outlets'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='number_of_outlets',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
