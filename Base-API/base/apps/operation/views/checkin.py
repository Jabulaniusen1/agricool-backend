import json
from datetime import date

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.operation.models import Checkin, Movement
from base.apps.operation.serializers import CheckinSerializer
from base.apps.operation.services.checkin import update_checkin
from base.apps.storage.models import CoolingUnit, Produce
from base.apps.user.models import Farmer, Operator

# Constants
ERROR_MISSING_OWNER = "Please pass on the 'owned_by_user_id' and optionally the 'on_behalf_of_company_id'"
SUCCESS_CHECKIN_UPDATED = "Check in updated successfully"


class CheckinViewSet(
    RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet
):
    model = Checkin
    serializer_class = CheckinSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return self.model.objects.all()

    def create(self, request, *args, **kwargs):
        request_data = request.data.copy()

        if request_data["farmer_id"] is not None:
            request_data["farmer"] = request_data["farmer_id"]
            farmer = get_object_or_404(Farmer, id=request_data["farmer_id"])
            request_data["owned_by_user"] = farmer.user_id
        elif request_data["owned_by_user_id"] is not None:
            request_data["owned_by_user"] = request_data["owned_by_user_id"]
            request_data["owned_on_behalf_of_company"] = request_data[
                "owned_on_behalf_of_company_id"
            ]

        if not request_data["owned_by_user"]:
            return Response(
                {"error": ERROR_MISSING_OWNER},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = Movement.generate_code()
        movement_date = date.today()
        try:
            operator = Operator.objects.get(user_id=request.user.id)
        except Operator.DoesNotExist:
            return Response(
                {"error": "Operator not found for current user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        movement_instance = Movement.objects.create(
            code=code,
            date=movement_date,
            operator=operator,
            initiated_for=Movement.InitiatedFor.CHECK_IN,
        )
        request_data["movement"] = movement_instance.id

        produces = json.loads(request_data["produces"])

        cooling_unit = CoolingUnit.objects.get(
            id=produces[0]["crates"][0]["cooling_unit_id"]
        )

        serializer = self.serializer_class(
            data=request_data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        cooling_unit.compute(save=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        PATCH /operation/checkins/:id/
        """
        produce_id = kwargs.get("pk")
        produce = get_object_or_404(Produce, pk=produce_id)
        checkin_id = produce.checkin_id

        try:
            update_checkin(checkin_id, request.data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": SUCCESS_CHECKIN_UPDATED})

