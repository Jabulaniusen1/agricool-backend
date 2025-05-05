from django.utils import translation
from base.utils.services.sms import send_sms

def send_sms_invite_operator_with_code(farmer_phone, link, language='en'):
    # Set up the context with variables to be inserted into the translation
    context = {
        'link': link,
    }

    # Default to English if language is English or None or not in the translations dictionary
    with translation.override(language or 'en'):
        message = translation.gettext("sms_ttpu_2_days_left") % context

    print(f"debug: sending TTPU sms to farmer: [{farmer_phone}] {message}!")
    send_sms(farmer_phone, message)
