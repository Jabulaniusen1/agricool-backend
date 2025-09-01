from itertools import chain

from django.db.models import Exists, Q
from rest_framework import permissions
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Crate, Produce
from base.apps.storage.serializers import ProduceSerializer


class NextCheckoutViewSet(ListModelMixin, GenericViewSet):
    model = Produce
    serializer_class = ProduceSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        by_remaining_shelf_life = (
            self.model.objects.filter(
                Q(crates__cooling_unit=self.request.query_params.get("cooling_unit"))
                & Exists(Crate.generate_checkedin_crates_subquery())
                & ~Q(crates__modified_dt=None)
            )
            .distinct()
            .order_by("crates__remaining_shelf_life")
        )
        by_planned_days = (
            self.model.objects.filter(
                Q(crates__cooling_unit=self.request.query_params.get("cooling_unit"))
                & Exists(Crate.generate_checkedin_crates_subquery())
                & Q(crates__modified_dt=None)
                & ~Q(crates__planned_days=None)
            )
            .distinct()
            .order_by("crates__planned_days")
        )
        by_checkout = (
            self.model.objects.filter(
                Q(crates__cooling_unit=self.request.query_params.get("cooling_unit"))
                & Exists(Crate.generate_checkedin_crates_subquery())
                & Q(crates__modified_dt=None)
                & Q(crates__planned_days=None)
            )
            .distinct()
            .order_by("-checkin__movement__date")
        )
        return list(
            dict.fromkeys(
                list(chain(by_remaining_shelf_life, by_planned_days, by_checkout))
            )
        )
