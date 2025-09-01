def get_weekly_capacity_forecast(cooling_unit):
    from base.apps.storage.models import Crate
    from datetime import datetime

    crates = Crate.objects.filter(cooling_unit=cooling_unit, weight__gt=0)
    crates_per_weekdays = [0] * 7

    for x in range(7):
        for crate in crates:
            if crate.produce:
                checkin_date = crate.produce.checkin.movement.date
                duration = (datetime.now().astimezone() - checkin_date).days
                planned_days = crate.planned_days or 1
                future_days = max(planned_days - duration, 1)

                if future_days > x:
                    crates_per_weekdays[x] += 1

    # compute percentages
    capacity = (
        cooling_unit.capacity_in_number_crates
        if (cooling_unit.capacity_in_number_crates and cooling_unit.metric == "CRATES")
        else cooling_unit.food_capacity_in_metric_tons or cooling_unit.capacity_in_metric_tons
    )
    cubic_meter_crate = (cooling_unit.crate_length * cooling_unit.crate_width * cooling_unit.crate_height) / 1_000_000

    percentages = []
    for count in crates_per_weekdays:
        div = (
            count
            if (cooling_unit.capacity_in_number_crates and cooling_unit.metric == "CRATES")
            else count * cubic_meter_crate * 0.68
        )
        percentages.append(div / capacity if count > 0 else 0)

    return percentages