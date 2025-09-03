from django.utils.translation import gettext_lazy as _
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers

from base.apps.storage.models import CoolingUnit, CoolingUnitCrop, Crop, Pricing
from base.apps.user.models import BankAccount, Company


class CompanySerializer(CountryFieldMixin, serializers.ModelSerializer):
    has_cooling_units = serializers.SerializerMethodField()
    bank_details = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = "__all__"

    def get_has_cooling_units(self, instance):
        if CoolingUnit.objects.filter(location__company=instance, deleted=False):
            return True
        else:
            return False

    def get_bank_details(self, instance):
        if instance.bank_account:
            return {
                "id": instance.bank_account.id,
                "bank_name": instance.bank_account.bank_name,
                "account_name": instance.bank_account.account_name,
                "account_number": instance.bank_account.account_number,
            }

    def create(self, validated_data):
        if validated_data["country"] == "IN" or validated_data["country"] == "NG":
            ml4market = True
        else:
            ml4market = False

        company_instance = Company.objects.create(**validated_data, ML4_market=ml4market)

        return company_instance

    def update(self, instance, validated_data):

        if instance.country != validated_data["country"]:
            if "crop" in validated_data:
                validated_data.pop("crop")
            crops = (
                Crop.objects.filter(countryRelated__country=validated_data["country"])
                .exclude(name="Other")
                .values_list("id", flat=True)
            )
            if validated_data["country"] == "IN" or validated_data["country"] == "NG":
                validated_data["ML4_market"] = True
            else:
                validated_data["ML4_market"] = False

            # Updates company's cooling units to have all crops of the country active
            cooling_units = CoolingUnit.objects.filter(location__company=instance)

            # Get a default pricing *once*
            first_unit_pricing = CoolingUnitCrop.objects.filter(cooling_unit__in=cooling_units).first()
            pricing_instance = first_unit_pricing.pricing if first_unit_pricing else None

            for cu in cooling_units:
                # Disable all current crops from the cooling unit
                CoolingUnitCrop.objects.filter(cooling_unit=cu).exclude(
                    crop__name="Other"
                ).update(active=False)

                for crop in crops:
                    cu_crop = CoolingUnitCrop.objects.filter(crop_id=crop, cooling_unit=cu)
                    if cu_crop:
                        cu_crop.update(active=True)
                    elif pricing_instance:
                        new_pricing_instance = Pricing.objects.create(
                            pricing_type=pricing_instance.pricing_type,
                            fixed_rate=pricing_instance.fixed_rate,
                            daily_rate=pricing_instance.daily_rate,
                        )
                        CoolingUnitCrop.objects.create(
                            crop_id=crop,
                            cooling_unit=cu,
                            pricing=new_pricing_instance,
                            active=True,
                        )

        else:
            crops = validated_data.pop("crop")

        instance.crop.set(crops)

        data = self.context["request"].data
        required_fields = ["bank_name", "account_name", "account_number"]

        bank_account_id = instance.bank_account.id if instance.bank_account else None

        if all(field in data for field in required_fields):
            bank_account_data = {
                "bank_name": data["bank_name"],
                "account_name": data["account_name"],
                "account_number": data["account_number"],
            }

            try:
                # Try to get the existing bank account by ID
                bank_account = BankAccount.objects.get(id=bank_account_id)
                # Update the bank account with new data
                for key, value in bank_account_data.items():
                    setattr(bank_account, key, value)
                bank_account.save()
            except BankAccount.DoesNotExist:
                # Create a new bank account if not found
                bank_account = BankAccount.objects.create(**bank_account_data)
                # Link the bank account to the instance
                instance.bank_account = bank_account

        return super().update(instance, validated_data)
