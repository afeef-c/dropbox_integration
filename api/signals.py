from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Contact
from .tasks import create_all_task

@receiver(post_save, sender=Contact)
def call_create_task(sender, instance, **kwargs):
    # Check if both 'client_signature_url' and 'representative_signature_url' are not null or empty
    if instance.client_signature_url and instance.representative_signature_url:
        # Call the Celery task with the contact_id
        create_all_task.delay(instance.contact_id)
