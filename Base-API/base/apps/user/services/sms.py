from django.utils import translation
from base.utils.services.sms import send_sms

# Translation constants
DEFAULT_LANGUAGE = 'en'
TTPU_TRANSLATION_KEY = "sms_ttpu_2_days_left"

# Context field names
LINK_CONTEXT_KEY = 'link'

# Debug message template
DEBUG_SMS_TEMPLATE = "debug: sending TTPU sms to farmer: [{}] {}!"

def send_sms_invite_operator_with_code(farmer_phone, link, language=DEFAULT_LANGUAGE):
    # Set up the context with variables to be inserted into the translation
    context = {
        LINK_CONTEXT_KEY: link,
    }

    # Default to English if language is English or None or not in the translations dictionary
    with translation.override(language or DEFAULT_LANGUAGE):
        message = translation.gettext(TTPU_TRANSLATION_KEY) % context

    print(DEBUG_SMS_TEMPLATE.format(farmer_phone, message))
    send_sms(farmer_phone, message)
