from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.conf.enable_utc = False
app.conf.update(timezone='UTC')

app.config_from_object(settings, namespace='CELERY')

# #Celery Beat Settings
# app.conf.beat_schedule = {
#     'schedule_all_data':{
#         'task': 'urlshortener.tasks.all_data_dump',
#         'schedule': crontab(hour=8, minute=2)
#     }
# }

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request:{self.request!r}')