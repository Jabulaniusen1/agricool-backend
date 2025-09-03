import random
import string

from django.db import transaction
from django.db.models import Case, CharField, OuterRef, Subquery, Value, When

from base.apps.marketplace.models import Order, PaystackAccount
from base.apps.marketplace.payment_processor.paystack import paystack
from base.utils.currencies import float_to_flat_int, is_valid_currency

# Payment reference configuration
PAYMENT_REFERENCE_LENGTH = 12

# Payment types
PAYMENT_TYPE_COOLING_FEES = "cooling-fees"
PAYMENT_TYPE_PRODUCE = "produce"

# Paystack split configuration
SPLIT_TYPE_FLAT = "flat"
SPLIT_CURRENCY_NGN = "NGN"
SPLIT_BEARER_TYPE_ACCOUNT = "account"

# Email domain suffixes
COMPANY_EMAIL_DOMAIN = "@company.coldtivate.org"
USER_EMAIL_DOMAIN = "@user.coldtivate.org"

# Callback URLs
BASE_APP_URL = "https://in-app.coldtivate.org"
PAYMENT_CALLBACK_URL_TEMPLATE = f"{BASE_APP_URL}/order/{{order_id}}/payment/callback"
PAYMENT_CANCEL_URL_TEMPLATE = f"{BASE_APP_URL}/order/{{order_id}}/payment/cancel"


def generate_payment_reference() -> str:
    """Generates a random payment reference."""
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(PAYMENT_REFERENCE_LENGTH))


@transaction.atomic
def set_the_order_as_pending_payment(order: Order) -> None:
    """
    Sets the order state to PAYMENT_PENDING by:
      - Recomputing order totals.
      - Validating currency and existence of order items.
      - Annotating order items with Paystack subaccount codes.
      - Creating split groups on Paystack.
      - Updating the order state.
    """
    splits = []
    subaccounts_share = {}

    # Recompute order totals
    order.compute(save=True)

    currency = order.currency
    if not is_valid_currency(currency):
        raise ValueError(f"Invalid currency code: {currency}")

    if order.items.count() == 0:
        raise ValueError(f"No crate items found for order {order.id}")

    # Get, in a single query, the splits for the order by:
        # - Getting the amount to pay in cooling feesto the cooling company
        # - Getting the amount to pay for the produce to the seller
        # - Getting the paystack account for the cooling company and seller
    order_crate_items = order.items.annotate(
        cooling_company_subaccount_code=Subquery(
            PaystackAccount.objects.filter(
                owned_on_behalf_of_company=OuterRef('market_listed_crate__crate__cooling_unit__location__company'),
                is_default_account=True,
            ).values('paystack_subaccount_code')[:1]
        ),
        seller_subaccount_code=Case(
            When(
                market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id__isnull=True,
                then=Subquery(
                    PaystackAccount.objects.filter(
                        is_default_account=True,
                        owned_by_user=OuterRef('market_listed_crate__crate__produce__checkin__owned_by_user'),
                        owned_on_behalf_of_company_id__isnull=True,
                    ).values('paystack_subaccount_code')[:1]
                )
            ),
            When(
                market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id__isnull=False,
                then=Subquery(
                    PaystackAccount.objects.filter(
                        is_default_account=True,
                        owned_on_behalf_of_company_id=OuterRef('market_listed_crate__crate__produce__checkin__owned_on_behalf_of_company_id'),
                    ).values('paystack_subaccount_code')[:1]
                )
            ),
            default=Value(None),
            output_field=CharField()
        ),
    )

    # Then, iterate through each line and create two splits for each line
    for order_crate_item in order_crate_items.iterator():
        if not order_crate_item.cooling_company_subaccount_code:
            raise ValueError(f"Missing account for Cooling Company on crate {order_crate_item.market_listed_crate.crate_id}")

        if not order_crate_item.seller_subaccount_code:
            raise ValueError(f"Missing account for Seller on crate {order_crate_item.market_listed_crate.crate_id}")

        # Define split for cooling fees
        cooling_fees_split = {
            'payment_type': PAYMENT_TYPE_COOLING_FEES,
            'subaccount_code': order_crate_item.cooling_company_subaccount_code,
            'amount': float_to_flat_int(order_crate_item.cmp_cooling_fees_amount, currency),
        }
        # Define split for produce payment
        produce_seller_split = {
            'payment_type': PAYMENT_TYPE_PRODUCE,
            'subaccount_code': order_crate_item.seller_subaccount_code,
            'amount': float_to_flat_int(
                max(order_crate_item.cmp_produce_amount - order_crate_item.cmp_discount_amount - order_crate_item.cmp_cooling_fees_amount, 0),
                currency,
            ),
        }

        splits.extend([cooling_fees_split, produce_seller_split])

        # Add to subaccounts share
        ## Cooling Fees
        subaccounts_share.setdefault(cooling_fees_split['subaccount_code'], 0)
        subaccounts_share[cooling_fees_split['subaccount_code']] += cooling_fees_split['amount']
        ## Produce
        subaccounts_share.setdefault(produce_seller_split['subaccount_code'], 0)
        subaccounts_share[produce_seller_split['subaccount_code']] += produce_seller_split['amount']

    # Build the subaccounts array for the split group
    subaccounts_arr = []
    for subaccount_code, amount in subaccounts_share.items():
        subaccounts_arr.append({
            'subaccount': subaccount_code,
            'share': amount, # already flattened
        })

    common_args = {
        "type": SPLIT_TYPE_FLAT,
        "currency": SPLIT_CURRENCY_NGN,
        "bearer_type": SPLIT_BEARER_TYPE_ACCOUNT,
        "subaccounts": subaccounts_arr
    }

    # Check if the total amount of splits is equal to the order amount
    total_splits_amount = sum(split['amount'] for split in splits)
    total_order_amount = float_to_flat_int(
        order.cmp_total_amount - order.cmp_total_coldtivate_amount - order.cmp_total_payment_fees_amount,
        currency
    )

    if total_splits_amount != total_order_amount:
        print(
            f"Total amount of splits ({total_splits_amount} flattened) does not equal the order amount "
        )

    # Create or update the split group on Paystack
    if order.paystack_split_code is None:
        response = paystack.transactionSplit.create(
            name=f"Order #{order.id}",
            **common_args  # Unpack common arguments
        )
    else:
        response = paystack.transactionSplit.update(
            split_id=order.paystack_split_id,
            **common_args  # Unpack common arguments
        )

    response_body = response.get('data', {})

    if not response_body:
        raise ValueError(f"Failed to create or update split group in Paystack: {response.get('message', 'No message provided')}")

    paystack_split_code = response_body.get('split_code', None)
    if not paystack_split_code:
        raise ValueError(f"Failed to create or update split group in Paystack: {response.get('message', 'No message provided')}")

    order.paystack_split_code = paystack_split_code
    if not order.paystack_split_code:
        raise ValueError("Failed to create or update split group in paystack")

    # moving the order state to payment pending:
        # - disables it as a cart
        # - reduces the total market available weight
        # - allows to draw back the order if the payment is not completed within its deadline
    order.status = Order.Status.PAYMENT_PENDING
    order.save()


def get_checkout_url_for_order(order: Order) -> str:
    """
    Initializes a Paystack transaction for the order and returns the checkout URL.
    
    Args:
        order (Order): The order for which to generate the checkout URL.
    
    Returns:
        str: The authorization URL for the transaction.
    
    Raises:
        ValueError: If the split group code or authorization URL is missing.
    """
    if not order.paystack_split_code:
        raise ValueError("Missing split group code in the order.")

    payment_reference = generate_payment_reference()
    hidden_email = (
        f"{order.owned_on_behalf_of_company_id}{COMPANY_EMAIL_DOMAIN}"
        if order.owned_on_behalf_of_company_id
        else f"{order.created_by_user_id}{USER_EMAIL_DOMAIN}"
    )

    response = paystack.transaction.initialize(
        split_code=order.paystack_split_code,
        bearer="account",
        currency=order.currency,
        email=hidden_email,
        reference=payment_reference,
        amount=float_to_flat_int(order.cmp_total_amount, order.currency),
        callback_url=PAYMENT_CALLBACK_URL_TEMPLATE.format(order_id=order.id),
        metadata={
            "order_id": order.id,
            "cancel_action": PAYMENT_CANCEL_URL_TEMPLATE.format(order_id=order.id),
        }
    )

    payload = response.get('data', {})
    authorization_url = payload.get('authorization_url', None)
    if not authorization_url:
        raise ValueError(f"Failed to initialize the transaction: {response.get('message', 'No message provided')}")

    order.payment_references.append(payment_reference)
    order.save()

    return authorization_url
