from django.utils import translation
from base.apps.user.models import User
from base.apps.operation.models import Checkout, Movement
from base.utils.services.sms import send_sms
from base.celery import app
from base.apps.operation.serializers import MovementSerializer

# Constants
DEFAULT_LANGUAGE = 'en'
DEFAULT_VALUE_NA = "N/A"
DATE_FORMAT_SMS = "%Y-%m-%d %H:%M"
CROP_NAME_SEPARATOR = ', '
ERROR_CHECKOUT_NOT_FOUND = "Checkout {checkout_id} does not exist."
ERROR_USER_NOT_FOUND = "User {user_id} does not exist."
SUCCESS_SMS_SENT = "SMS sent to {phone}"

@app.task
def send_sms_checkout_movement_report(checkout_id, user_id):
    try:
        # Fetch the order and user details
        checkout = Checkout.objects.get(id=checkout_id)
        user = User.objects.get(id=user_id)
        movement = checkout.movement

        crates = []
        total_price = None
        owner_user = None
        owner_company = None
        owner = ""
        sum_weight = 0

        if (movement.initiated_for == Movement.InitiatedFor.CHECK_IN or 
            movement.initiated_for == Movement.InitiatedFor.MARKETPLACE_ORDER):
            checkin = movement.checkins.first()
            crates = [
                crate
                for produce in checkin.produces.all()
                for crate in produce.crates.all()
            ]
            owner_user = checkin.owned_by_user
            owner_company = checkin.owned_on_behalf_of_company
            sum_weight = sum(crate.weight for crate in crates)

        elif movement.initiated_for == Movement.InitiatedFor.CHECK_OUT:
            checkout = movement.checkouts.first()
            total_price = checkout.cmp_total_amount or None
            partial_checkouts = checkout.partial_checkouts.all()
            crates = [
                partial_checkout.crate
                for partial_checkout in partial_checkouts
            ]
            if crates:
                owner_user = crates[0].produce.checkin.owned_by_user
                owner_company = crates[0].produce.checkin.owned_on_behalf_of_company
            else:
                owner_user = None
                owner_company = None
            sum_weight = sum(partial_checkout.weight_in_kg for partial_checkout in partial_checkouts)

        movement_crops = list({
            crate.produce.crop.id: {"name": crate.produce.crop.name, "id": crate.produce.crop.id}
            for crate in crates
        }.values())

        if owner_company:
            owner = f"{owner_company.name}"
        elif owner_user:
            owner = f"{owner_user.first_name} {owner_user.last_name}"

        # Get cooling unit and company
        if not crates:
            return "No crates found for this movement"
        
        company = crates[0].cooling_unit.location.company

        # Get all the affected crates by filtering the affected order items
        with translation.override(user.language or DEFAULT_LANGUAGE):
            movement_type = DEFAULT_VALUE_NA
            movement_type_for_date = DEFAULT_VALUE_NA

            if movement.initiated_for == Movement.InitiatedFor.CHECK_IN:
                movement_type = translation.gettext("movement_type_checkin")
                movement_type_for_date = translation.gettext("movement_type_checked_in")
            elif movement.initiated_for == Movement.InitiatedFor.CHECK_OUT:
                movement_type = translation.gettext("movement_type_check_out")
                movement_type_for_date = translation.gettext("movement_type_checked_out")

            # Compose the SMS content
            message = translation.gettext("sms_history_sms_report").format(
                company_name=company.name,
                movement_type=movement_type,
                movement_type_for_date=movement_type_for_date,
                code=movement.code,
                crops=CROP_NAME_SEPARATOR.join([crop['name'] for crop in movement_crops]),
                weight=sum_weight,
                date=movement.date.strftime(DATE_FORMAT_SMS),
                price=total_price or DEFAULT_VALUE_NA,
                farmers_name=owner,
            )

        # Send the message
        send_sms(user.phone, message)

        return SUCCESS_SMS_SENT.format(phone=user.phone)

    except Checkout.DoesNotExist:
        return ERROR_CHECKOUT_NOT_FOUND.format(checkout_id=checkout_id)
    except User.DoesNotExist:
        return ERROR_USER_NOT_FOUND.format(user_id=user_id)
    except (AttributeError, IndexError) as e:
        return f"Data structure error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
