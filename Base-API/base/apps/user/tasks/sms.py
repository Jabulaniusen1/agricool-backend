from django.utils import translation
from base.apps.user.models import User
from base.utils.services.sms import send_sms, get_last_sms_sent
from base.celery import app
from base.settings import AUTH_PASSWORD_URL, FRONTEND_URL, INVITATION_SERVICE_PROVIDER_URL, INVITATION_OPERATOR_URL

@app.task
def send_sms_invite_service_provider_with_code(inviter_user_id, phone, link):
    try:
        # Fetch the farmer and produce details
        user = User.objects.get(id=inviter_user_id)

        # construct message
        with translation.override(user.language or 'en'):
            message = translation.gettext("sms_invite_service_provider_with_code").format(
                link=link
            )

        # Send the message
        send_sms(phone, message)

        return f"SMS sent to {phone}"

    except User.DoesNotExist:
        return f"User {inviter_user_id} does not exist."
    except Exception as e:
        return str(e)

@app.task
def send_sms_invite_operator_with_code(inviter_user_id, phone, link):
    try:
        # Fetch the farmer and produce details
        user = User.objects.get(id=inviter_user_id)
        print(f"User language: {user.language or 'en'}")

        # construct message
        with translation.override(user.language or 'en'):
            message = translation.gettext("sms_invite_operator_with_code").format(
                link=link
            )

        print(f"Translated message: {message}")

        # Send the message
        send_sms(phone, message)

        return f"SMS sent to {phone}"

    except User.DoesNotExist:
        return f"User {inviter_user_id} does not exist."
    except Exception as e:
        return str(e)

@app.task
def send_sms_auth_reset_password(user_id, phone, link):
    try:
        # Fetch the farmer and produce details
        user = User.objects.get(id=user_id)

        # construct message
        with translation.override(user.language or 'en'):
            message = translation.gettext("sms_auth_reset_password").format(
                link=link
            )

        # Send the message
        send_sms(phone, message)

        return f"SMS sent to {phone}"

    except User.DoesNotExist:
        return f"User {user_id} does not exist."
    except Exception as e:
        return str(e)

@app.task
def get_last_sent_sms(phone):
    return get_last_sms_sent(phone)