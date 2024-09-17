from celery import shared_task
from .models import *
import requests
from django.conf import settings
from celery.exceptions import MaxRetriesExceededError
from requests.exceptions import RequestException
import json
import datetime
from datetime import timedelta
from datetime import timezone as tzone
import pytz

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def historic_fetch(self, *args):
    locations = Location.objects.all()
    for location in locations:
        location_id = location.locationId
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
            if field['name'] == 'Design Project No':
                project_id_cf = field['id']
            if field['name'] == 'Representative Signing Date and Time':
                representative_signed_date_cf = field['id']
            if field['name'] == 'Created':
                submitted_at_cf = field['id']
            if field['name'] == 'Modified':
                modified_at_cf = field['id']
            

        check_is_token_expired = checking_token_expiration(location_id)
        if check_is_token_expired:
            refresh_the_tokens = refreshing_tokens(location_id)
        else:
            pass
        
        location = Location.objects.get(locationId = location_id) 
        access_token = location.access_token

        url = 'https://services.leadconnectorhq.com/contacts/'

        params = {'locationId': location_id, 'limit': 100}
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'Version': '2021-07-28'
        }

        count = 0
        while url is not None:
            if count > 0:
                params = {}
            
            try:
                response = requests.get(url, headers=headers, params=params)
            except (RequestException, ConnectionError) as exc:
                try:
                    print('retry on get all contacts')
                    self.retry()  # Retry the task
                except MaxRetriesExceededError:
                    print('Maximum number of retries exceeded')
                    print('error on fetching all contacts')
            
            if response.status_code == 200:
                # Successful request
                count += 1
                data = response.json()
                contacts = data['contacts']
                for contact in contacts:
                    contact_id = contact['id']
                    primary_email = contact.get('email')
                    primary_phone = contact.get('phone')
                    name = contact.get('name')
                    if not name:
                        first_name = contact.get('firstName')
                        last_name = contact.get('lastName')

                        if first_name and last_name:
                            name = f'{first_name} {last_name}'
                        elif first_name:
                            name = first_name
                        elif last_name:
                            name = last_name
                        else:
                            name = None
                    city = contact.get('city')
                    state = contact.get('state')
                    zip = contact.get('postalCode')
                    address = contact.get('address1')
                    
                    customFields = contact.get('customFields')
                    project_id = None
                    secondary_phone = None
                    secondary_email = None
                    refferd_by = None
                    hoa = None
                    plot_plan = None
                    hardscape_2d_3d = None
                    hardscape_and_planting = None
                    above_plan_plus = None
                    measuring_for_site_plan = None
                    property_droning = None
                    property_survey = None
                    consultations_and_revisions_amount_hour = None
                    other = None
                    describe_other = None
                    project_amount = None
                    payment_option = None
                    amount_to_charge_for_credit_card = None
                    card_holder_name = None
                    credit_card_number = None
                    expiration_date = None
                    billing_zip_code = None
                    cvv = None
                    amount_to_charge_for_zelle = None
                    amount_to_charge_for_cash = None
                    amount_to_charge_for_check = None
                    check_number = None
                    submitted_at = None
                    modified_at = None
                    representative_signed_date = None
                    for field in customFields:
                        if field['id'] == refferd_by_cf:
                            refferd_by = field['value']
                        if field['id'] == secondary_phone_cf:
                            secondary_phone = field['value']
                        if field['id'] == secondary_email_cf:
                            secondary_email = field['value']
                        if field['id'] == HOA_cf:
                            hoa = field['value']
                        if field['id'] == plot_plan_cf:
                            plot_plan = field['value']
                        if field['id'] == hardscape_cf:
                            hardscape_2d_3d = field['value']
                        if field['id'] == hardscape_and_planning_cf:
                            hardscape_and_planting = field['value']
                        if field['id'] == above_plans_plus_cf:
                            above_plan_plus = field['value']
                        if field['id'] == measuring_for_site_plan_cf:
                            measuring_for_site_plan = field['value']
                        if field['id'] == property_droning_cf:
                            property_droning = field['value']
                        if field['id'] == property_survey_cf:
                            property_survey = field['value']
                        if field['id'] == consultations_and_revisions_amount_cf:
                            consultations_and_revisions_amount_hour = field['value']
                        if field['id'] == other_cf:
                            other = field['value']
                        if field['id'] == describe_other_cf:
                            describe_other = field['value']
                        if field['id'] == project_amount_cf:
                            project_amount = field['value']
                        if field['id'] == payment_options_cf:
                            payment_option = field['value']
                        if field['id'] == amount_to_charge_for_credit_card_cf:
                            amount_to_charge_for_credit_card = field['value']
                        if field['id'] == amount_to_charge_for_zelle_cf:
                            amount_to_charge_for_zelle = field['value']
                        if field['id'] == amount_to_charge_for_cash_cf:
                            amount_to_charge_for_cash = field['value']
                        if field['id'] == amount_to_charge_for_check_cf:
                            amount_to_charge_for_check = field['value']
                        if field['id'] == check_number_cf:
                            check_number = field['value']
                        if field['id'] == project_id_cf:
                            project_id = field['value']
                        if field['id'] == representative_signed_date_cf:
                            representative_signed_date_str = field['value']
                            representative_signed_date_timestamp_s = representative_signed_date_str / 1000
                            representative_signed_date = datetime.datetime.fromtimestamp(representative_signed_date_timestamp_s).date()
                        if field['id'] == submitted_at_cf:
                            submitted_at_str = field['value']
                            submitted_at_timestamp_s = submitted_at_str / 1000
                            submitted_at = datetime.datetime.fromtimestamp(submitted_at_timestamp_s).date()
                        if field['id'] == modified_at_cf:
                            modified_at_str = field['value']
                            modified_at_timestamp_s = modified_at_str / 1000
                            modified_at = datetime.datetime.fromtimestamp(modified_at_timestamp_s).date()
                        
                    try:
                        Contact.objects.update_or_create(
                            contact_id = models.CharField(primary_key=True, max_length=700),
                            defaults = {
                                'project_id' : project_id,
                                'location_id': location_id,
                                'location_name': location.location_name,
                                'name': name,
                                'primary_phone': primary_phone,
                                'primary_email': primary_email,
                                'secondary_phone': secondary_phone,
                                'secondary_email': secondary_email,
                                'refferd_by': refferd_by,
                                'address': address,
                                'city': city,
                                'state': state,
                                'zip' : zip,
                                'hoa': hoa,
                                'plot_plan': plot_plan,
                                'hardscape_2d_3d': hardscape_2d_3d,
                                'hardscape_and_planting': hardscape_and_planting,
                                'above_plan_plus': above_plan_plus,
                                'measuring_for_site_plan': measuring_for_site_plan,
                                'property_droning': property_droning,
                                'property_survey': property_survey,
                                'consultations_and_revisions_amount_hour': consultations_and_revisions_amount_hour,
                                'other': other,
                                'describe_other': describe_other,
                                'project_amount': project_amount,
                                'payment_option': payment_option,
                                'amount_to_charge_for_credit_card': amount_to_charge_for_credit_card,
                                'card_holder_name': card_holder_name,
                                'credit_card_number': credit_card_number,
                                'expiration_date': expiration_date,
                                'billing_zip_code': billing_zip_code,
                                'cvv': cvv,
                                'amount_to_charge_for_zelle': amount_to_charge_for_zelle,
                                'amount_to_charge_for_cash': amount_to_charge_for_cash,
                                'amount_to_charge_for_check': amount_to_charge_for_check,
                                'check_number': check_number,
                                'representative_signed_date': representative_signed_date,
                                'submitted_at': submitted_at,
                                'modified_at': modified_at,
                            }
                        )
                        print('contact created/updated')
                    except Exception as e:
                        print(e)
                        print(contact_id)

                url = data['meta']['nextPageUrl']

            elif response.status_code == 401:
                refreshing_tokens(location_id)
                location = Location.objects.get(locationId = location_id)
                access_token = location.access_token

                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Version': '2021-07-28'
                }
            else:
                print(response.json())
                print(response.status_code)
                break


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

          
        