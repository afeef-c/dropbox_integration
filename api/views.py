from django.shortcuts import render
import requests
from rest_framework.response import Response
from rest_framework.decorators import api_view, parser_classes
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.conf import settings
from .models import *
from django.http import JsonResponse
import datetime
from datetime import timedelta
from datetime import timezone as tzone
import pytz
import uuid
from .serializers import *
from django.db.models import Q
from .tasks import historic_fetch, fetch_users_by_location, create_all_task
import json
from django.core.files.base import ContentFile
import base64
from io import BytesIO
from django.core.files.storage import default_storage
import os
from PIL import Image
from django.db.models import Count, Case, When, IntegerField, Min, Max

# Create your views here.

def onboarding_page(request):
   
   return render(request,'onboard.html')

def validation(request):
    if request.method == 'POST':
        location_id = request.POST.get('locationId')
        access_code = request.POST.get('accessCode')
        client_id = settings.CLIENT_ID
        client_secret = settings.CLIENT_SECRET
        url = 'https://services.leadconnectorhq.com/oauth/token'
        params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': access_code,
        }

        response = requests.post(url, data=params)
    
        if response.status_code == 200:
            data = response.json()
            if location_id == data['locationId']:
                # Extract the required data from the response
                access_token = data['access_token']
                refresh_token = data['refresh_token']
                expires_in = data['expires_in']

                # Calculate the expiration datetime
                expiration_datetime = datetime.datetime.now(tzone.utc) + timedelta(seconds=expires_in)

                location_details = get_location_details(location_id, access_token)
                location_name = location_details['name']
                location_timezone = location_details['timezone']


                # Save the data in the database
                Location.objects.update_or_create(
                    locationId=location_id,
                    defaults={
                        'location_name':location_name,
                        'timezone': location_timezone,
                        'access_token':access_token,
                        'refresh_token':refresh_token,
                        'expires_in':expiration_datetime
                    }
                )

                return JsonResponse({'success':True, 'message':'Successful response'}, safe=False)
            else:
                return JsonResponse({'success':False, 'message':'Location ID is incorrect'}, safe=False)
        elif response.status_code == 400:
            return JsonResponse({'success':False, 'message':'Bad Request'}, safe=False)
        elif response.status_code == 401:
            return JsonResponse({'success':False, 'message':'Unauthorized'}, safe=False)
        elif response.status_code == 422:
            return JsonResponse({'success':False, 'message':'Unprocessable Entity'}, safe=False)
        else:
            return JsonResponse({'success':False, 'message':'Unprocessable Entity'}, safe=False)

    return JsonResponse({'success':False, 'message':'Only POST request allowed'}, safe=False)

def get_location_details(location_id, access_token):

    url = f"https://services.leadconnectorhq.com/locations/{location_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }

    response = requests.get(url, headers=headers)

    # Check the status code and print the response
    if response.ok:
        data = response.json()
        location = data['location']
        return location

def checking_token_expiration(location_id):
    location = Location.objects.get(locationId = location_id)

    if location:
        current_time = datetime.datetime.now(tzone.utc)
        expiration_time = location.expires_in
        time_difference = expiration_time - current_time

        if time_difference.total_seconds() <= 300:  # 300 seconds = 5 minutes
            # Token is expiring within 5 minutes
            return True
        
    return False
    
def refreshing_tokens(location_id):

    client_id = settings.CLIENT_ID
    client_secret = settings.CLIENT_SECRET
    location = Location.objects.get(locationId = location_id)
    refreshToken = location.refresh_token

    url = 'https://services.leadconnectorhq.com/oauth/token'
    params = {
    'client_id': client_id,
    'client_secret': client_secret,
    'grant_type': 'refresh_token',
    'refresh_token': refreshToken,
    }

    response = requests.post(url, data=params)

    if response.status_code == 200:
        data = response.json()
        # Extract the required data from the response
        access_token = data['access_token']
        refresh_token = data['refresh_token']
        expires_in = data['expires_in']

        # Calculate the expiration datetime
        expiration_datetime = datetime.datetime.now(tzone.utc) + timedelta(seconds=expires_in)


        # Save the data in the database
        location = Location.objects.get(locationId = location_id)
        location.access_token = access_token
        location.refresh_token = refresh_token
        location.expires_in = expiration_datetime
        location.save()
        return True
    else:
        return False
    
def get_all_custom_fields(location_id):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    url = 'https://services.leadconnectorhq.com/locations/{locationId}/customFields'
    locationId = location_id
    access_token = access_token

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-07-28'
    }

    
    response = requests.get(url.format(locationId=locationId), headers=headers)
   
    # Check the response status code
    if response.status_code == 200:
        # Successful request
        data = response.json()
        custom_fields = data['customFields']
        return custom_fields
    else:
       return None
    
@api_view(['GET'])
def current_client(request, project_id):
    contact = Contact.objects.get(project_id=project_id)
    serializer = ContactSerializerV2(contact)
    return Response({'data': serializer.data}, status=status.HTTP_200_OK)

@api_view(['GET'])
def current_client_v2(request, contact_id):
    contact = Contact.objects.get(contact_id=contact_id)
    serializer = ContactSerializerV2(contact)
    return Response({'data': serializer.data}, status=status.HTTP_200_OK)
    
@api_view(['GET'])
def current_clients(request):
    limit = request.GET.get('limit', 10)
    offset = request.GET.get('offset', 0)
    limit = int(limit)
    offset = int(offset)
    search = request.GET.get('search')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

    all_contacts = Contact.objects.filter(submitted_at__range=[start_date, end_date], archived=False).order_by('-submitted_at')

    if search:
        search_lower = search.lower()
        all_contacts = all_contacts.filter(
            Q(name__istartswith=search_lower) |
            Q(primary_email__istartswith=search_lower) |
            Q(primary_phone__istartswith=search_lower)
        )
    else:
        all_contacts = all_contacts
    
    # Apply offset and limit
    if offset or limit:
        all_contacts = all_contacts[offset:offset + limit]

    serializer = ContactSerializerV2(all_contacts, many=True)
    return Response({'data': serializer.data}, status=status.HTTP_200_OK)

# @api_view(['POST'])
# @parser_classes([MultiPartParser, FormParser])  # Enables file upload support
# def submit_client_signature(request):
#     form_data = request.data
    
#     client_signature = request.FILES.get('signature')
#     agreement = request.FILES.get('pdf')

#     project_id = form_data.get('project_id')

#     location = Location.objects.first()
#     location_id = location.locationId
#     location_timezone = location.timezone

#     timezone = pytz.timezone(location_timezone)
#     submitted_at = datetime.datetime.now(timezone).replace(tzinfo=None)

#     all_custom_fields = get_all_custom_fields(location_id)
#     for field in all_custom_fields:
#         if field['name'] == 'Client Signature':
#             client_signature_cf = field['id']
#         if field['name'] == 'Representative Signature':
#             representative_signature_cf = field['id']
#         if field['name'] == 'Agreement':
#             agreement_cf = field['id']

#     contact = Contact.objects.get(project_id=project_id)

#     contact.client_signature = client_signature
#     contact.client_signed_date = submitted_at.date()
#     contact.pdf = agreement
#     contact.save()

#     update_contact_file_customfields(location_id=location_id, contact_id=contact.contact_id, client_signature_cf=client_signature_cf, representative_signature_cf=representative_signature_cf, agreement_cf=agreement_cf)
#     serializer = ContactSerializerV2(contact)
#     return Response({'data': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_agreement(request):
    # Extract form data
    project_id = request.data.get('project_id')
    # Extract files
    agreement = request.FILES.get('pdf')

    contact = Contact.objects.get(project_id=project_id)
    contact.pdf = agreement
    contact.save()

    contact_id = contact.contact_id
    location_id = contact.location_id
    all_custom_fields = get_all_custom_fields(location_id)
    for field in all_custom_fields:
        if field['name'] == 'Client Signature':
            client_signature_cf = field['id']
        if field['name'] == 'Representative Signature':
            representative_signature_cf = field['id']
        if field['name'] == 'Agreement':
            agreement_cf = field['id']

    update_contact_file_customfields(location_id=location_id, contact_id=contact_id, client_signature_cf=client_signature_cf, representative_signature_cf=representative_signature_cf, agreement_cf=agreement_cf)
    serializer = ContactSerializerV2(contact)
    return Response({'data': serializer.data}, status=status.HTTP_200_OK)

def _decode_base64_image(base64_str):
    format, imgstr = base64_str.split(';base64,')
    ext = format.split('/')[-1]
    img_data = base64.b64decode(imgstr)
    return ContentFile(img_data, name=f'signature.{ext}')

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_form_data(request):
    print(request.data)
    form_data = request.data


    client_signature = request.FILES.get('signature')
    representative_signature = request.FILES.get('representative_sign')
    agreement = request.FILES.get('pdf')
    
    # Extract form data from the parsed JSON
    contact_id = form_data.get('contact_id')
    project_id = form_data.get('project_id')
    print(project_id)
    refferd_by = form_data.get('refferd_by')
    client_name = form_data.get('name')
    address = form_data.get('address')
    city = form_data.get('city')
    state = form_data.get('state')
    zip = form_data.get('zip')
    primary_phone = form_data.get('primary_phone')
    secondary_phone = form_data.get('secondary_phone')
    primary_email = form_data.get('primary_email')
    secondary_email = form_data.get('secondary_email')

    # // Project Info
    HOA = form_data.get('hoa')
    plot_plan = form_data.get('plot_plan')
    hardscape = form_data.get('hardscape_2d_3d')
    hardscape_and_planning = form_data.get('hardscape_and_planting')
    above_plans_plus = form_data.get('above_plan_plus')
    measuring_for_site_plan = form_data.get('measuring_for_site_plan')
    property_droning = form_data.get('property_droning')
    property_survey = form_data.get('property_survey')
    consultations_and_revisions_amount = form_data.get('consultations_and_revisions_amount_hour')
    other = form_data.get('other')
    describe_other = form_data.get('describe_other')
    project_amount = form_data.get('project_amount')

    # // Billing Info
    payment_options = form_data.get('payment_option')

    # //credit card
    amount_to_charge_for_credit_card = form_data.get('amount_to_charge_for_credit_card')
    card_holder_name = form_data.get('card_holder_name')
    credit_card_number = form_data.get('credit_card_number')
    expiration_date = form_data.get('expiration_date')
    billing_zip_code = form_data.get('billing_zip_code')
    CVV = form_data.get('cvv')

    # //zelle
    amount_to_charge_for_zelle = form_data.get('amount_to_charge_for_zelle')

    # //cash
    amount_to_charge_for_cash = form_data.get('amount_to_charge_for_cash')

    # //check
    amount_to_charge_for_check = form_data.get('amount_to_charge_for_check')
    check_number = form_data.get('check_number')

    location = Location.objects.first()
    location_id = location.locationId
    location_name = location.location_name
    location_timezone = location.timezone

    timezone = pytz.timezone(location_timezone)
    submitted_at = datetime.datetime.now(timezone).replace(tzinfo=None)

    all_custom_fields = get_all_custom_fields(location_id)
    for field in all_custom_fields:
        if field['name'] == 'ReferredBy':
            refferd_by_cf = field['id']
        if field['name'] == 'SecondaryPhone':
            secondary_phone_cf = field['id']
        if field['name'] == 'SecondaryEmail':
            secondary_email_cf = field['id']
        if field['name'] == 'HOA':
            HOA_cf = field['id']
        if field['name'] == 'Plot Plan':
            plot_plan_cf = field['id']
        if field['name'] == 'Hardscape (2D & 3D)':
            hardscape_cf = field['id']
        if field['name'] == 'Hardscape & Planting':
            hardscape_and_planning_cf = field['id']
        if field['name'] == 'Above Plans plus (Irrigation, Drainage and Lighting)':
            above_plans_plus_cf = field['id']
        if field['name'] == 'Measuring for site plan':
            measuring_for_site_plan_cf = field['id']
        if field['name'] == 'Property Droning':
            property_droning_cf = field['id']
        if field['name'] == 'Property Survey (price determined per job)':
            property_survey_cf = field['id']
        if field['name'] == 'Consultations And Revisions Amount':
            consultations_and_revisions_amount_cf = field['id']
        if field['name'] == 'Other':
            other_cf = field['id']
        if field['name'] == 'Describe Other':
            describe_other_cf = field['id']
        if field['name'] == 'Project Amount':
            project_amount_cf = field['id']
        if field['name'] == 'Payment Options':
            payment_options_cf = field['id']
        if field['name'] == 'Amount to charge for Credit Card':
            amount_to_charge_for_credit_card_cf = field['id']
        if field['name'] == 'Amount to charge for Zelle':
            amount_to_charge_for_zelle_cf = field['id']
        if field['name'] == 'Amount to charge for cash':
            amount_to_charge_for_cash_cf = field['id']
        if field['name'] == 'Amount to charge for check':
            amount_to_charge_for_check_cf = field['id']
        if field['name'] == 'Check Number':
            check_number_cf = field['id']
        if field['name'] == 'Client Signature':
            client_signature_cf = field['id']
        if field['name'] == 'Representative Signature':
            representative_signature_cf = field['id']
        if field['name'] == 'Agreement':
            agreement_cf = field['id']
        if field['name'] == 'ReferredBy':
            refferd_by_cf = field['id']
        if field['name'] == 'Client Signature Form Link':
            client_signature_form_link_cf = field['id']

    defaults = {
        'project_id' : project_id,
        'location_id': location_id,
        'location_name': location_name,
        'name': client_name,
        'primary_phone': primary_phone,
        'primary_email': primary_email,
        'secondary_phone': secondary_phone,
        'secondary_email': secondary_email,
        'refferd_by': refferd_by,
        'address': address,
        'city': city,
        'state': state,
        'zip': zip,
        'hoa': HOA,
        'plot_plan': plot_plan,
        'hardscape_2d_3d': hardscape,
        'hardscape_and_planting': hardscape_and_planning,
        'above_plan_plus': above_plans_plus,
        'measuring_for_site_plan': measuring_for_site_plan,
        'property_droning': property_droning,
        'property_survey': property_survey,
        'consultations_and_revisions_amount_hour': consultations_and_revisions_amount,
        'other': other,
        'describe_other': describe_other,
        'project_amount': project_amount,
        'payment_option': payment_options,
        'amount_to_charge_for_credit_card': amount_to_charge_for_credit_card,
        'card_holder_name': card_holder_name,
        'credit_card_number': credit_card_number,
        'billing_zip_code': billing_zip_code,
        'cvv': CVV,
        'amount_to_charge_for_zelle': amount_to_charge_for_zelle,
        'amount_to_charge_for_cash': amount_to_charge_for_cash,
        'amount_to_charge_for_check': amount_to_charge_for_check,
        'check_number': check_number,
        'modified_at': submitted_at.date(),
    }
    if expiration_date and expiration_date != 'null':
        try:
            defaults['expiration_date'] = expiration_date
        except:
            pass
        try:
            defaults['expiration_date_str'] = expiration_date
        except:
            pass

    if client_signature and client_signature != 'null':
        # defaults['client_signature'] = client_signature
        defaults['client_signed_date'] = submitted_at.date()

    if representative_signature and representative_signature != 'null':
        # defaults['representative_signature'] = representative_signature
        defaults['representative_signed_date'] = submitted_at.date()
    
    # if agreement:
    #     defaults['pdf'] = agreement

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    if not project_id:
        current_year = datetime.datetime.now().year
        # Extract last two digits of the year
        year_short = str(current_year)[-2:]
        # Find the project with the largest sequence number for the current year
        last_project = Contact.objects.filter(project_id__startswith=year_short).order_by('-project_id').first()

        if last_project:
            # Extract the sequence number from the project_id (e.g., 24-001 -> 001)
            last_sequence = int(last_project.project_id.split('-')[1])
            next_sequence = last_sequence + 1
        else:
            # If no project exists for the current year, start with 1
            next_sequence = 1

        # Generate the new project_id in the format YY-XXX
        project_id = f"{year_short}-{str(next_sequence).zfill(3)}"

        client_signature_form_link = f'https://main.d2f78myqkxzqx9.amplifyapp.com/client-signature/{project_id}'


        defaults['project_id'] = project_id
        defaults['submitted_at'] = submitted_at.date()
        
        url = "https://services.leadconnectorhq.com/contacts/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        data = {
            "name": client_name,
            "email" : primary_email,
            "phone" : primary_phone,
            "address1" : address,
            "city" : city,
            "state" : state,
            "locationId": location_id,
            "customFields": [
                {
                    "id": refferd_by_cf,
                    "field_value": refferd_by
                },
                {
                    "id": secondary_phone_cf,
                    "field_value": secondary_phone
                },
                {
                    "id": secondary_email_cf,
                    "field_value": secondary_email
                },
                {
                    "id": HOA_cf,
                    "field_value": HOA
                },
                {
                    "id": plot_plan_cf,
                    "field_value": plot_plan
                },
                {
                    "id": hardscape_cf,
                    "field_value": hardscape
                },
                {
                    "id": hardscape_and_planning_cf,
                    "field_value": hardscape_and_planning
                },
                {
                    "id": above_plans_plus_cf,
                    "field_value": above_plans_plus
                },
                {
                    "id": measuring_for_site_plan_cf,
                    "field_value": measuring_for_site_plan
                },
                {
                    "id": property_droning_cf,
                    "field_value": property_droning
                },
                {
                    "id": property_survey_cf,
                    "field_value": property_survey
                },
                {
                    "id": consultations_and_revisions_amount_cf,
                    "field_value": consultations_and_revisions_amount
                },
                {
                    "id": other_cf,
                    "field_value": other
                },
                {
                    "id": describe_other_cf,
                    "field_value": describe_other
                },
                {
                    "id": project_amount_cf,
                    "field_value": project_amount
                },
                {
                    "id": payment_options_cf,
                    "field_value": payment_options
                },
                {
                    "id": amount_to_charge_for_credit_card_cf,
                    "field_value": amount_to_charge_for_credit_card
                },
                {
                    "id": amount_to_charge_for_zelle_cf,
                    "field_value": amount_to_charge_for_zelle
                },
                {
                    "id": amount_to_charge_for_cash_cf,
                    "field_value": amount_to_charge_for_cash
                },
                {
                    "id": amount_to_charge_for_check_cf,
                    "field_value": amount_to_charge_for_check
                },
                {
                    "id": check_number_cf,
                    "field_value": check_number
                },
                {
                    "id": client_signature_form_link_cf,
                    "field_value": client_signature_form_link
                }
            ]
        }

        print(data)
        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            contact_data = response.json()
            contact = contact_data.get('contact')
            contact_id = contact['id']
            print(contact_id)

            # Use update_or_create method
            new_contact, created = Contact.objects.update_or_create(
                contact_id=contact_id,
                defaults=defaults
            )

            print('contact created')
            serializer = ContactSerializerV2(new_contact)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            error_response = response.json()
            print(error_response)
            message = error_response.get('message')
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
    else:
        client_signature_form_link = f'https://main.d2f78myqkxzqx9.amplifyapp.com/client-signature/{project_id}'
        contact_id = Contact.objects.get(project_id=project_id).contact_id

        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }

        data = {
            "name": client_name,
            "email" : primary_email,
            "customFields": [
                {
                    "id": refferd_by_cf,
                    "field_value": refferd_by
                },
                {
                    "id": secondary_phone_cf,
                    "field_value": secondary_phone
                },
                {
                    "id": secondary_email_cf,
                    "field_value": secondary_email
                },
                {
                    "id": HOA_cf,
                    "field_value": HOA
                },
                {
                    "id": plot_plan_cf,
                    "field_value": plot_plan
                },
                {
                    "id": hardscape_cf,
                    "field_value": hardscape
                },
                {
                    "id": hardscape_and_planning_cf,
                    "field_value": hardscape_and_planning
                },
                {
                    "id": above_plans_plus_cf,
                    "field_value": above_plans_plus
                },
                {
                    "id": measuring_for_site_plan_cf,
                    "field_value": measuring_for_site_plan
                },
                {
                    "id": property_droning_cf,
                    "field_value": property_droning
                },
                {
                    "id": property_survey_cf,
                    "field_value": property_survey
                },
                {
                    "id": consultations_and_revisions_amount_cf,
                    "field_value": consultations_and_revisions_amount
                },
                {
                    "id": other_cf,
                    "field_value": other
                },
                {
                    "id": describe_other_cf,
                    "field_value": describe_other
                },
                {
                    "id": project_amount_cf,
                    "field_value": project_amount
                },
                {
                    "id": payment_options_cf,
                    "field_value": payment_options
                },
                {
                    "id": amount_to_charge_for_credit_card_cf,
                    "field_value": amount_to_charge_for_credit_card
                },
                {
                    "id": amount_to_charge_for_zelle_cf,
                    "field_value": amount_to_charge_for_zelle
                },
                {
                    "id": amount_to_charge_for_cash_cf,
                    "field_value": amount_to_charge_for_cash
                },
                {
                    "id": amount_to_charge_for_check_cf,
                    "field_value": amount_to_charge_for_check
                },
                {
                    "id": check_number_cf,
                    "field_value": check_number
                },
                {
                    "id": client_signature_form_link_cf,
                    "field_value": client_signature_form_link
                }
            ]
        }

        if primary_phone:
            data['phone'] = primary_phone
        if address:
            data['address1'] = address
        if city:
            data['city'] = city
        if state:
            data['state'] = state

        print(data)
        response = requests.put(url, headers=headers, json=data)
        if response.ok:
            # Use update_or_create method
            update_contact, created = Contact.objects.update_or_create(
                contact_id=contact_id,
                defaults=defaults
            )
            
            serializer = ContactSerializerV2(update_contact)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            error_response = response.json()
            print(error_response)
            message = error_response.get('message')
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
        
def update_contact_file_customfields(location_id, contact_id, client_signature_cf=None, representative_signature_cf=None, agreement_cf=None):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)

    location = Location.objects.get(locationId=location_id)
    access_token = location.access_token

    contact = Contact.objects.get(contact_id=contact_id)

    custom_fields = []

    # Add client signature if available
    if client_signature_cf and contact.client_signature:
        client_signature_link = f'{settings.BASE_URL}{contact.client_signature.url}'
        custom_fields.append({
            "id": client_signature_cf,
            "field_value": {
                str(uuid.uuid4()): {
                    "meta": {
                        "fieldname": client_signature_cf,
                        "originalname": 'client_signature',
                        "mimetype": "image/png",
                        "uuid": str(uuid.uuid4())
                    },
                    "url": client_signature_link
                }
            }
        })

    # Add representative signature if available
    if representative_signature_cf and contact.representative_signature:
        representative_signature_link = f'{settings.BASE_URL}{contact.representative_signature.url}'
        custom_fields.append({
            "id": representative_signature_cf,
            "field_value": {
                str(uuid.uuid4()): {
                    "meta": {
                        "fieldname": representative_signature_cf,
                        "originalname": 'representative_signature',
                        "mimetype": "image/png",
                        "uuid": str(uuid.uuid4())
                    },
                    "url": representative_signature_link
                }
            }
        })

    # Add agreement if available
    if agreement_cf and contact.pdf:
        agreement_link = f'{settings.BASE_URL}{contact.pdf.url}'
        custom_fields.append({
            "id": agreement_cf,
            "field_value": {
                str(uuid.uuid4()): {
                    "meta": {
                        "fieldname": agreement_cf,
                        "originalname": f'{contact.name}_agreement.pdf',
                        "mimetype": "application/pdf",
                        "uuid": str(uuid.uuid4())
                    },
                    "url": agreement_link
                }
            }
        })

    # If there are any custom fields to update, make the API call
    if custom_fields:
        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }

        data = {
            "customFields": custom_fields
        }

        response = requests.put(url, headers=headers, json=data)
        if response.ok:
            print('Custom fields updated successfully')
        else:
            print('Failed to update custom fields')
    else:
        print('No custom fields to update')
        
def update_contact_client_signatures(location_id, contact_id, client_signature_cf):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    contact = Contact.objects.get(contact_id=contact_id)
    if contact.client_signature:
        client_signature_link = f'{settings.BASE_URL}{contact.client_signature.url}'
    else:
        client_signature_link = None

    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    data = {
            "customFields": [
                {
                    "id": client_signature_cf,
                    "field_value": {
                        str(uuid.uuid4()): {
                            "meta": {
                                "fieldname": client_signature_cf,
                                "originalname": 'client_signature',
                                "mimetype": "image/png",
                                "uuid": str(uuid.uuid4())
                            },
                            "url": client_signature_link
                        }
                    }
                }
            ]
    }

    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        print('Client signatures uploaded')
    else:
        print('Failed to upload Client signatures')

def update_contact_representative_signatures(location_id, contact_id, representative_signature_cf):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    contact = Contact.objects.get(contact_id=contact_id)
    if contact.representative_signature:
        representative_signature_link = f'{settings.BASE_URL}{contact.representative_signature.url}'
    else:
        representative_signature_link = None

    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    data = {
            "customFields": [
                {
                    "id": representative_signature_cf,
                    "field_value": {
                        str(uuid.uuid4()): {
                            "meta": {
                                "fieldname": representative_signature_cf,
                                "originalname": 'representative_signature',
                                "mimetype": "image/png",
                                "uuid": str(uuid.uuid4())
                            },
                            "url": representative_signature_link
                        }
                    }
                }
            ]
    }

    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        print('Representative signatures uploaded')
    else:
        print('Failed to upload Representative signatures')

def update_contact_signatures(location_id, contact_id, client_signature_cf, representative_signature_cf):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    contact = Contact.objects.get(contact_id=contact_id)
    if contact.client_signature:
        client_signature_link = f'{settings.BASE_URL}{contact.client_signature.url}'
    else:
        client_signature_link = None
    
    if contact.representative_signature:
        representative_signature_link = f'{settings.BASE_URL}{contact.representative_signature.url}'
    else:
        representative_signature_link = None

    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    data = {
            "customFields": [
                {
                    "id": client_signature_cf,
                    "field_value": {
                        str(uuid.uuid4()): {
                            "meta": {
                                "fieldname": client_signature_cf,
                                "originalname": 'client_signature',
                                "mimetype": "image/png",
                                "uuid": str(uuid.uuid4())
                            },
                            "url": client_signature_link
                        }
                    }
                },
                {
                    "id": representative_signature_cf,
                    "field_value": {
                        str(uuid.uuid4()): {
                            "meta": {
                                "fieldname": representative_signature_cf,
                                "originalname": 'representative_signature',
                                "mimetype": "image/png",
                                "uuid": str(uuid.uuid4())
                            },
                            "url": representative_signature_link
                        }
                    }
                }
            ]
    }

    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        print('signatures uploaded')
    else:
        print('Failed to upload signatures')


def update_contact_agreement(location_id, contact_id, agreement_cf):

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    contact = Contact.objects.get(contact_id=contact_id)
    if contact.pdf:
        agreement_link = f'{settings.BASE_URL}{contact.pdf.url}'
    else:
        agreement_link = None

    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    data = {
            "customFields": [
                {
                    "id": agreement_cf,
                    "field_value": {
                        str(uuid.uuid4()): {
                            "meta": {
                                "fieldname": agreement_cf,
                                "originalname": f'{contact.name}_agreement.pdf',
                                "mimetype": "application/pdf",
                                "uuid": str(uuid.uuid4())
                            },
                            "url": agreement_link
                        }
                    }
                }
            ]
    }

    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        print('Agreement uploaded')
    else:
        print('Failed to upload Agreement')


@api_view(['GET'])
def historic(request):
    historic_fetch.delay()
    return Response('started', status=status.HTTP_200_OK)

@api_view(['GET'])
def fetch_users(request):
    location = Location.objects.first()
    location_id = location.locationId
    fetch_users_by_location.delay(location_id)
    return Response('started', status=status.HTTP_200_OK)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_agreement_v2(request):
    print(request.data)
    # Extract form data
    project_id = request.data.get('project_id')
    if not project_id:
        contact_id = request.data.get('contact_id')
    # Extract files
    agreement = request.FILES.get('pdf')
    client_signature = request.FILES.get('signature')
    representative_signature = request.FILES.get('representative_sign')

    if project_id:
        contact = Contact.objects.get(project_id=project_id)
    else:
        contact = Contact.objects.get(contact_id=contact_id)

    contact_id = contact.contact_id

    # Define storage folder path
    agreement_folder_path = os.path.join(settings.MEDIA_ROOT, 'agreements')
    signature_folder_path = os.path.join(settings.MEDIA_ROOT, 'signatures')
    if not os.path.exists(agreement_folder_path):
        os.makedirs(agreement_folder_path)
    if not os.path.exists(signature_folder_path):
        os.makedirs(signature_folder_path)
    

    # If it's a PDF, create/overwrite the file in the folder
    pdf_path = os.path.join(agreement_folder_path, f'agreement.pdf')
    with default_storage.open(pdf_path, 'wb+') as destination:
        for chunk in agreement.chunks():
            destination.write(chunk)

    agreement_file = upload_agreement_file(contact_id)
    if not agreement_file:
        return Response('Failed to upload the media file', status=400)

    agreement_file_details = get_agreement_file(contact_id, agreement_file)
    if not agreement_file_details:
        return Response('Failed to get file details', status=400)
    
    if client_signature and client_signature != 'null':
        client_signature_path = os.path.join(signature_folder_path, f'client_signature.png')
        with default_storage.open(client_signature_path, 'wb+') as destination:
            for chunk in client_signature.chunks():
                destination.write(chunk)
        
        client_signature_file_name = 'client_signature.png'
        client_signature_file = upload_signature_file(contact_id, client_signature_file_name)
        if not client_signature_file:
            return Response('Failed to upload the client_signature file', status=400)

        client_signature_details = get_signature_file(contact_id, client_signature_file, client_signature_file_name)
        if not client_signature_details:
            return Response('Failed to get client_signature file details', status=400)

    if representative_signature and representative_signature != 'null':
        representative_signature_path = os.path.join(signature_folder_path, f'representative_signature.png')
        with default_storage.open(representative_signature_path, 'wb+') as destination:
            for chunk in representative_signature.chunks():
                destination.write(chunk)

        representative_signature_file_name = 'representative_signature.png'
        representative_signature_file = upload_signature_file(contact_id, representative_signature_file_name)
        if not representative_signature_file:
            return Response('Failed to upload the representative_signature file', status=400)

        representative_signature_details = get_signature_file(contact_id, representative_signature_file, representative_signature_file_name)
        if not representative_signature_details:
            return Response('Failed to get representative_signature file details', status=400)

    try:
        client_signature_link = client_signature_details['file_link']
    except:
        client_signature_link = None

    try:
        representative_signature_link = representative_signature_details['file_link']
    except:
        representative_signature_link = None

    upload_cf_files = update_contact_file_customfields_v2(contact_id, agreement_file_details['file_link'], client_signature_link, representative_signature_link)
    if upload_cf_files:
        if client_signature_link:
            contact.client_signature_url = client_signature_link
        if representative_signature_link:
            contact.representative_signature_url = representative_signature_link
        contact.pdf_url = agreement_file_details['file_link']
        contact.save()
        serializer = ContactSerializerV2(contact)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)
    else:
        return Response('Failed to upload the files to CF', status=400)


def upload_agreement_file(contact_id):
    location = Location.objects.first()
    location_id = location.locationId

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)

    location = Location.objects.get(locationId=location_id)
    access_token = location.access_token

    url = 'https://services.leadconnectorhq.com/medias/upload-file'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'version': '2021-07-28'
    }

    files = {
        'file': (f'{contact_id}_agreement.pdf', open(str(settings.BASE_DIR) + f'/media/agreements/agreement.pdf', 'rb'))
    }

    response = requests.post(url, headers=headers, files=files)
    if response.status_code == 201:
        data = response.json()
        return data['fileId']
    else:
        print(response.json())
        return False

def get_agreement_file(contact_id, media_file):
    location = Location.objects.first()
    location_id = location.locationId

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)

    location = Location.objects.get(locationId=location_id)
    access_token = location.access_token

    url = 'https://services.leadconnectorhq.com/medias/files'
    params = {
        'sortBy': 'createdAt',
        'sortOrder': 'desc',
        'altType': 'location',
        'altId': media_file,
        'query': f'{contact_id}_agreement.pdf'
    }

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'version': '2021-07-28'
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        file = data['files'][0]
        print(file)
        return{
            "file_name": file['name'],
            "file_link": file['url']
        }
    else:
        return False
    
def upload_signature_file(contact_id, filename):
    location = Location.objects.first()
    location_id = location.locationId

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)

    location = Location.objects.get(locationId=location_id)
    access_token = location.access_token

    url = 'https://services.leadconnectorhq.com/medias/upload-file'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'version': '2021-07-28'
    }

    files = {
        'file': (f'{contact_id}_{filename}', open(str(settings.BASE_DIR) + f'/media/signatures/{filename}', 'rb'))
    }

    response = requests.post(url, headers=headers, files=files)
    if response.status_code == 201:
        data = response.json()
        return data['fileId']
    else:
        print(response.json())
        return False

def get_signature_file(contact_id, media_file, filename):
    location = Location.objects.first()
    location_id = location.locationId

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)

    location = Location.objects.get(locationId=location_id)
    access_token = location.access_token

    url = 'https://services.leadconnectorhq.com/medias/files'
    params = {
        'sortBy': 'createdAt',
        'sortOrder': 'desc',
        'altType': 'location',
        'altId': media_file,
        'query': f'{contact_id}_{filename}'
    }

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'version': '2021-07-28'
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        file = data['files'][0]
        print(file)
        return{
            "file_name": file['name'],
            "file_link": file['url']
        }
    else:
        return False
    
def update_contact_file_customfields_v2(contact_id, agreement_file_link, client_signature_link, representative_signature_link):
    location = Location.objects.first()
    location_id = location.locationId

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)

    location = Location.objects.get(locationId=location_id)
    access_token = location.access_token

    contact = Contact.objects.get(contact_id=contact_id)

    all_custom_fields = get_all_custom_fields(location_id)
    for field in all_custom_fields:
        if field['name'] == 'Client Signature':
            client_signature_cf = field['id']
        if field['name'] == 'Representative Signature':
            representative_signature_cf = field['id']
        if field['name'] == 'Agreement':
            agreement_cf = field['id']
    
    custom_fields = [
        {
            "id": agreement_cf,
            "field_value": {
                str(uuid.uuid4()): {
                    "meta": {
                        "fieldname": agreement_cf,
                        "originalname": f'{contact.name}_agreement.pdf',
                        "mimetype": "application/pdf",
                        "uuid": str(uuid.uuid4())
                    },
                    "url": agreement_file_link
                }
            }
        }
        
    ]

    if client_signature_link:
        custom_fields.append({
            "id": client_signature_cf,
            "field_value": {
                str(uuid.uuid4()): {
                    "meta": {
                        "fieldname": client_signature_cf,
                        "originalname": 'client_signature',
                        "mimetype": "image/png",
                        "uuid": str(uuid.uuid4())
                    },
                    "url": client_signature_link
                }
            }
        })

    if representative_signature_link:
        custom_fields.append({
            "id": representative_signature_cf,
            "field_value": {
                str(uuid.uuid4()): {
                    "meta": {
                        "fieldname": representative_signature_cf,
                        "originalname": 'representative_signature',
                        "mimetype": "image/png",
                        "uuid": str(uuid.uuid4())
                    },
                    "url": representative_signature_link
                }
            }
        })



    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    
    data = {
        "customFields": custom_fields
    }

    response = requests.put(url, json=data, headers=headers)

    if response.status_code == 200:        
        return True
    else:
        print("Error occured while uploading file to custom field")
        print(response.json())
        return False
    
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_client_signature_v2(request):
    form_data = request.data
    
    client_signature = request.FILES.get('signature')
    agreement = request.FILES.get('pdf')

    contact_id = form_data.get('contact_id')

    contact = Contact.objects.get(contact_id=contact_id)

    agreement_folder_path = os.path.join(settings.MEDIA_ROOT, 'agreements')
    signature_folder_path = os.path.join(settings.MEDIA_ROOT, 'signatures')
    if not os.path.exists(agreement_folder_path):
        os.makedirs(agreement_folder_path)
    if not os.path.exists(signature_folder_path):
        os.makedirs(signature_folder_path)

    # If it's a PDF, create/overwrite the file in the folder
    pdf_path = os.path.join(agreement_folder_path, f'agreement.pdf')
    with default_storage.open(pdf_path, 'wb+') as destination:
        for chunk in agreement.chunks():
            destination.write(chunk)

    agreement_file = upload_agreement_file(contact_id)
    if not agreement_file:
        return Response('Failed to upload the media file', status=400)

    agreement_file_details = get_agreement_file(contact_id, agreement_file)
    if not agreement_file_details:
        return Response('Failed to get file details', status=400)
    
    if client_signature and client_signature != 'null':
        client_signature_path = os.path.join(signature_folder_path, f'client_signature.png')
        with default_storage.open(client_signature_path, 'wb+') as destination:
            for chunk in client_signature.chunks():
                destination.write(chunk)
        
        client_signature_file_name = 'client_signature.png'
        client_signature_file = upload_signature_file(contact_id, client_signature_file_name)
        if not client_signature_file:
            return Response('Failed to upload the client_signature file', status=400)

        client_signature_details = get_signature_file(contact_id, client_signature_file, client_signature_file_name)
        if not client_signature_details:
            return Response('Failed to get client_signature file details', status=400)
        
    try:
        client_signature_link = client_signature_details['file_link']
    except:
        client_signature_link = None

    representative_signature_link=None

    upload_cf_files = update_contact_file_customfields_v2(contact_id, agreement_file_details['file_link'], client_signature_link, representative_signature_link)
    if upload_cf_files:
        contact.client_signature_url = client_signature_link
        contact.pdf_url = agreement_file_details['file_link']
        contact.save()
        serializer = ContactSerializerV2(contact)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)
    else:
        return Response('Failed to upload the files to CF', status=400)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_client_signature(request):
    form_data = request.data
    
    client_signature = request.FILES.get('signature')
    agreement = request.FILES.get('pdf')

    project_id = form_data.get('project_id')

    contact = Contact.objects.get(project_id=project_id)
    contact_id = contact.contact_id

    agreement_folder_path = os.path.join(settings.MEDIA_ROOT, 'agreements')
    signature_folder_path = os.path.join(settings.MEDIA_ROOT, 'signatures')
    if not os.path.exists(agreement_folder_path):
        os.makedirs(agreement_folder_path)
    if not os.path.exists(signature_folder_path):
        os.makedirs(signature_folder_path)

    # If it's a PDF, create/overwrite the file in the folder
    pdf_path = os.path.join(agreement_folder_path, f'agreement.pdf')
    with default_storage.open(pdf_path, 'wb+') as destination:
        for chunk in agreement.chunks():
            destination.write(chunk)

    agreement_file = upload_agreement_file(contact_id)
    if not agreement_file:
        return Response('Failed to upload the media file', status=400)

    agreement_file_details = get_agreement_file(contact_id, agreement_file)
    if not agreement_file_details:
        return Response('Failed to get file details', status=400)
    
    if client_signature and client_signature != 'null':
        client_signature_path = os.path.join(signature_folder_path, f'client_signature.png')
        with default_storage.open(client_signature_path, 'wb+') as destination:
            for chunk in client_signature.chunks():
                destination.write(chunk)
        
        client_signature_file_name = 'client_signature.png'
        client_signature_file = upload_signature_file(contact_id, client_signature_file_name)
        if not client_signature_file:
            return Response('Failed to upload the client_signature file', status=400)

        client_signature_details = get_signature_file(contact_id, client_signature_file, client_signature_file_name)
        if not client_signature_details:
            return Response('Failed to get client_signature file details', status=400)
        
    try:
        client_signature_link = client_signature_details['file_link']
    except:
        client_signature_link = None

    representative_signature_link=None

    upload_cf_files = update_contact_file_customfields_v2(contact_id, agreement_file_details['file_link'], client_signature_link, representative_signature_link)
    if upload_cf_files:
        contact.client_signature_url = client_signature_link
        contact.pdf_url = agreement_file_details['file_link']
        contact.save()
        serializer = ContactSerializerV2(contact)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)
    else:
        return Response('Failed to upload the files to CF', status=400)
    
@api_view(['POST'])
def delete_current_client_v2(request, contact_id):
    contact = Contact.objects.get(contact_id=contact_id)
    contact.archived = True
    contact.save()
    return Response('success', status=status.HTTP_200_OK)

@api_view(['POST'])
def delete_current_client(request, project_id):
    contact = Contact.objects.get(project_id=project_id)
    contact.archived = True
    contact.save()
    return Response('success', status=status.HTTP_200_OK)

@api_view(['POST'])
def ghl_webhook(request):
    print(request.data)
    data = request.data
    location_id = data.get('locationId')
    try:
        location_timezone = Location.objects.get(locationId = location_id).timezone
    except:
        location_timezone = None

    if location_timezone:
        type = data.get('type')
        if type == 'TaskComplete':
            task_id = data.get('id')
            try:
                task = Task.objects.get(task_id=task_id)
            except:
                task = None
                print('No task found')
            
            if task:
                user_id = data.get('assignedTo')
                if user_id:
                    assigned_user_name = User.objects.get(user_id=user_id).name
                else:
                    assigned_user_name = None
                title = data.get('title')
                due_date = data.get('dueDate')

                try:
                    naive_due_date = datetime.datetime.fromisoformat(due_date[:-1])
                except:
                    try:
                        naive_due_date = datetime.datetime.strptime(due_date, '%Y-%m-%dT%H:%M:%S')
                    except:
                        naive_due_date = datetime.datetime.strptime(due_date, '%Y-%m-%d')

                input_timezone = pytz.timezone("UTC")
                due_date_obj = input_timezone.localize(naive_due_date)
                target_timezone = pytz.timezone(location_timezone)
                due_date_in_location_time_zone = due_date_obj.astimezone(target_timezone).replace(tzinfo=None).date()

                task.completed = True
                task.assigned_to_id = user_id
                task.assigned_to = assigned_user_name
                task.name = title
                task.due_date = due_date_in_location_time_zone
                task.save()
                print('Task completed')

    return Response('Success', status=status.HTTP_200_OK)

@api_view(['GET'])
def get_gantt_chart(request, project_id):
    contact = Contact.objects.get(project_id=project_id)
    all_tasks = Task.objects.filter(contact=contact).order_by('created_at')
    payload = {
        'project_id': project_id,
        'start': all_tasks.first().start_date,
        'end': all_tasks.latest('due_date').due_date,
        'tasks': []
    }
    order = 0
    for task in all_tasks:
        order += 1
        task_data = {
            'start': task.start_date,
            'end': task.due_date,
            'name': task.name,
            'category': task.category,
            'id': task.task_id,
            'progress': 100 if task.completed else 0,
            'assigned_user': task.assigned_to,
            'type': 'task',
            'displayOrder': order
        }

        payload['tasks'].append(task_data)

    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_form_data_v2(request):
    print(request.data)
    form_data = request.data


    client_signature = request.FILES.get('signature')
    representative_signature = request.FILES.get('representative_sign')
    agreement = request.FILES.get('pdf')
    
    # Extract form data from the parsed JSON
    contact_id = form_data.get('contact_id')
    project_id = form_data.get('project_id')
    print(contact_id)
    refferd_by = form_data.get('refferd_by')
    client_name = form_data.get('name')
    address = form_data.get('address')
    city = form_data.get('city')
    state = form_data.get('state')
    zip = form_data.get('zip')
    primary_phone = form_data.get('primary_phone')
    secondary_phone = form_data.get('secondary_phone')
    primary_email = form_data.get('primary_email')
    secondary_email = form_data.get('secondary_email')

    # // Project Info
    HOA = form_data.get('hoa')
    plot_plan = form_data.get('plot_plan')
    hardscape = form_data.get('hardscape_2d_3d')
    hardscape_and_planning = form_data.get('hardscape_and_planting')
    above_plans_plus = form_data.get('above_plan_plus')
    measuring_for_site_plan = form_data.get('measuring_for_site_plan')
    property_droning = form_data.get('property_droning')
    property_survey = form_data.get('property_survey')
    consultations_and_revisions_amount = form_data.get('consultations_and_revisions_amount_hour')
    other = form_data.get('other')
    describe_other = form_data.get('describe_other')
    project_amount = form_data.get('project_amount')

    # // Billing Info
    payment_options = form_data.get('payment_option')

    # //credit card
    amount_to_charge_for_credit_card = form_data.get('amount_to_charge_for_credit_card')
    card_holder_name = form_data.get('card_holder_name')
    credit_card_number = form_data.get('credit_card_number')
    expiration_date = form_data.get('expiration_date')
    billing_zip_code = form_data.get('billing_zip_code')
    CVV = form_data.get('cvv')

    # //zelle
    amount_to_charge_for_zelle = form_data.get('amount_to_charge_for_zelle')

    # //cash
    amount_to_charge_for_cash = form_data.get('amount_to_charge_for_cash')

    # //check
    amount_to_charge_for_check = form_data.get('amount_to_charge_for_check')
    check_number = form_data.get('check_number')

    location = Location.objects.first()
    location_id = location.locationId
    location_name = location.location_name
    location_timezone = location.timezone

    timezone = pytz.timezone(location_timezone)
    submitted_at = datetime.datetime.now(timezone).replace(tzinfo=None)

    all_custom_fields = get_all_custom_fields(location_id)
    for field in all_custom_fields:
        if field['name'] == 'ReferredBy':
            refferd_by_cf = field['id']
        if field['name'] == 'SecondaryPhone':
            secondary_phone_cf = field['id']
        if field['name'] == 'SecondaryEmail':
            secondary_email_cf = field['id']
        if field['name'] == 'HOA':
            HOA_cf = field['id']
        if field['name'] == 'Plot Plan':
            plot_plan_cf = field['id']
        if field['name'] == 'Hardscape (2D & 3D)':
            hardscape_cf = field['id']
        if field['name'] == 'Hardscape & Planting':
            hardscape_and_planning_cf = field['id']
        if field['name'] == 'Above Plans plus (Irrigation, Drainage and Lighting)':
            above_plans_plus_cf = field['id']
        if field['name'] == 'Measuring for site plan':
            measuring_for_site_plan_cf = field['id']
        if field['name'] == 'Property Droning':
            property_droning_cf = field['id']
        if field['name'] == 'Property Survey (price determined per job)':
            property_survey_cf = field['id']
        if field['name'] == 'Consultations And Revisions Amount':
            consultations_and_revisions_amount_cf = field['id']
        if field['name'] == 'Other':
            other_cf = field['id']
        if field['name'] == 'Describe Other':
            describe_other_cf = field['id']
        if field['name'] == 'Project Amount':
            project_amount_cf = field['id']
        if field['name'] == 'Payment Options':
            payment_options_cf = field['id']
        if field['name'] == 'Amount to charge for Credit Card':
            amount_to_charge_for_credit_card_cf = field['id']
        if field['name'] == 'Amount to charge for Zelle':
            amount_to_charge_for_zelle_cf = field['id']
        if field['name'] == 'Amount to charge for cash':
            amount_to_charge_for_cash_cf = field['id']
        if field['name'] == 'Amount to charge for check':
            amount_to_charge_for_check_cf = field['id']
        if field['name'] == 'Check Number':
            check_number_cf = field['id']
        if field['name'] == 'Client Signature':
            client_signature_cf = field['id']
        if field['name'] == 'Representative Signature':
            representative_signature_cf = field['id']
        if field['name'] == 'Agreement':
            agreement_cf = field['id']
        if field['name'] == 'ReferredBy':
            refferd_by_cf = field['id']
        if field['name'] == 'Client Signature Form Link':
            client_signature_form_link_cf = field['id']

    defaults = {
        'project_id' : project_id,
        'location_id': location_id,
        'location_name': location_name,
        'name': client_name,
        'primary_phone': primary_phone,
        'primary_email': primary_email,
        'secondary_phone': secondary_phone,
        'secondary_email': secondary_email,
        'refferd_by': refferd_by,
        'address': address,
        'city': city,
        'state': state,
        'zip': zip,
        'hoa': HOA,
        'plot_plan': plot_plan,
        'hardscape_2d_3d': hardscape,
        'hardscape_and_planting': hardscape_and_planning,
        'above_plan_plus': above_plans_plus,
        'measuring_for_site_plan': measuring_for_site_plan,
        'property_droning': property_droning,
        'property_survey': property_survey,
        'consultations_and_revisions_amount_hour': consultations_and_revisions_amount,
        'other': other,
        'describe_other': describe_other,
        'project_amount': project_amount,
        'payment_option': payment_options,
        'amount_to_charge_for_credit_card': amount_to_charge_for_credit_card,
        'card_holder_name': card_holder_name,
        'credit_card_number': credit_card_number,
        'billing_zip_code': billing_zip_code,
        'cvv': CVV,
        'amount_to_charge_for_zelle': amount_to_charge_for_zelle,
        'amount_to_charge_for_cash': amount_to_charge_for_cash,
        'amount_to_charge_for_check': amount_to_charge_for_check,
        'check_number': check_number,
        'modified_at': submitted_at.date(),
    }
    if expiration_date and expiration_date != 'null':
        try:
            defaults['expiration_date'] = expiration_date
        except:
            pass
        try:
            defaults['expiration_date_str'] = expiration_date
        except:
            pass

    if client_signature and client_signature != 'null':
        # defaults['client_signature'] = client_signature
        defaults['client_signed_date'] = submitted_at.date()

    if representative_signature and representative_signature != 'null':
        # defaults['representative_signature'] = representative_signature
        defaults['representative_signed_date'] = submitted_at.date()
    
    # if agreement:
    #     defaults['pdf'] = agreement

    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    if not contact_id:

        defaults['submitted_at'] = submitted_at.date()
        
        url = "https://services.leadconnectorhq.com/contacts/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        data = {
            "name": client_name,
            "email" : primary_email,
            "phone" : primary_phone,
            "address1" : address,
            "city" : city,
            "state" : state,
            "locationId": location_id,
            "customFields": [
                {
                    "id": refferd_by_cf,
                    "field_value": refferd_by
                },
                {
                    "id": secondary_phone_cf,
                    "field_value": secondary_phone
                },
                {
                    "id": secondary_email_cf,
                    "field_value": secondary_email
                },
                {
                    "id": HOA_cf,
                    "field_value": HOA
                },
                {
                    "id": plot_plan_cf,
                    "field_value": plot_plan
                },
                {
                    "id": hardscape_cf,
                    "field_value": hardscape
                },
                {
                    "id": hardscape_and_planning_cf,
                    "field_value": hardscape_and_planning
                },
                {
                    "id": above_plans_plus_cf,
                    "field_value": above_plans_plus
                },
                {
                    "id": measuring_for_site_plan_cf,
                    "field_value": measuring_for_site_plan
                },
                {
                    "id": property_droning_cf,
                    "field_value": property_droning
                },
                {
                    "id": property_survey_cf,
                    "field_value": property_survey
                },
                {
                    "id": consultations_and_revisions_amount_cf,
                    "field_value": consultations_and_revisions_amount
                },
                {
                    "id": other_cf,
                    "field_value": other
                },
                {
                    "id": describe_other_cf,
                    "field_value": describe_other
                },
                {
                    "id": project_amount_cf,
                    "field_value": project_amount
                },
                {
                    "id": payment_options_cf,
                    "field_value": payment_options
                },
                {
                    "id": amount_to_charge_for_credit_card_cf,
                    "field_value": amount_to_charge_for_credit_card
                },
                {
                    "id": amount_to_charge_for_zelle_cf,
                    "field_value": amount_to_charge_for_zelle
                },
                {
                    "id": amount_to_charge_for_cash_cf,
                    "field_value": amount_to_charge_for_cash
                },
                {
                    "id": amount_to_charge_for_check_cf,
                    "field_value": amount_to_charge_for_check
                },
                {
                    "id": check_number_cf,
                    "field_value": check_number
                }
            ]
        }

        print(data)
        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            contact_data = response.json()
            contact = contact_data.get('contact')
            contact_id = contact['id']
            print(contact_id)
            client_signature_form_link = f'https://main.d2f78myqkxzqx9.amplifyapp.com/client-signature/{contact_id}'
            update_client_signature_form_link_cf(location_id, contact_id, client_signature_form_link_cf, client_signature_form_link)

            # Use update_or_create method
            new_contact, created = Contact.objects.update_or_create(
                contact_id=contact_id,
                defaults=defaults
            )

            print('contact created')
            serializer = ContactSerializerV2(new_contact)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            error_response = response.json()
            print(error_response)
            message = error_response.get('message')
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
    else:
        client_signature_form_link = f'https://main.d2f78myqkxzqx9.amplifyapp.com/client-signature/{contact_id}'

        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }

        data = {
            "name": client_name,
            "email" : primary_email,
            "customFields": [
                {
                    "id": refferd_by_cf,
                    "field_value": refferd_by
                },
                {
                    "id": secondary_phone_cf,
                    "field_value": secondary_phone
                },
                {
                    "id": secondary_email_cf,
                    "field_value": secondary_email
                },
                {
                    "id": HOA_cf,
                    "field_value": HOA
                },
                {
                    "id": plot_plan_cf,
                    "field_value": plot_plan
                },
                {
                    "id": hardscape_cf,
                    "field_value": hardscape
                },
                {
                    "id": hardscape_and_planning_cf,
                    "field_value": hardscape_and_planning
                },
                {
                    "id": above_plans_plus_cf,
                    "field_value": above_plans_plus
                },
                {
                    "id": measuring_for_site_plan_cf,
                    "field_value": measuring_for_site_plan
                },
                {
                    "id": property_droning_cf,
                    "field_value": property_droning
                },
                {
                    "id": property_survey_cf,
                    "field_value": property_survey
                },
                {
                    "id": consultations_and_revisions_amount_cf,
                    "field_value": consultations_and_revisions_amount
                },
                {
                    "id": other_cf,
                    "field_value": other
                },
                {
                    "id": describe_other_cf,
                    "field_value": describe_other
                },
                {
                    "id": project_amount_cf,
                    "field_value": project_amount
                },
                {
                    "id": payment_options_cf,
                    "field_value": payment_options
                },
                {
                    "id": amount_to_charge_for_credit_card_cf,
                    "field_value": amount_to_charge_for_credit_card
                },
                {
                    "id": amount_to_charge_for_zelle_cf,
                    "field_value": amount_to_charge_for_zelle
                },
                {
                    "id": amount_to_charge_for_cash_cf,
                    "field_value": amount_to_charge_for_cash
                },
                {
                    "id": amount_to_charge_for_check_cf,
                    "field_value": amount_to_charge_for_check
                },
                {
                    "id": check_number_cf,
                    "field_value": check_number
                },
                {
                    "id": client_signature_form_link_cf,
                    "field_value": client_signature_form_link
                }
            ]
        }

        if primary_phone:
            data['phone'] = primary_phone
        if address:
            data['address1'] = address
        if city:
            data['city'] = city
        if state:
            data['state'] = state

        print(data)
        response = requests.put(url, headers=headers, json=data)
        if response.ok:
            # Use update_or_create method
            update_contact, created = Contact.objects.update_or_create(
                contact_id=contact_id,
                defaults=defaults
            )
            
            serializer = ContactSerializerV2(update_contact)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            error_response = response.json()
            print(error_response)
            message = error_response.get('message')
            return Response(message, status=status.HTTP_400_BAD_REQUEST)


def update_client_signature_form_link_cf(location_id, contact_id, client_signature_form_link_cf, client_signature_form_link):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    data = {
        
        "customFields": [
            
            {
                "id": client_signature_form_link_cf,
                "field_value": client_signature_form_link
            }
        ]
    }

    
    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        print('client_signature_form_link updated')
    else:
        print('Failed to update client_signature_form_link')

@api_view(['GET'])
def get_gantt_chart_v2(request, contact_id):
    contact = Contact.objects.get(contact_id=contact_id)
    all_tasks = Task.objects.filter(contact=contact).order_by('created_at')
    payload = {
        'project_id': contact.project_id,
        'project_name': contact.name,
        'start': all_tasks.first().start_date,
        'end': all_tasks.latest('due_date').due_date,
        'tasks': []
    }
    order = 0
    for task in all_tasks:
        order += 1
        task_data = {
            'start': task.start_date,
            'end': task.due_date,
            'name': task.name,
            'category': task.category,
            'id': task.task_id,
            'progress': 100 if task.completed else 0,
            'assigned_user': task.assigned_to,
            'type': 'task',
            'displayOrder': order
        }

        payload['tasks'].append(task_data)

    return Response(payload, status=status.HTTP_200_OK)

@api_view(['POST'])
def update_task(request, task_id):
    task = Task.objects.get(task_id=task_id)
    data = request.data
    task.start_date = data['start']
    task.due_date = data['end']
    task.save()

    contact = task.contact

    all_tasks = Task.objects.filter(contact=contact).order_by('created_at')
    payload = {
        'project_id': contact.project_id,
        'start': all_tasks.first().start_date,
        'end': all_tasks.latest('due_date').due_date,
        'tasks': []
    }
    order = 0
    for task in all_tasks:
        order += 1
        task_data = {
            'start': task.start_date,
            'end': task.due_date,
            'name': task.name,
            'category': task.category,
            'id': task.task_id,
            'progress': 100 if task.completed else 0,
            'assigned_user': task.assigned_to,
            'type': 'task',
            'displayOrder': order
        }

        payload['tasks'].append(task_data)

    return Response(payload, status=status.HTTP_200_OK)

@api_view(['GET'])
def open_projects_gantt_chart(request):
    # Filter contacts with at least one incomplete task

    contacts_with_incomplete_tasks = Contact.objects.filter(
        contact__completed=False
    ).annotate(
        smallest_start_date=Min('contact__start_date'),
        largest_due_date=Max('contact__due_date'),
        total_tasks=Count('contact')
    ).distinct().order_by('submitted_at')

    result = Task.objects.filter(
        contact__in=Contact.objects.filter(contact__completed=False)
    ).aggregate(
        smallest_start_date=Min('start_date'),
        largest_due_date=Max('due_date')
    )

    payload = {
        'start': result['smallest_start_date'],
        'end': result['largest_due_date'],
        'tasks': []
    }
    order = 0
    for contact in contacts_with_incomplete_tasks:
        completed_tasks = Task.objects.filter(contact=contact, completed=True).count()
        progress = (completed_tasks/contact.total_tasks) * 100
        order += 1
        task_data = {
            'start': contact.smallest_start_date,
            'end': contact.largest_due_date,
            'name': contact.name,
            'id': contact.contact_id,
            'progress': progress,
            'type': 'task',
            'displayOrder': order
        }

        payload['tasks'].append(task_data)

    return Response(payload, status=status.HTTP_200_OK)