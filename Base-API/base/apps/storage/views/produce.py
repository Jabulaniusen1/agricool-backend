from django.db.models import Exists, OuterRef, Prefetch, Q
from rest_framework import permissions, status
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.marketplace.models import MarketListedCrate
from base.apps.storage.models import CoolingUnit, CoolingUnitCrop, Crate, Produce
from base.apps.storage.serializers import ProduceSerializer
from base.apps.user.models import Farmer, Operator, ServiceProvider


class IsOperatorOrServiceProviderForCoolingUnit(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        cooling_unit_id = view.kwargs.get("cooling_unit_id")
        if not cooling_unit_id:
            return False

        try:
            cooling_unit = CoolingUnit.objects.select_related("location__company").get(
                id=cooling_unit_id
            )
            company = cooling_unit.location.company

            # Check if user is Operator or ServiceProvider for the cooling unit's company
            return Operator.is_operator_of_company(
                request.user, company
            ) or ServiceProvider.is_employee_of_company(request.user, company)
        except CoolingUnit.DoesNotExist:
            return False


class IsFarmerOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        farmer_id = view.kwargs.get("farmer_id")
        cooling_unit_id = view.kwargs.get("cooling_unit_id")
        
        if not farmer_id or not cooling_unit_id:
            return False

        try:
            # Check if farmer belongs to authenticated user AND is associated with the cooling unit
            farmer = Farmer.objects.get(
                id=farmer_id, 
                user=request.user,
                cooling_units=cooling_unit_id
            )
            return True
        except Farmer.DoesNotExist:
            return False


class ProduceViewSet(
    RetrieveModelMixin,
    UpdateModelMixin,
    GenericViewSet,
    CreateModelMixin,
):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (permissions.AllowAny,)

    def list(self, request, *args, **kwargs):
        return Response(
            {"detail": "Generic produce listing is disabled. Use specific endpoints."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def get_queryset(self):
        return self.model.objects.none()


class CoolingUnitProduceViewSet(ListModelMixin, GenericViewSet):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (IsOperatorOrServiceProviderForCoolingUnit,)

    def get_queryset(self):
        cooling_unit_id = self.kwargs.get("cooling_unit_id")

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
            "checkin__movement__operator",
            "checkin__movement__operator__user",
            "crop",
        ).prefetch_related(
            Prefetch("crates", queryset=crates_qs),
        )

        return queryset


class FarmerCoolingUnitProduceViewSet(ListModelMixin, GenericViewSet):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (IsFarmerOwner,)

    def get_queryset(self):
        cooling_unit_id = self.kwargs.get("cooling_unit_id")
        farmer_id = self.kwargs.get("farmer_id")

        queryset = (
            self.model.objects.filter(
                Q(crates__cooling_unit=cooling_unit_id)
                & Q(checkin__owned_by_user__farmer__id=farmer_id)
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
            "checkin__movement__operator",
            "checkin__movement__operator__user",
            "crop",
        ).prefetch_related(
            Prefetch("crates", queryset=crates_qs),
        )

        return queryset
