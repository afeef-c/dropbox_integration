from django.urls import path
from .views import *

urlpatterns = [
    path('', onboarding_page, name='onboarding_page'),
    path('validation', validation, name='validation'),
    path('submit_form_data', submit_form_data, name='submit_form_data'),
    path('submit_agreement', submit_agreement, name='submit_agreement'),
    path('current_clients', current_clients, name='current_clients'),
    path('historic', historic, name='historic'),
]