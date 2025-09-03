from django.utils import translation

from base.apps.storage.models import Produce
from base.apps.user.models import Farmer
from base.celery import app
from base.utils.services.sms import send_sms

# Translation constants
DEFAULT_LANGUAGE = 'en'
SMS_TRANSLATION_KEY = "sms_ttpu_2_days_left"

# Return message templates
SMS_SENT_TEMPLATE = "SMS sent to {}"
FARMER_NOT_FOUND_TEMPLATE = "Farmer {} does not exist."
PRODUCE_NOT_FOUND_TEMPLATE = "Produce {} does not exist."


@app.task
def send_sms_ttpu_2_days_left(farmer_id, produce_id):
    try:
        # Fetch the farmer and produce details
        produce = Produce.objects.get(id=produce_id)
        farmer = Farmer.objects.get(id=farmer_id)
        user = farmer.user

        # Compile message for the target user
        with translation.override(user.language or DEFAULT_LANGUAGE):
            message = translation.gettext(SMS_TRANSLATION_KEY).format(
                crop_name=produce.crop.name,
                checkin_date=produce.checkin.movement.date,
                cooling_unit=produce.crates.first().cooling_unit.name,
                checkin_code=produce.checkin.movement.code,
            )

        # Send the message
        send_sms(user.phone, message)

        return SMS_SENT_TEMPLATE.format(user.phone)

    except Farmer.DoesNotExist:
        return FARMER_NOT_FOUND_TEMPLATE.format(farmer_id)
    except Produce.DoesNotExist:
        return PRODUCE_NOT_FOUND_TEMPLATE.format(produce_id)
    except Exception as e:
        return str(e)
