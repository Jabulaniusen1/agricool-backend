from django.utils import translation
from base.apps.user.models import User
from base.utils.services.sms import send_sms, get_last_sms_sent
from base.celery import app
from base.settings import AUTH_PASSWORD_URL, FRONTEND_URL, INVITATION_SERVICE_PROVIDER_URL, INVITATION_OPERATOR_URL

# Translation constants
DEFAULT_LANGUAGE = 'en'

# Translation keys
SMS_INVITE_SP_KEY = "sms_invite_service_provider_with_code"
SMS_INVITE_OP_KEY = "sms_invite_operator_with_code"
SMS_AUTH_RESET_KEY = "sms_auth_reset_password"

# Message template constants
SMS_SENT_TEMPLATE = "SMS sent to {}"
USER_NOT_FOUND_TEMPLATE = "User {} does not exist."

# Debug message templates
DEBUG_USER_LANGUAGE_TEMPLATE = "User language: {}"
DEBUG_TRANSLATED_MESSAGE_TEMPLATE = "Translated message: {}"

# Format parameter names
LINK_PARAM = "link"

@app.task
def send_sms_invite_service_provider_with_code(inviter_user_id, phone, link):
    try:
        # Fetch the farmer and produce details
        user = User.objects.get(id=inviter_user_id)

        # construct message
        with translation.override(user.language or DEFAULT_LANGUAGE):
            message = translation.gettext(SMS_INVITE_SP_KEY).format(
                **{LINK_PARAM: link}
            )

        # Send the message
        send_sms(phone, message)

        return SMS_SENT_TEMPLATE.format(phone)

    except User.DoesNotExist:
        return USER_NOT_FOUND_TEMPLATE.format(inviter_user_id)
    except Exception as e:
        return str(e)

@app.task
def send_sms_invite_operator_with_code(inviter_user_id, phone, link):
    try:
        # Fetch the farmer and produce details
        user = User.objects.get(id=inviter_user_id)
        print(DEBUG_USER_LANGUAGE_TEMPLATE.format(user.language or DEFAULT_LANGUAGE))

        # construct message
        with translation.override(user.language or DEFAULT_LANGUAGE):
            message = translation.gettext(SMS_INVITE_OP_KEY).format(
                **{LINK_PARAM: link}
            )

        print(DEBUG_TRANSLATED_MESSAGE_TEMPLATE.format(message))

        # Send the message
        send_sms(phone, message)

        return SMS_SENT_TEMPLATE.format(phone)

    except User.DoesNotExist:
        return USER_NOT_FOUND_TEMPLATE.format(inviter_user_id)
    except Exception as e:
        return str(e)

@app.task
def send_sms_auth_reset_password(user_id, phone, link):
    try:
        # Fetch the farmer and produce details
        user = User.objects.get(id=user_id)

        # construct message
        with translation.override(user.language or DEFAULT_LANGUAGE):
            message = translation.gettext(SMS_AUTH_RESET_KEY).format(
                **{LINK_PARAM: link}
            )

        # Send the message
        send_sms(phone, message)

        return SMS_SENT_TEMPLATE.format(phone)

    except User.DoesNotExist:
        return USER_NOT_FOUND_TEMPLATE.format(user_id)
    except Exception as e:
        return str(e)

@app.task
def get_last_sent_sms(phone):
    return get_last_sms_sent(phone)