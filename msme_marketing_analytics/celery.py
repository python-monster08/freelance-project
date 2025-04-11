# msme_marketing_analytics/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'msme_marketing_analytics.settings')

app = Celery('msme_marketing_analytics')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto discover tasks in installed apps
app.autodiscover_tasks()

# Use database scheduler (django-celery-beat)
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'



# # msme_marketing_analytics/celery.py
# from __future__ import absolute_import, unicode_literals
# import os
# from celery import Celery

# # Set default Django settings module
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'msme_marketing_analytics.settings')

# app = Celery('msme_marketing_analytics')

# # Load task settings from Django
# app.config_from_object('django.conf:settings', namespace='CELERY')

# # Auto-discover tasks from registered apps
# app.autodiscover_tasks()

# # 🔥 Explicit import to ensure tasks are registered
# import api.v1.tasks

# # Use Django DB scheduler for periodic tasks
# app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'



# from __future__ import absolute_import, unicode_literals
# import os
# from celery import Celery

# # Set default Django settings module for 'celery'
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'msme_marketing_analytics.settings')

# app = Celery('msme_marketing_analytics')

# # Load task modules from all registered Django app configs.
# app.config_from_object('django.conf:settings', namespace='CELERY')

# # Autodiscover task modules from all apps
# app.autodiscover_tasks()

# # ✅ Add this to enable django-celery-beat scheduler
# app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'
