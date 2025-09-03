from django.db.models import Count, F, Sum
from django.utils import translation

from base.apps.marketplace.models import MarketListedCratePrice, Order
from base.apps.user.models import User
from base.celery import app
from base.utils.services.sms import send_sms

# Default language constant
DEFAULT_LANGUAGE = 'en'

# Translation key constants
TRANSLATION_ORDER_DETAILS = 'sms_marketplace_order_seller_notice_details'
TRANSLATION_ORDER_NOTICE = 'sms_marketplace_order_seller_notice'
TRANSLATION_PRICE_CHANGE_DETAILS = 'sms_marketplace_seller_market_listed_crates_price_changed_details'
TRANSLATION_PRICE_CHANGE_NOTICE = 'sms_marketplace_seller_market_listed_crates_price_changed'

# Success message templates
SMS_SENT_SUCCESS = "SMS sent to {phone}"

# Error message templates
ERROR_ORDER_NOT_FOUND = "Order {order_id} does not exist."
ERROR_USER_NOT_FOUND = "User {user_id} does not exist."
ERROR_PRICE_NOT_FOUND = "MarketListedCratePrice {price_ids} does not exist."
ERROR_GENERAL = "Something went wrong: {error}"


@app.task
def send_sms_notification_to_owner_on_order_completed(order_id, user_id):
    """
    Sends an SMS notification to the seller when an order is completed.

    Retrieves the order and user details, aggregates relevant order item data
    (such as crop name, weight, and amount), and constructs a localized SMS message
    that is then sent to the user's phone.
    
    Returns a confirmation message on success or a string describing the error.
    """
    try:
        # Fetch the order and user details
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return ERROR_ORDER_NOT_FOUND.format(order_id=order_id)
            
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return ERROR_USER_NOT_FOUND.format(user_id=user_id)

        details = []

        # Use the user's language for message translations
        with translation.override(user.language or DEFAULT_LANGUAGE):
            # Aggregate order items for the user from affected crates
            items = (
                order.items
                .filter(
                    market_listed_crate__crate__produce__checkin__owned_by_user=user_id,
                )
                .values(
                    'market_listed_crate__crate__produce__crop_id',
                    'market_listed_crate__crate__produce__crop__name',
                    'ordered_produce_weight',
                    'cmp_produce_amount',
                    'cmp_discount_amount',
                )
                .annotate(
                    num_of_crates=Count('market_listed_crate__crate__produce__crop_id'),
                    crop_name=F('market_listed_crate__crate__produce__crop__name'),
                    weight_in_kg=Sum('ordered_produce_weight'),
                    amount=Sum('cmp_produce_amount') - Sum('cmp_discount_amount'),
                )
                .values(
                    'num_of_crates',
                    'crop_name',
                    'weight_in_kg',
                    'amount',
                )
            )

            # Build a detailed message for each aggregated item
            for item in items:
                detailed_item_message = translation.gettext(
                    TRANSLATION_ORDER_DETAILS
                ).format(
                    crop_name=item['crop_name'],
                    weight_in_kg=item['weight_in_kg'],
                    amount=item['amount'],
                    currency=order.currency,
                )
                details.append(detailed_item_message)

            # Construct the overall notification message
            message = translation.gettext(TRANSLATION_ORDER_NOTICE).format(
                details='\n'.join(details),
                order_id=order.id,
            )

        # Send the SMS
        send_sms(user.phone, message)
        return SMS_SENT_SUCCESS.format(phone=user.phone)

    except Exception as e:
        return str(e)


@app.task
def send_sms_notification_to_owner_on_listing_price_changed(market_listed_crate_price_ids, user_id):
    """
    Sends an SMS notification to the seller when there is a change in the listing price
    of one or more market-listed crates.

    Fetches the related Paystack account pricing details, constructs a localized SMS
    message including details like the cooling unit name, crop name, and the updated price
    for each crate, and sends it to the seller's phone.

    Returns a confirmation string on success or an error message on failure.
    """
    try:
        # Fetch user record and list of market listed crate prices
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return ERROR_USER_NOT_FOUND.format(user_id=user_id)
            
        market_listed_crate_prices = MarketListedCratePrice.objects.filter(id__in=market_listed_crate_price_ids)
        if not market_listed_crate_prices.exists():
            return ERROR_PRICE_NOT_FOUND.format(price_ids=market_listed_crate_price_ids)
        
        # Extract shared info from the first related crate
        first_crate = market_listed_crate_prices.first().market_listed_crate.crate
        cooling_unit_name = first_crate.cooling_unit.name
        crop_name = first_crate.produce.crop.name

        details = []

        # Use user's language for translation
        with translation.override(user.language or DEFAULT_LANGUAGE):
            # Build details for each listing price
            for market_listed_crate_price in market_listed_crate_prices:
                crate = market_listed_crate_price.market_listed_crate.crate
                detailed_item_message = translation.gettext(
                    TRANSLATION_PRICE_CHANGE_DETAILS
                ).format(
                    crate_id=crate.id,
                    produce_price_in_kg=market_listed_crate_price.produce_price_per_kg,
                    currency=crate.currency,
                )
                details.append(detailed_item_message)

            # Construct the overall SMS message
            message = translation.gettext(TRANSLATION_PRICE_CHANGE_NOTICE).format(
                cooling_unit_name=cooling_unit_name,
                crop_name=crop_name,
                details='\n'.join(details),
            )

        # Send the SMS to the seller's phone
        send_sms(user.phone, message)
        return SMS_SENT_SUCCESS.format(phone=user.phone)

    except Exception as e:
        return ERROR_GENERAL.format(error=e)