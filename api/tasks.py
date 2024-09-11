from celery import shared_task
from .models import *
import requests
from django.conf import settings
from celery.exceptions import MaxRetriesExceededError
from requests.exceptions import RequestException
import json

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def historic_fetch(self, *args):
    locations = Location.objects.all()
    for location in locations:
        location_id = location.locationId

          
        