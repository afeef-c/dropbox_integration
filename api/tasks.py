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
import time

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
                            contact_id = contact_id,
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
                        print(name)

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

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def fetch_users_by_location(self, location_id, *args):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass
    
    location = Location.objects.get(locationId = location_id) 
    access_token = location.access_token

    url = 'https://services.leadconnectorhq.com/users/'
    params = {'locationId': location_id}
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Version': '2021-07-28'
    }

    response = requests.get(url, params=params, headers=headers)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        data = response.json()
        users = data.get('users')
        for user in users:
            user_id = user['id']
            first_name = user.get('firstName')
            last_name = user.get('lastName')
            email = user.get('email')
            phone = user.get('phone')
            full_name = f'{first_name} {last_name}'
            print(f'{full_name} ({email})')
            try:
                db_user = User.objects.get(user_id=user_id)
                db_user.name = full_name
                db_user.email = email
                db_user.phone = phone
                db_user.save()
            except:
                db_user = User.objects.create(user_id=user_id, email=email, name=full_name, phone=phone)
            db_user.save()

            print('user created/updated')
    
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def create_all_task(self, contact_id, *args):
    contact = Contact.objects.get(contact_id=contact_id)
    if not contact.project_id:
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

        contact.project_id = project_id
        contact.save()
        pass_project_id_to_ghl(contact.location_id, contact_id, project_id)
    
    tasks = [
        {"category": "Sales", "task_name": "Contract signed & numbered", "assigned_to": ["Gio Leonardo", "Julian Terrazas", "Kimberly Parry", "Enjoli Cullen"]},
        {"category": "Sales", "task_name": "Project added to Dropbox", "assigned_to": ["Debra Leonardo"]},
        {"category": "Sales", "task_name": "Emailed to PM & Office", "assigned_to": ["Debra Leonardo"]},
        {"category": "Sales", "task_name": "PM to call client for intro", "assigned_to": ["Courtney Smith"]},
        {"category": "Sales", "task_name": "Initial payment captured", "assigned_to": ["Gio Leonardo", "Julian Terrazas", "Kimberly Parry", "Enjoli Cullen"]},
        {"category": "Sales", "task_name": "Design notes added to Dropbox", "assigned_to": ["Gio Leonardo", "Julian Terrazas", "Kimberly Parry", "Enjoli Cullen"]},
        {"category": "Sales", "task_name": "HOA Guidelines captured", "assigned_to": ["Courtney Smith"]},
        {"category": "Sales", "task_name": "Questionnaire captured", "assigned_to": ["Courtney Smith"]},
        {"category": "Sales", "task_name": "House plans scanned (if applicable)", "assigned_to": ["Gio Leonardo"]},
        {"category": "Sales", "task_name": "Get Setbacks", "assigned_to": ["Courtney Smith"]},
        # {"category": "Measure", "task_name": "Schedule measure", "assigned_to": ["Julian Terrazas"]},
        {"category": "Measure", "task_name": "Measure/Prop Pics/Aerials", "assigned_to": ["Julian Terrazas"]},
        {"category": "Site Plan Created", "task_name": "Site plan completed", "assigned_to": ["Gio Leonardo", "Julian Terrazas"]},
        # {"category": "Hardscape", "task_name": "Monitor progress", "assigned_to": []},
        # {"category": "Hardscape", "task_name": "Track expenses", "assigned_to": []},
        # {"category": "Hardscape", "task_name": "Evaluate progress", "assigned_to": []},
        # {"category": "Hardscape", "task_name": "Address risks", "assigned_to": []},
        {"category": "Hardscape", "task_name": "Design review with sales as needed", "assigned_to": ["Gio Leonardo", "Julian Terrazas", "Kimberly Parry", "Enjoli Cullen"]},
        {"category": "Hardscape", "task_name": "House created in Structure Studio", "assigned_to": ["Mike Koppenhaver", "Rebekah Koppenhaver"]},
        {"category": "Hardscape", "task_name": "Design review with client", "assigned_to": ["Mike Koppenhaver", "Gio Leonardo"]},
        {"category": "Hardscape", "task_name": "HP Created", "assigned_to": ["Mike Koppenhaver"]},
        {"category": "Hardscape", "task_name": "Hardscape numbers", "assigned_to": ["Mike Koppenhaver", "Gio Leonardo"]},
        {"category": "Hardscape", "task_name": "Hardscape Prelim", "assigned_to": ["Mike Koppenhaver", "Gio Leonardo"]},
        {"category": "Hardscape", "task_name": "Revisions 1", "assigned_to": ["Mike Koppenhaver"]},
        {"category": "Hardscape", "task_name": "Revisions 2", "assigned_to": ["Mike Koppenhaver"]},
        {"category": "Hardscape", "task_name": "Revisions 3 (If needed/Hourly rates apply)", "assigned_to": ["Mike Koppenhaver"]},
        {"category": "Hardscape", "task_name": "HP Sign-Off (Notify Office & PP)", "assigned_to": ["Mike Koppenhaver", "Gio Leonardo"]},
        {"category": "Hardscape", "task_name": "HP Created for PP", "assigned_to": ["Mike Koppenhaver"]},
        {"category": "Hardscape", "task_name": "HP Payment captured", "assigned_to": ["Mike Koppenhaver", "Gio Leonardo", "Debra Leonardo"]},
        {"category": "Planting Plan", "task_name": "Initial call to client", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "PP created", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "PP meeting with client", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "Revisions 1", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "Revisions 2", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "Revisions 3 (If needed/Hourly rates apply)", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "PP Sign-Off (Notify office)", "assigned_to": ["Courtney Smith", "Kimberly Parry"]},
        {"category": "Planting Plan", "task_name": "PP payment captured", "assigned_to": ["Courtney Smith", "Kimberly Parry", "Debra Leonardo"]},
        {"category": "Planting Plan", "task_name": "Layout Final set of plans on Borders", "assigned_to": ["Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "Notify Designer to create Final HP (Callouts/totals/screenshots)", "assigned_to": ["Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "Hardscape created (Notify PM)", "assigned_to": ["Mike Koppenhaver"]},
        {"category": "Final Set of Plans", "task_name": "Assign Tech Sheets to Designer (PM to notify)", "assigned_to": ["Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "Create Irrigation", "assigned_to": ["Mike Koppenhaver", "Rebekah Koppenhaver", "Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "Create Drainage", "assigned_to": ["Mike Koppenhaver", "Rebekah Koppenhaver", "Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "Create Lighting", "assigned_to": ["Mike Koppenhaver", "Rebekah Koppenhaver", "Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "QC Tech sheets (Notify PM & Gio)", "assigned_to": ["Gio Leonardo", "Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "PM to notify Gio for Final", "assigned_to": ["Courtney Smith"]},
        {"category": "Final Set of Plans", "task_name": "Schedule client for Final", "assigned_to": ["Gio Leonardo"]},
        {"category": "Final Set of Plans", "task_name": "Final plan presentation", "assigned_to": ["Gio Leonardo"]},
        {"category": "Final Set of Plans", "task_name": "Final payment captured", "assigned_to": ["Debra Leonardo"]},
        {"category": "Final Set of Plans", "task_name": "Digital copies sent to client", "assigned_to": ["Gio Leonardo"]}
    ]

    # {
    #     "project_id" : "20-001",
    #     "Task": "Contract signed & numbered",
    #     "AssignedPerson": "Courtney Smith",
    #     "ProgressDoneOrNotDone": "Yes",
    #     "DueDate": "2024-10-20",
    #     "ID": "mIlTIO6cgbKqD1IjCFKW"
    # }
    contact = Contact.objects.get(contact_id=contact_id)
    location_id = contact.location_id
    location_timezone = Location.objects.get(locationId = location_id).timezone
    
    current_datetime = datetime.datetime.now(datetime.timezone.utc)
    # Add 90 days to submitted_at
    ninety_days_later = current_datetime + datetime.timedelta(days=90)
    # Replace time part with 23:59:59
    ninety_days_later = ninety_days_later.replace(hour=23, minute=59, second=59)
    # Stringify in the format "YYYY-MM-DDTHH:MM:SSZ"
    due_date = ninety_days_later.strftime("%Y-%m-%dT%H:%M:%SZ")

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


    for task in tasks:
        task_name = task['task_name']
        category = task['category']
        if not Task.objects.filter(contact=contact, name=task_name, category=category).exists():
            assigned_to_list = task['assigned_to']
            if assigned_to_list:
                if len(assigned_to_list) > 1:
                    list_lenght = len(assigned_to_list)
                    # Fetch previous task assignments for the current task name
                    previous_task_assignments = Task.objects.filter(name=task_name).order_by('-created_at')

                    # Determine the last assigned user
                    last_assigned_user = None
                    if previous_task_assignments.exists():
                        last_assigned_user = previous_task_assignments.first().assigned_to
                    
                    if last_assigned_user:
                        # Get the index of the last assigned user
                        last_user_index = assigned_to_list.index(last_assigned_user) if last_assigned_user in assigned_to_list else -1
                        # Calculate the next user index in round-robin fashion
                        next_user_index = (last_user_index + 1) % len(assigned_to_list)
                        assigned_user_name = assigned_to_list[next_user_index]
                    else:
                        # If no previous assignments exist, assign to the first user
                        assigned_user_name = assigned_to_list[0]
                else:
                    assigned_user_name = assigned_to_list[0]
            else:
                assigned_user_name = 'Gio Leonardo'

            print(assigned_user_name)
            user_id = User.objects.get(name=assigned_user_name).user_id

            new_task = create_task(location_id, contact_id, task_name, user_id, due_date)
            if new_task:
                task_id = new_task['id']
                start_at = datetime.datetime.now(datetime.timezone.utc)
                # Stringify in the format "YYYY-MM-DDTHH:MM:SSZ"
                start_at_str = start_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                try:
                    naive_start_at = datetime.datetime.fromisoformat(start_at_str[:-1])
                except:
                    try:
                        naive_start_at = datetime.datetime.strptime(start_at_str, '%Y-%m-%dT%H:%M:%S')
                    except:
                        naive_start_at = datetime.datetime.strptime(start_at_str, '%Y-%m-%d')

                input_timezone = pytz.timezone("UTC")
                start_at_obj = input_timezone.localize(naive_start_at)
                target_timezone = pytz.timezone(location_timezone)
                start_date = start_at_obj.astimezone(target_timezone).replace(tzinfo=None).date()

                Task.objects.update_or_create(
                    task_id = task_id,
                    contact = contact,
                    category = category,
                    name = task_name,
                    defaults={
                        'assigned_to_id' : user_id,
                        'assigned_to' : assigned_user_name,
                        'start_date' : start_date,
                        'due_date' : due_date_in_location_time_zone
                    }
                )

                print(f'{task_name} task added')
            else:
                print(f'Failed to create the {task_name} task for {contact.name}')
        else:
            print(f'{task_name} task already added')

def pass_project_id_to_ghl(location_id, contact_id, project_id):

    all_custom_fields = get_all_custom_fields(location_id)
    for field in all_custom_fields:
        if field['name'] == 'Design Project No':
            project_id_cf = field['id']
            break
        

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
                "id": project_id_cf,
                "field_value": project_id
            }
        ]
    }

    
    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        print('project_id CF updated')
    else:
        print('Failed to update project_id CF')
            
def create_task(location_id, contact_id, task_name, user_id, due_date):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass

    location = Location.objects.get(locationId = location_id)
    access_token = location.access_token

    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}/tasks"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }
    payload = {
        "title": task_name,
        "dueDate": due_date,
        "completed": False,
        "assignedTo": user_id
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.ok:
        data = response.json()
        task = data['task']
        return task
    else:
        print(response.json())
        return None
    
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def get_and_update_all_task(self, *args):
    location = Location.objects.first()
    location_id = location.locationId
    location_timezone = location.timezone

    unique_contact_ids = Task.objects.values_list('contact__contact_id', flat=True).distinct()
    print(f'Contacts count: {len(unique_contact_ids)}')

    for contact_id in unique_contact_ids:
        check_is_token_expired = checking_token_expiration(location_id)
        if check_is_token_expired:
            refresh_the_tokens = refreshing_tokens(location_id)

        location = Location.objects.get(locationId=location_id)
        access_token = location.access_token

        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}/tasks"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Version": "2021-07-28"
        }

        response = requests.get(url, headers=headers)
        if response.ok:
            data = response.json()
            tasks = data['tasks']
            for task in tasks:
                task_id = task['id']

                try:
                    is_task = Task.objects.get(task_id=task_id)
                except:
                    is_task = None
                    print('No task found')
                
                if is_task:
                    user_id = task.get('assignedTo')
                    if user_id:
                        assigned_user_name = User.objects.get(user_id=user_id).name
                    else:
                        assigned_user_name = None
                    title = task.get('title')
                    due_date = task.get('dueDate')
                    completed = task.get('completed')

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

                    # Check if any field has changed before updating the task
                    if (is_task.completed != completed or 
                        is_task.assigned_to_id != user_id or 
                        is_task.assigned_to != assigned_user_name or 
                        is_task.name != title or 
                        is_task.due_date != due_date_in_location_time_zone):

                        print('Task updated in GHL')

                        # Update the task fields
                        is_task.completed = completed
                        is_task.assigned_to_id = user_id
                        is_task.assigned_to = assigned_user_name
                        is_task.name = title
                        is_task.due_date = due_date_in_location_time_zone
                        is_task.save()
        else:
            print(response.json())

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def wait_task(self, *args):
    print("Waiting for 10 seconds before processing next task...")
    time.sleep(10)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def update_task_status(self, data, *args):
    print(data)

    location_id = data.get('locationId')
    try:
        location_timezone = Location.objects.get(locationId = location_id).timezone
    except:
        location_timezone = None

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
        add_task_tag_to_ghl_contact(location_id, task.contact.contact_id, title)

        # Get the next task based on the created_at timestamp
        next_task = Task.objects.filter(
            contact=task.contact,
            created_at__gt=task.created_at  # Filter tasks created after the current task
        ).order_by('created_at').first()  # Get the next task by ordering

        if next_task:
            next_task_user_id = next_task.assigned_to_id
            next_task_title = next_task.name
            
            update_next_task_cfs(location_id, task.contact.contact_id, next_task_user_id, next_task_title)
        print('Task completed')


def add_task_tag_to_ghl_contact(location_id, contact_id, title):
    if title == 'Contract signed & numbered':
        tag = ['contract signed']
    elif title == 'Emailed to PM & Office':
        tag = ['emailed to pm']
    elif title == 'PM to call client for intro':
        tag = ['pm to call client']
    elif title == 'Initial payment captured':
        tag = ['initial payment']
    elif title == 'Site plan completed':
        tag = ['site plan']
    elif title == 'HP Sign-Off (Notify Office & PP)':
        tag = ['hp sign-off']
    elif title == 'HP Created for PP':
        tag = ['hp created']
    elif title == 'PP Sign-Off (Notify office)':
        tag = ['pp sign-off']
    elif title == 'Layout Final set of plans on Borders':
        tag = ['layout final']
    elif title == 'QC Tech sheets (Notify PM & Gio)':
        tag = ['qc tech']
    elif title == 'Final plan presentation':
        tag = ['final plan']
    else:
        tag = []

    if tag:
        check_is_token_expired = checking_token_expiration(location_id)
        if check_is_token_expired:
            refresh_the_tokens = refreshing_tokens(location_id)
        else:
            pass

        location = Location.objects.get(locationId = location_id)
        access_token = location.access_token

        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}/tags"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
        data = {
            "tags": tag
        }

        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            print('Task tag added')
        else:
            print('Failed to add Task tag')
            print(response.json())
    else:
        print('tag is empty')

def update_next_task_cfs(location_id, contact_id, next_task_user_id, next_task_title):
    all_custom_fields = get_all_custom_fields(location_id)
    for field in all_custom_fields:
        if field['name'] == 'Next Task User':
            next_task_user_cf = field['id']
        if field['name'] == 'Next Task Title':
            next_task_title_cf = field['id']

    user_email = User.objects.get(user_id=next_task_user_id).email

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
                "id": next_task_user_cf,
                "field_value": user_email
            },
            {
                "id": next_task_title_cf,
                "field_value": next_task_title
            }
        ]
    }

    response = requests.put(url, headers=headers, json=data)
    if response.ok:
        tags = ['next task notify']
        add_tags(location_id, contact_id, tags)
        print('next task notify added')
    else:
        print('failed to update next task CFs')
        print(response.status_code)
        print(response.json)

def add_tags(location_id, contact_id, tags):
    check_is_token_expired = checking_token_expiration(location_id)
    if check_is_token_expired:
        refresh_the_tokens = refreshing_tokens(location_id)
    else:
        pass
    
    location = Location.objects.get(locationId = location_id) 
    access_token = location.access_token

    url = f'https://services.leadconnectorhq.com/contacts/{contact_id}/tags'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Version': '2021-07-28'
    }

    data = {
        "tags": tags
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print('tags added')
    else:
        print('failed to add tags')
