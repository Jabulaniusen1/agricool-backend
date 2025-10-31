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
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        country = None

        # For some countries we want to filter crops only specific to them
        if user.is_authenticated:
            try:
                service_provider = ServiceProvider.objects.get(user=user)
                if service_provider.company and service_provider.company.country:
                    country = service_provider.company.country.name
            except (ServiceProvider.DoesNotExist, AttributeError):
                try:
                    operator = Operator.objects.get(user=user)
                    if operator.company and operator.company.country:
                        country = operator.company.country.name
                except (Operator.DoesNotExist, AttributeError):
                    try:
                        farmer = Farmer.objects.get(user=user)
                        if farmer.country:
                            country = farmer.country
                    except (Farmer.DoesNotExist, AttributeError):
                        pass

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
