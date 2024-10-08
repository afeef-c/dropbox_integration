from rest_framework import serializers
from django.conf import settings
from .models import Contact

class ContactSerializer(serializers.ModelSerializer):
    client_signature_url = serializers.SerializerMethodField()
    representative_signature_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'contact_id', 'project_id', 'location_id', 'location_name', 'name',
            'primary_phone', 'primary_email', 'secondary_phone', 'secondary_email',
            'refferd_by', 'address', 'zip', 'city', 'state', 'hoa', 'plot_plan',
            'hardscape_2d_3d', 'hardscape_and_planting', 'above_plan_plus',
            'measuring_for_site_plan', 'property_droning', 'property_survey',
            'consultations_and_revisions_amount_hour', 'other', 'describe_other',
            'project_amount', 'payment_option', 'amount_to_charge_for_credit_card',
            'card_holder_name', 'credit_card_number', 'expiration_date', 'billing_zip_code',
            'cvv', 'amount_to_charge_for_zelle', 'amount_to_charge_for_cash', 
            'amount_to_charge_for_check', 'check_number', 'submitted_at', 'client_signature_url', 
            'representative_signature_url', 'pdf_url', 'modified_at', 'representative_signed_date',
            'client_signed_date'
        ]

    def get_client_signature_url(self, obj):
        if obj.client_signature:
            return f'{settings.BASE_URL}{obj.client_signature.url}'
        return None

    def get_representative_signature_url(self, obj):
        if obj.representative_signature:
            return f'{settings.BASE_URL}{obj.representative_signature.url}'
        return None

    def get_pdf_url(self, obj):
        if obj.pdf:
            return f'{settings.BASE_URL}{obj.pdf.url}'
        return None
    

class ContactSerializerV2(serializers.ModelSerializer):
    client_signature_url = serializers.SerializerMethodField()
    representative_signature_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    expiration_date = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'contact_id', 'project_id', 'location_id', 'location_name', 'name',
            'primary_phone', 'primary_email', 'secondary_phone', 'secondary_email',
            'refferd_by', 'address', 'zip', 'city', 'state', 'hoa', 'plot_plan',
            'hardscape_2d_3d', 'hardscape_and_planting', 'above_plan_plus',
            'measuring_for_site_plan', 'property_droning', 'property_survey',
            'consultations_and_revisions_amount_hour', 'other', 'describe_other',
            'project_amount', 'payment_option', 'amount_to_charge_for_credit_card',
            'card_holder_name', 'credit_card_number', 'expiration_date', 'expiration_date_str', 'billing_zip_code',
            'cvv', 'amount_to_charge_for_zelle', 'amount_to_charge_for_cash', 
            'amount_to_charge_for_check', 'check_number', 'submitted_at', 'client_signature_url', 
            'representative_signature_url', 'pdf_url', 'modified_at', 'representative_signed_date',
            'client_signed_date'
        ]

    def get_client_signature_url(self, obj):
        if obj.client_signature:
            return f'{settings.BASE_URL}{obj.client_signature.url}'
        return obj.client_signature_url

    def get_representative_signature_url(self, obj):
        if obj.representative_signature:
            return f'{settings.BASE_URL}{obj.representative_signature.url}'
        return obj.representative_signature_url

    def get_pdf_url(self, obj):
        if obj.pdf:
            return f'{settings.BASE_URL}{obj.pdf.url}'
        return obj.pdf_url