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
from .tasks import historic_fetch

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

    all_contacts = Contact.objects.filter(submitted_at__range=[start_date, end_date]).order_by('-submitted_at')

    if search:
        search_lower = search.lower()
        all_contacts = all_contacts.filter(
            Q(name__istartswith=search_lower) |
            Q(email__istartswith=search_lower) |
            Q(phone__istartswith=search_lower)
        )
    else:
        all_contacts = all_contacts
    
    # Apply offset and limit
    if offset or limit:
        all_contacts = all_contacts[offset:offset + limit]

    serializer = ContactSerializer(all_contacts, many=True)
    return Response({'data': serializer.data}, status=status.HTTP_200_OK)
    
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
    update_contact_agreement(location_id, contact_id)
    serializer = ContactSerializer(contact)
    return Response({'data': serializer.data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])  # Enables file upload support
def submit_form_data(request):
    print(request.data)
    # Extract form data
    project_id = request.data.get('project_id')
    refferd_by = request.data.get('refferd_by')
    client_name = request.data.get('client_name')
    print(client_name)
    address = request.data.get('address')
    city = request.data.get('city')
    state = request.data.get('state')
    zip = request.data.get('zip')
    primary_phone = request.data.get('primary_phone')
    secondary_phone = request.data.get('secondary_phone')
    primary_email = request.data.get('primary_email')
    secondary_email = request.data.get('secondary_email')

    # // Project Info
    HOA = request.data.get('HOA')
    plot_plan = request.data.get('plot_plan')
    hardscape = request.data.get('hardscape')
    hardscape_and_planning = request.data.get('hardscape_and_planning')
    above_plans_plus = request.data.get('above_plans_plus')
    measuring_for_site_plan = request.data.get('measuring_for_site_plan')
    property_droning = request.data.get('property_droning')
    property_survey = request.data.get('property_survey')
    consultations_and_revisions_amount = request.data.get('consultations_and_revisions_amount')
    other = request.data.get('other')
    describe_other = request.data.get('describe_other')
    project_amount = request.data.get('project_amount')

    # // Billing Info
    payment_options = request.data.get('payment_options')

    # //credit card
    amount_to_charge_for_credit_card = request.data.get('amount_to_charge_for_credit_card')
    card_holder_name = request.data.get('card_holder_name')
    credit_card_number = request.data.get('credit_card_number')
    expiration_date = request.data.get('expiration_date')
    billing_zip_code = request.data.get('billing_zip_code')
    CVV = request.data.get('CVV')

    # //zelle
    amount_to_charge_for_zelle = request.data.get('amount_to_charge_for_zelle')

    # //cash
    amount_to_charge_for_cash = request.data.get('amount_to_charge_for_cash')

    # //check
    amount_to_charge_for_check = request.data.get('amount_to_charge_for_check')
    check_number = request.data.get('ckeck_number')

    # Extract files
    client_signature = request.FILES.get('client_sign')
    representative_signature = request.FILES.get('representative_sign')
    agreement = request.FILES.get('pdf')

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
        'expiration_date': expiration_date,
        'billing_zip_code': billing_zip_code,
        'cvv': CVV,
        'amount_to_charge_for_zelle': amount_to_charge_for_zelle,
        'amount_to_charge_for_cash': amount_to_charge_for_cash,
        'amount_to_charge_for_check': amount_to_charge_for_check,
        'check_number': check_number,
        'client_signature' : client_signature,
        'representative_signature' : representative_signature,
        'agreement' : agreement,
        'modified_at': submitted_at.date(),
    }

    if client_signature:
        defaults['client_signed_date'] = submitted_at.date()

    if representative_signature:
        defaults['representative_signed_date'] = submitted_at.date()

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
        # Count the number of projects for the current year
        project_count = Contact.objects.filter(project_id__startswith=year_short).count() + 1
        # Generate project_id in the format YYYY-0001
        project_id = f"{year_short}-{str(project_count).zfill(3)}"
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
                }
            ]
        }

        print(data)
        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            contact_data = response.json()
            contact = contact_data.get('contact')
            contact_id = contact['id']

            # Use update_or_create method
            new_contact, created = Contact.objects.update_or_create(
                contact_id=contact_id,
                defaults=defaults
            )

            if client_signature:
                update_contact_client_signatures(location_id, contact_id, client_signature_cf)
            if representative_signature:
                update_contact_representative_signatures(location_id, contact_id, representative_signature_cf)
            if agreement:
                update_contact_agreement(location_id, contact_id, agreement_cf)
            serializer = ContactSerializer(new_contact)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            error_response = response.json()
            print(error_response)
            message = error_response.get('message')
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
    else:
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
        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            # Use update_or_create method
            update_contact, created = Contact.objects.update_or_create(
                contact_id=contact_id,
                defaults=defaults
            )

            if client_signature:
                update_contact_client_signatures(location_id, contact_id, client_signature_cf)
            if representative_signature:
                update_contact_representative_signatures(location_id, contact_id, representative_signature_cf)
            if agreement:
                update_contact_agreement(location_id, contact_id, agreement_cf)

            serializer = ContactSerializer(update_contact)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        else:
            error_response = response.json()
            print(error_response)
            message = error_response.get('message')
            return Response(message, status=status.HTTP_400_BAD_REQUEST)
        
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
                                "originalname": 'client_signature',
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