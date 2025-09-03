from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ViewSet

from base.apps.marketplace.models import Order
from base.utils.currencies import flat_int_to_float

# Webhook event types
WEBHOOK_EVENT_CHARGE_SUCCESS = "charge.success"

# Error messages
ERROR_EVENT_NOT_IMPLEMENTED = "Event not yet implemented"
ERROR_ORDER_ID_NOT_FOUND = "Order ID not found"
ERROR_ORDER_REFERENCE_NOT_FOUND = "Order reference not found"


# Create a viewset to receive webhooks from Paystack
class WebhooksPaystackViewSet(ViewSet):
    permission_classes = (AllowAny,)

    def create(self, request):
        event = request.data.get('event')
        data = request.data.get('data', {})

        # # Validate the request with hmac sha512
        # received_signature = request.headers.get('X-PAYSTACK-SIGNATURE')
        # if not received_signature:
        #     return Response({"error": "No signature provided"}, status=HTTP_400_BAD_REQUEST)

        # # Ensure request.data is serialized to a string and encoded as bytes
        # request_data_str = json.dumps(request.data)
        # request_data_bytes = request_data_str.encode('utf-8')
        # print(request_data_bytes)
        # # Validate event by generating hash
        # hash_obj = hmac.new(PAYSTACK_SECRET_KEY.encode('utf-8'), msg=request_data_bytes, digestmod=hashlib.sha512)
        # generated_signature = hash_obj.hexdigest()

        # # confirm that the hash matches the signature
        # if generated_signature != received_signature:
        #     print(f"received signature: {received_signature}")
        #     print(f"generated signature: {generated_signature}")
        #     return Response({"error": "Signature does not match"}, status=HTTP_400_BAD_REQUEST)

        # switch case based on request.event
        if event == WEBHOOK_EVENT_CHARGE_SUCCESS:
            return self.process_charge_succeeded(data)

        # if request.event == 'charge.failed':
        #     return self.process_charge_failed(data)
        # if request.event == 'charge.refunded':
        #     return self.process_charge_refunded(data)
        # if request.event == 'charge.expired':
        #     return self.process_charge_expired(data)
        # if request.event == 'charge.voided':
        #     return self.process_charge_voided(data)
        # if request.event == 'charge.dispute.created':
        #     return self.process_charge_dispute_created(data)
        # if request.event == 'charge.dispute.updated':
        #     return self.process_charge_dispute_updated(data)
        # if request.event == 'charge.dispute.closed':
        #     return self.process_charge_dispute_closed(data)
        # if request.event == 'charge.dispute.expired':
        #     return self.process_charge_dispute_expired(data)
        # if request.event == 'charge.dispute.won':
        #     return self.process_charge_dispute_won(data)
        # if request.event == 'charge.dispute.lost':
        #     return self.process_charge_dispute_lost(data)

        # Report that this is not yet implemented
        return Response({"error": ERROR_EVENT_NOT_IMPLEMENTED}, status=HTTP_400_BAD_REQUEST)

    def process_charge_succeeded(self, data={}):
        from base.apps.operation.models import Checkout

        # Gather values from the request
        reference = data.get('reference')
        currency = data.get('currency')
        metadata = data.get('metadata', {})
        order_id = metadata.get('order_id')
        amount_paid = flat_int_to_float(data.get('amount'), currency)

        if not order_id:
            return Response({"error": ERROR_ORDER_ID_NOT_FOUND}, status=HTTP_400_BAD_REQUEST)

        # Identify the order
        order = Order.objects.filter(id=order_id).first()

        if not order:
            return Response({"error": ERROR_ORDER_REFERENCE_NOT_FOUND}, status=HTTP_400_BAD_REQUEST)

        try:
            # update the amount paid
            order.amount_paid += amount_paid

            if order.status == Order.Status.PAYMENT_PENDING:
                order.complete_payment_pending_order(
                    payment_through=Checkout.PaymentThrough.COLDTIVATE,
                    payment_gateway=Checkout.PaymentGateway.PAYSTACK,
                    payment_method=Checkout.PaymentMethod.CREDIT_CARD, # TODO: get the payment method from the request
                )
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_200_OK)
