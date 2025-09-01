from django.shortcuts import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.operation.models import Checkout, Movement
from base.apps.operation.services.checkout_to_checkin import convert_checkout_to_checkin
from base.apps.storage.models import Crate
from base.apps.storage.serializers import CrateSerializer
from base.apps.user.models import Farmer


class CheckoutToCheckinViewSet(ListModelMixin, CreateModelMixin, GenericViewSet):
    model = Crate
    serializer_class = CrateSerializer

    def list(self, request):
        code = self.request.query_params.get("code")

        if code:
            try:
                movement = Movement.objects.get(code=code, used_for_checkin=False)
                checkout = Checkout.objects.get(movement=movement)
                crates = Crate.objects.filter(
                    partial_checkouts__checkout_id=checkout.id
                )

                # Fix:
                # This is a temporary fix and could later be changed with a more appropriate solution
                # The crate doesn't have a reference for the latest checkout weight
                # The crate's weight determines its current weight, and the initial weight is the weight of the crate when it was checked in
                # But in the meantime, there could have been several partial checkouts that caused the weight to change over time.ArithmeticError
                # We're only interested to gather the latest checkout weight, so we will be patching this value just for the read aspect of it
                for crate in crates:
                    latest_crate_partial_checkout = crate.partial_checkouts.latest("id")
                    weight_to_be_considered_in_kg = (
                        latest_crate_partial_checkout.weight_in_kg
                        if latest_crate_partial_checkout
                        else crate.initial_weight
                    )

                    crate.weight = weight_to_be_considered_in_kg
                    crate.initial_weight = weight_to_be_considered_in_kg

                serializer = CrateSerializer(crates, many=True)
                return Response(serializer.data)
            except:
                return Response(
                    {"message": "This code has already been used for a check in."},
                    status=404,
                )
        else:
            return None

    def create(self, request, *args, **kwargs):
        params = request.data["params"]
        checkout_code = params["code"]
        cooling_unit_id = params["coolingUnitId"]
        days = params.get("days")
        tags = params.get("tags", [])

        # Determine ownership
        if params.get("farmer"):
            farmer = get_object_or_404(Farmer, id=params["farmer"])
            owned_by_user_id = farmer.user_id
        else:
            owned_by_user_id = params["owned_by_user"]

        # Call service
        convert_checkout_to_checkin(
            checkout_code=checkout_code,
            owned_by_user_id=owned_by_user_id,
            cooling_unit_id=cooling_unit_id,
            days=days,
            tags=tags,
            operator_user_id=request.user.id,
        )

        return Response({"message": "Successfully moved crate"}, status=200)
