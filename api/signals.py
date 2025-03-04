from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Contact, Task
from .tasks import create_all_task
from .views import add_archieved_tag_to_ghl

@receiver(post_save, sender=Contact)
def call_create_task(sender, instance, **kwargs):
    # Check if both 'client_signature_url' and 'representative_signature_url' are not null or empty
    if instance.client_signature_url and instance.representative_signature_url:
        # Call the Celery task with the contact_id
        create_all_task.delay(instance.contact_id)

@receiver(post_save, sender=Task)
def task_completion_signal(sender, instance, **kwargs):
    # Check if the task name matches and is marked as completed
    print(instance.name)
    if instance.name == "Digital copies sent to client" and instance.completed:
        # Perform your action here (e.g., send notification, log entry, etc.)
        add_archieved_tag_to_ghl(instance.contact.location_id, instance.contact.contact_id)
