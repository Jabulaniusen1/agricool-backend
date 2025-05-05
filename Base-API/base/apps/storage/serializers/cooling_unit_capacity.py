from datetime import datetime

from rest_framework import serializers

from ..models import CoolingUnit, Crate


class CoolingUnitCapacitySerializer(serializers.ModelSerializer):
    used_capacity = serializers.SerializerMethodField()

    class Meta:
        model = CoolingUnit
        fields = ("id", "used_capacity")

    def get_used_capacity(self, instance):
        capacity = 1
        crates = Crate.objects.filter(cooling_unit__id=instance.id, weight__gt=0)

        crates_per_weekdays = [0] * 7
        for x in range(7):
            for crate in crates:
                if crate.produce:
                    checkin_date = crate.produce.checkin.movement.date
                    current_datetime = datetime.now().astimezone()
                    duration = (current_datetime - checkin_date).days
                    planned_days = crate.planned_days if crate.planned_days else 1
                    future_days = planned_days - duration
                    if future_days < 0:
                        future_days = 1
                    if future_days > x:
                        crates_per_weekdays[x] += 1

        weekdays_percentage = []

        capacity = (
            instance.capacity_in_number_crates
            if (instance.capacity_in_number_crates and instance.metric == "CRATES")
            else (
                instance.food_capacity_in_metric_tons
                if instance.food_capacity_in_metric_tons
                else instance.capacity_in_metric_tons
            )
        )
        cubic_meter_crate = (
            instance.crate_length * instance.crate_width * instance.crate_height
        ) / 1000000

        for crate in crates_per_weekdays:
            # the magic number of 0.68 is provided by BASE/EMPA as an estimation of how much of the room is used for storage
            dividor = (
                crate
                if (instance.capacity_in_number_crates and instance.metric == "CRATES")
                else crate * cubic_meter_crate * 0.68
            )
            if crate > 0:
                weekdays_percentage.append(dividor / capacity)
            else:
                weekdays_percentage.append(0)
        return weekdays_percentage
