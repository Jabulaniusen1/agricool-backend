from rest_framework import permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from base.apps.storage.models import Crop
from base.apps.storage.serializers import CropSerializer
from base.apps.user.models import Country, Farmer, Operator, ServiceProvider

# Filter exclusions
EXCLUDE_CROP_NAME = "Other"


class CropViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    model = Crop
    serializer_class = CropSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        user = self.request.user

        # For some countries we want to filter crops only specific to them
        try:
            country = ServiceProvider.objects.get(user=user).company.country.name
        except ServiceProvider.DoesNotExist:
            try:
                country = Operator.objects.get(user=user).company.country.name
            except Operator.DoesNotExist:
                try:
                    country = Farmer.objects.get(user=user).country
                except Farmer.DoesNotExist:
                    country = None

        is_filter_country = False
        for c in Country.objects.all():
            if c.country.name == country:
                is_filter_country = True
                break

        if is_filter_country:
            if "crop" in self.request.data:
                return self.model.objects.filter(
                    crop_type__id=self.request.query_params.get("crop"),
                    countryRelated__country__name=country,
                ).order_by("name")
            else:
                return (
                    self.model.objects.filter(countryRelated__country__name=country)
                    .exclude(name=EXCLUDE_CROP_NAME)
                    .order_by("name")
                )

        if "crop" in self.request.data:
            return self.model.objects.filter(
                crop_type__id=self.request.query_params.get("crop")
            ).order_by("name")
        else:
            return self.model.objects.all().order_by("name")
