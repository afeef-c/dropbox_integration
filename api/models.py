from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.timezone import now
from django.conf import settings
from datetime import timedelta
import requests

# Create your models here.

class Location(models.Model):
    locationId = models.CharField(primary_key=True, max_length=700)
    location_name = models.CharField(max_length=700, null=True, blank=True)
    timezone = models.CharField(max_length=700, null=True, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.DateTimeField()

    def __str__(self):
        return self.locationId

class Contact(models.Model):
    contact_id = models.CharField(primary_key=True, max_length=700)
    project_id = models.CharField(max_length=700, null=True, blank=True)
    location_id = models.CharField(max_length=700, null=True, blank=True)
    location_name = models.CharField(max_length=700, null=True, blank=True)
    name = models.CharField(max_length=700, null=True, blank=True)
    primary_phone = models.CharField(max_length=700, null=True, blank=True)
    primary_email = models.CharField(max_length=700, null=True, blank=True)
    secondary_phone = models.CharField(max_length=700, null=True, blank=True)
    secondary_email = models.CharField(max_length=700, null=True, blank=True)
    secondary_phone_name = models.CharField(max_length=700, null=True, blank=True)
    primary_phone_name = models.CharField(max_length=700, null=True, blank=True)
    refferd_by = models.CharField(max_length=700, null=True, blank=True)
    address = models.CharField(max_length=700, null=True, blank=True)
    zip = models.CharField(max_length=700, null=True, blank=True)
    city = models.CharField(max_length=700, null=True, blank=True)
    state = models.CharField(max_length=700, null=True, blank=True)
    hoa = models.CharField(max_length=700, null=True, blank=True)
    plot_plan = models.CharField(max_length=700, null=True, blank=True)
    hardscape_2d_3d = models.FloatField(null=True, blank=True)
    hardscape_and_planting = models.FloatField(null=True, blank=True)
    above_plan_plus = models.FloatField(null=True, blank=True)
    measuring_for_site_plan = models.FloatField(null=True, blank=True)
    property_droning = models.FloatField(null=True, blank=True)
    property_survey = models.FloatField(null=True, blank=True)
    consultations_and_revisions_amount_hour = models.IntegerField(null=True, blank=True)
    other = models.FloatField(null=True, blank=True)
    describe_other = models.CharField(max_length=700, null=True, blank=True)
    project_amount = models.FloatField(null=True, blank=True)
    first_payment_amount = models.FloatField(null=True, blank=True)
    payment_option = models.CharField(max_length=700, null=True, blank=True)
    amount_to_charge_for_credit_card = models.FloatField(null=True, blank=True)
    card_holder_name = models.CharField(max_length=700, null=True, blank=True)
    credit_card_number = models.CharField(max_length=700, null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    expiration_date_str = models.CharField(max_length=700, null=True, blank=True)
    billing_zip_code = models.CharField(max_length=700, null=True, blank=True)
    cvv = models.CharField(max_length=700, null=True, blank=True)
    amount_to_charge_for_zelle = models.FloatField(null=True, blank=True)
    amount_to_charge_for_cash = models.FloatField(null=True, blank=True)
    amount_to_charge_for_check = models.FloatField(null=True, blank=True)
    check_number = models.CharField(max_length=700, null=True, blank=True)
    submitted_at = models.DateField(null=True, blank=True)
    client_signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    representative_signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    pdf = models.FileField(upload_to='pdfs/', null=True, blank=True)
    client_signature_url = models.CharField(max_length=700, null=True, blank=True)
    representative_signature_url = models.CharField(max_length=700, null=True, blank=True)
    pdf_url = models.CharField(max_length=700, null=True, blank=True)
    modified_at = models.DateField(null=True, blank=True)
    representative_signed_date = models.DateField(null=True, blank=True)
    client_signed_date = models.DateField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.project_id} - {self.contact_id}"

class User(models.Model):
    user_id = models.CharField(primary_key=True, max_length=700)
    name = models.CharField(max_length=700, null=True, blank=True)
    email = models.CharField(max_length=700, null=True, blank=True)
    phone = models.CharField(max_length=700, null=True, blank=True)

    def __str__(self):
        return self.name

class Task(models.Model):
    END_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ]
    task_id = models.CharField(primary_key=True, max_length=700)
    contact = models.ForeignKey(Contact, related_name='contact', on_delete=models.CASCADE)
    category = models.CharField(max_length=700, null=True, blank=True)
    name = models.CharField(max_length=700, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    assigned_to_id = models.CharField(max_length=700, null=True, blank=True)
    assigned_to = models.CharField(max_length=700, null=True, blank=True)
    completed = models.BooleanField(default=False)
    progress = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_progress = models.BooleanField(default=True)
    end_choices = models.CharField(max_length=10, choices=END_CHOICES, default='na')
    

    class Meta:
        unique_together = ('contact', 'category', 'name')
    
    def __str__(self):
        return f"{self.contact.project_id} : {self.name}"
    



class CreditCard(models.Model):
    contact = models.OneToOneField(Contact, on_delete=models.CASCADE, related_name='credit_card')
    card_holder_name = models.CharField(max_length=700, null=True, blank=True)
    credit_card_number = models.CharField(max_length=700, null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    cvv = models.CharField(max_length=700, null=True, blank=True)


    def __str__(self):
        return f"Credit Card for {self.contact.contact_id}"
    



class TaskTemplate(models.Model):
    category = models.CharField(max_length=255)
    task_name = models.CharField(max_length=255)
    assigned_to = ArrayField(models.CharField(max_length=255), blank=True, default=list)

    def __str__(self):
        return f"{self.category} - {self.task_name}"
    
    
    
class DropBoxToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.access_token[:5]



    def is_expired(self):
        return now() >= self.expires_at

    def refresh_access_token(self):
        if not self.refresh_token:
            return None  
        
        
        url = "https://api.dropbox.com/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "client_id": settings.APP_KEY,
            "client_secret": settings.APP_SECRET
        }
        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.expires_at = now() + timedelta(seconds=token_data["expires_in"])
            self.save()
            return self.access_token
        else:
            print("Failed to refresh token:", response.json())
            return None

    def get_valid_access_token(self):
        """Get a valid access token, refreshing if expired."""
        if self.is_expired():
            return self.refresh_access_token()
        return self.access_token



