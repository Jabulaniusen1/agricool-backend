from django.utils import translation

from base.apps.storage.models import Produce
from base.apps.user.models import Farmer
from base.celery import app
from base.utils.services.sms import send_sms


@app.task
def send_sms_ttpu_2_days_left(farmer_id, produce_id):
    try:
        # Fetch the farmer and produce details
        produce = Produce.objects.get(id=produce_id)
        farmer = Farmer.objects.get(id=farmer_id)
        user = farmer.user

        # Compile message for the target user
        with translation.override(user.language or 'en'):
            message = translation.gettext("sms_ttpu_2_days_left").format(
                crop_name=produce.crop.name,
                checkin_date=produce.checkin.movement.date,
                cooling_unit=produce.crates.first().cooling_unit.name,
                checkin_code=produce.checkin.movement.code,
            )

        # Send the message
        send_sms(user.phone, message)

        return f"SMS sent to {user.phone}"

    except Farmer.DoesNotExist:
        return f"Farmer {farmer_id} does not exist."
    except Produce.DoesNotExist:
        return f"Produce {produce_id} does not exist."
    except Exception as e:
        return str(e)
