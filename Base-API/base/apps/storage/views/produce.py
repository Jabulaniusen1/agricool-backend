from django.db.models import Exists, OuterRef, Prefetch, Q
from rest_framework import permissions
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from base.apps.marketplace.models import MarketListedCrate
from base.apps.storage.models import CoolingUnitCrop, Crate, Produce
from base.apps.storage.serializers import ProduceSerializer


class ProduceViewSet(
    RetrieveModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    GenericViewSet,
    CreateModelMixin,
):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        cooling_unit_id = self.request.query_params.get("cooling_unit")

        queryset = (
            self.model.objects.filter(
                Q(crates__cooling_unit=cooling_unit_id)
                & Exists(Crate.generate_checkedin_crates_subquery())
            )
            .distinct()
            .order_by("-checkin__movement__date")
        )

        # Define subqueries for annotations
        listed_qs = MarketListedCrate.objects.filter(
            crate_id=OuterRef("pk"),
            delisted_at__isnull=True,
        )
        locked_qs = MarketListedCrate.objects.filter(
            crate_id=OuterRef("pk"),
            delisted_at__isnull=True,
            cmp_weight_locked_in_payment_pending_orders_in_kg__gt=0,
        )

        # Annotated Crates queryset
        crates_qs = (
            Crate.objects.filter(weight__gt=0)
            .annotate(
                is_listed_in_the_marketplace=Exists(listed_qs),
                is_locked_within_pending_orders=Exists(locked_qs),
            )
            .select_related("cooling_unit", "cooling_unit__location__company")
            .prefetch_related(
                Prefetch(
                    "cooling_unit__crop_cooling_unit",
                    queryset=CoolingUnitCrop.objects.select_related("pricing", "crop"),
                    to_attr="all_crop_cooling_units",
                ),
            )
        )

        # Prefetch related fields to solve the 1+N problem
        queryset = queryset.select_related(
            "checkin__owned_by_user",
            "checkin__owned_by_user__farmer",
            "checkin__movement",
            "checkin__movement__operator",  # Added operator join
            "checkin__movement__operator__user",  # Added users operator join
            "crop",
        ).prefetch_related(
            Prefetch("crates", queryset=crates_qs),
        )

        if self.request.query_params.get("farmer_id"):
            queryset = queryset.filter(
                checkin__owned_by_user__farmer__id=self.request.query_params.get(
                    "farmer_id"
                )
            )

        return queryset
