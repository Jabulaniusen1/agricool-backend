from django.db.models import Exists, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import CoolingUnit, Crate, Location, Produce
from base.apps.storage.serializers import LocationSerializer
from base.apps.user.models import Farmer, ServiceProvider


class LocationViewSet(
    RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet
):
    model = Location
    serializer_class = LocationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if self.request.query_params.get("company"):
            return self.model.objects.filter(
                company=self.request.query_params.get("company"), deleted=False
            )
        elif self.request.query_params.get("farmer_id"):
            farmer = Farmer.objects.get(id=self.request.query_params.get("farmer_id"))
            cooling_units = CoolingUnit.objects.filter(
                (Q(public=True) | Q(pk__in=farmer.cooling_units.all())), deleted=False
            )
            cooling_units = map(lambda cu: cu.location.id, cooling_units)
            return self.model.objects.filter(pk__in=cooling_units, deleted=False)
        else:
            return self.model.objects.filter(deleted=False)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def delete(self, request, *args, **kwargs):
        user = request.user
        location_id = self.kwargs.get("pk")

        if not location_id:
            return Response(
                {"error": "Location ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        location = get_object_or_404(Location, id=location_id)
        company = location.company

        if not ServiceProvider.is_employee_of_company(user, company):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        cooling_units = CoolingUnit.objects.filter(location=location)
        if Produce.objects.filter(
            Q(crates__cooling_unit__in=cooling_units)
            & Exists(Crate.generate_checkedin_crates_subquery())
        ).exists():
            return Response(
                {
                    "error": "This location cannot be deleted because it has cooling units with active check-ins"
                },
                status=status.HTTP_409_CONFLICT,
            )

        location.deleted = True
        location.save()
        CoolingUnit.objects.filter(location=location).update(deleted=True)

        return Response(
            {"success": "Successfully deleted location and its cooling units"},
            status=status.HTTP_200_OK,
        )
