from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ViewSet

from base.apps.marketplace.models import Order
from base.apps.operation.models import Checkout


class DevelopmentViewSet(ViewSet):
    """
    A development-only viewset that provides endpoints to test and manipulate order statuses.
    
    Endpoints include:
      - test: A simple endpoint returning a "Hello World!" message.
      - mark-order-as-paid: Marks a specific order as paid.
      - mark-order-as-expired: Marks a specific order as expired.
      - mark-order-as-cancelled: Cancels a specific order.
    """
    permission_classes = (AllowAny,)
    lookup_field = 'id'

    @action(methods=['GET'], url_path='test', detail=False)
    def test(self, request):
        """Simple test endpoint returning 'Hello World!'."""
        return Response({"message": "Hello World!"}, status=HTTP_200_OK)

    @action(methods=['POST'], url_path='mark-order-as-paid', detail=False)
    @transaction.atomic
    def mark_order_as_paid(self, request):
        """
        Marks an order as paid.

        The endpoint retrieves the order using an 'order_id' from the query parameters,
        updates its amount_paid to the computed total, and, if the order is still in a 
        PAYMENT_PENDING status, completes the payment process.
        """
        order_id = request.query_params.get('order_id', None)
        if not order_id:
            return Response({"error": "Missing order_id"}, status=HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=order_id)
        try:
            # Update amount_paid to the computed total.
            order.amount_paid = order.cmp_total_amount

            if order.status == Order.Status.PAYMENT_PENDING:
                order.complete_payment_pending_order(
                    payment_through=Checkout.PaymentThrough.COLDTIVATE,
                    payment_gateway=Checkout.PaymentGateway.PAYTACK,
                    payment_method=Checkout.PaymentMethod.CREDIT_CARD, # TODO: get the payment method from the request
                )
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_200_OK)

    @action(methods=['POST'], url_path='mark-order-as-expired', detail=False)
    @transaction.atomic
    def mark_order_as_expired(self, request):
        """
        Marks an order as expired.

        This endpoint retrieves the order using an 'order_id' from the query parameters,
        updates its amount_paid, and if the order is still in PAYMENT_PENDING status, 
        expires the pending payment.
        """
        order_id = request.query_params.get('order_id')
        if not order_id:
            return Response({"error": "Missing order_id"}, status=HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=order_id)
        try:
            order.amount_paid = order.cmp_total_amount

            if order.status == Order.Status.PAYMENT_PENDING:
                order.expire_payment_pending_order()
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_200_OK)

    @action(methods=['POST'], url_path='mark-order-as-cancelled', detail=False)
    @transaction.atomic
    def mark_order_as_cancelled(self, request):
        """
        Cancels an order.

        This endpoint retrieves an order using an 'order_id' from the query parameters,
        updates its amount_paid, and if the order is in PAYMENT_PENDING status, cancels the order.
        """
        order_id = request.query_params.get('order_id')
        if not order_id:
            return Response({"error": "Missing order_id"}, status=HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=order_id)
        try:
            order.amount_paid = order.cmp_total_amount

            if order.status == Order.Status.PAYMENT_PENDING:
                order.cancel_payment_pending_order()
        except Exception as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response(status=HTTP_200_OK)
