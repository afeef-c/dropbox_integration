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
    path('fetch_users', fetch_users, name='fetch_users'),
    path('ghl_webhook', ghl_webhook, name='ghl_webhook'),
    path('get_gantt_chart/<str:project_id>', get_gantt_chart, name='get_gantt_chart'),
    path('delete_current_client/<str:project_id>', delete_current_client, name='delete_current_client'),

    path('submit_form_data_v2', submit_form_data_v2, name='submit_form_data_v2'),
    path('submit_agreement_v2', submit_agreement_v2, name='submit_agreement_v2'),
    path('submit_client_signature_form_data_v2', submit_client_signature_form_data_v2, name='submit_client_signature_form_data_v2'),
    path('submit_client_signature_v2', submit_client_signature_v2, name='submit_client_signature_v2'),
    path('current_client_v2/<str:contact_id>', current_client_v2, name='current_client_v2'),
    path('get_gantt_chart_v2/<str:contact_id>', get_gantt_chart_v2, name='get_gantt_chart_v2'),
    path('update_task/<str:task_id>', update_task, name='update_task'),
    path('open_projects_gantt_chart', open_projects_gantt_chart, name='open_projects_gantt_chart'),
    path('delete_current_client_v2/<str:contact_id>', delete_current_client_v2, name='delete_current_client_v2'),
]