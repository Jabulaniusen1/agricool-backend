from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.operation.models import Checkout, Movement
from base.apps.operation.serializers import CheckoutSerializer
from base.apps.storage.models import Crate
from base.apps.user.models import Operator
from base.celery import app


class CheckoutViewSet(ListModelMixin, CreateModelMixin, GenericViewSet):
    model = Checkout
    serializer_class = CheckoutSerializer
    permission_classes = (permissions.AllowAny,)
    # use the movement_id instead of code
    lookup_field = "movement_id"

    def get_queryset(self):
        code = self.request.query_params.get("code")

        if code:
            try:
                checkout = self.model.objects.get(movement__code=code)
                crates = Crate.objects.filter(
                    partial_checkouts__checkout_id=checkout.id
                )
                return crates
            except:
                return None
        else:
            return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        request_data = request.data.copy()

        code = Movement.generate_code()
        movement_date = date.today()
        operator = Operator.objects.get(user_id=self.request.user.id)
        movement_instance = Movement.objects.create(
            code=code,
            date=movement_date,
            operator=operator,
            initiated_for=Movement.InitiatedFor.CHECK_OUT,
        )
        request_data["movement"] = movement_instance.id

        serializer = self.serializer_class(
            data=request_data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        serializer.save()
        return Response(serializer.data, status=200)

    @action(detail=True, methods=["POST"], url_path="send_sms_report")
    def send_sms_report(self, request, movement_id=None):
        """GET /operation/checkouts/:movement_id/send_sms_report - sends an SMS report to a user"""

        checkout = get_object_or_404(Checkout, movement_id=movement_id)
        app.send_task(
            "base.apps.operation.tasks.sms.send_sms_checkout_movement_report",
            args=[checkout.id, request.user.id],
        )

        return Response(status=200)
