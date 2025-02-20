# Generated by Django 5.1.5 on 2025-02-20 16:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v1', '0010_rename_anniversary_cate_customer_anniversary_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
            options={
                'verbose_name': 'Channel',
                'verbose_name_plural': 'Channels',
                'db_table': 'channel',
            },
        ),
        migrations.RemoveField(
            model_name='campaign',
            name='channel_type',
        ),
        migrations.RemoveField(
            model_name='campaign',
            name='discount_value',
        ),
        migrations.RemoveField(
            model_name='campaign',
            name='image_url',
        ),
        migrations.AddField(
            model_name='campaign',
            name='bg_image',
            field=models.ImageField(blank=True, null=True, upload_to='campaign_bg_images/'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='campaign_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns', to='v1.campaigntype'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='campaign_logos/'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='outlets',
            field=models.ManyToManyField(blank=True, related_name='campaigns', to='v1.outlet'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='profession',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns', to='v1.profession'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='reward_choice',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns', to='v1.rewardchoice'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='reward_choice_text',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='campaign',
            name='channels',
            field=models.ManyToManyField(related_name='campaign_channels', to='v1.channel'),
        ),
    ]
