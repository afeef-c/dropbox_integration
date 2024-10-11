from django.urls import path
from .views import *

urlpatterns = [
    path('', onboarding_page, name='onboarding_page'),
    path('validation', validation, name='validation'),
    path('submit_form_data', submit_form_data, name='submit_form_data'),
    path('submit_agreement', submit_agreement, name='submit_agreement'),
    path('submit_client_signature', submit_client_signature_v2, name='submit_client_signature'),
    path('current_clients', current_clients, name='current_clients'),
    path('current_client/<str:project_id>', current_client, name='current_client'),
    path('historic', historic, name='historic'),
    path('fetch_users', fetch_users, name='fetch_users'),

    path('submit_agreement_v2', submit_agreement_v2, name='submit_agreement_v2'),
    path('delete_current_client/<str:project_id>', delete_current_client, name='delete_current_client'),
]