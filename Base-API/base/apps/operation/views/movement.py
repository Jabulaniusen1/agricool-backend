from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.operation.models import Movement
from base.apps.operation.serializers import MovementSerializer


def parse_comma_separated_params(param_string):
    """Helper function to parse comma-separated query parameters."""
    return param_string.split(",") if param_string else []


class MovementViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Movement
    serializer_class = MovementSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        cooling_unit_id = self.request.query_params.get("cooling_unit")
        farmer_id = self.request.query_params.get("farmer_id")
        owned_by_user_id = self.request.query_params.get("owned_by_user_id")

        queryset = self.model.objects.all()

        if cooling_unit_id:
            queryset = queryset.filter(
                Q(checkins__produces__crates__cooling_unit=cooling_unit_id)
                | Q(checkouts__partial_checkouts__crate__cooling_unit=cooling_unit_id)
            )

        if farmer_id:
            queryset = queryset.filter(
                Q(checkins__owned_by_user__farmer__id=farmer_id)
                | Q(
                    checkouts__partial_checkouts__crate__produce__checkin__owned_by_user__farmer__id=farmer_id
                )
            )

        if owned_by_user_id:
            queryset = queryset.filter(
                Q(checkins__owned_by_user_id=owned_by_user_id)
                | Q(
                    checkouts__partial_checkouts__crate__produce__checkin__owned_by_user_id=owned_by_user_id
                )
            )

        return queryset.order_by("-date").distinct()

    def list(self, request, *args, **kwargs):
        serializer = MovementSerializer.optimized_init(self.get_queryset())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="revenue")
    def get_checkouts_revenue(self, request, *args, **kwargs):
        cooling_units = parse_comma_separated_params(
            self.request.query_params.get("cooling_units", "")
        )
        payment_methods = parse_comma_separated_params(
            self.request.query_params.get("payment_methods", "")
        )

        serializer = MovementSerializer.optimized_init(
            (
                self.model.objects.all()
                .filter(
                    Q(
                        checkouts__partial_checkouts__crate__cooling_unit__in=cooling_units
                    )
                    & Q(checkouts__payment_method__in=payment_methods)
                )
                .order_by("-date")
                .distinct()
            )
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="usage")
    def get_checkouts_usage(self, request, *args, **kwargs):
        cooling_units = parse_comma_separated_params(
            self.request.query_params.get("cooling_units", "")
        )
        serializer = MovementSerializer.optimized_init(
            (
                self.model.objects.filter(
                    Q(checkins__produces__crates__cooling_unit__in=cooling_units)
                )
            )
        )

        return Response(serializer.data, status=status.HTTP_200_OK)
