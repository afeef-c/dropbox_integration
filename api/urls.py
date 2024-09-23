from django.urls import path
from .views import *

urlpatterns = [
    path('', onboarding_page, name='onboarding_page'),
    path('validation', validation, name='validation'),
    path('submit_form_data', submit_form_data, name='submit_form_data'),
    path('submit_agreement', submit_agreement, name='submit_agreement'),
    path('submit_client_signature', submit_client_signature, name='submit_client_signature'),
    path('current_clients', current_clients, name='current_clients'),
    path('current_client/<str:project_id>', current_client, name='current_client'),
    path('historic', historic, name='historic'),
]