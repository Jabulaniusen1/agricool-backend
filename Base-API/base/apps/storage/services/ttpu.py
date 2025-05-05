import numpy as np
from django.utils import timezone

from ..models import CoolingUnitSpecifications, Crate, Produce


def _kinetic_constant(k0: float, Ea: float, R: float, T: float):
    """
    Compute the kinetic constant rate for the quality model.
    Args:
        - k0: commodity-dependent constant [1/s].
        - Ea: commodity-dependent activation energy constant [J/mol].
        - R: universal gas constant [-].
        - T: temperature [Kelvin].
    """

    return k0 * np.exp(-Ea / (R * (T + 273.15))) * 24 * 60 * 60


def initial_TTPU(
    T_room: float, initial_quality: float, SL_buffer: float, k0: float, Ea: float
) -> float:
    """
    Compute the initial "time to pick-up" for a certain commodity.
    Args:
        -crop_id: commodity id to read cmmodity specific paramters.
        -T_room: current temperature in the room [Celcius]. Last temperature value from the room.
        -initial_quality: quality derived from the answer to check-in question of number of days since harvest.
        -SL_buffer: Shelf-life buffer outside at T_out degrees [days]. Note that this must be the same as the one passed to the the Digital Twin.
    """

    # TODO Hardcoded the parameters here, but they should be moved into the database by changing the models and adding to the fixtures
    PARAMETERS = {
        "T_out": 30,
        "R": 8.31451,
    }

    R = PARAMETERS["R"]  # air gas constant
    T_out = PARAMETERS[
        "T_out"
    ]  # outside temperature (IF CHANGED IN THE APP MUST BE CHANGED IN THE JSON FILE TOO!)

    k_out = _kinetic_constant(
        k0, Ea, R, T_out
    )  # kinetic constant rate, outside conditions
    k_in = _kinetic_constant(
        k0, Ea, R, T_room
    )  # kinetic constant rate, inside conditions
    q_th = 20 * np.exp(k_out * SL_buffer)  # quality threshold inside
    ttpu = max(
        0, round(-np.log(q_th / initial_quality) / k_in, 2)
    )  # "time to pick-up" for the commodity to have SL_buffer days of shelf-life remaining

    return ttpu


def get_set_t(crate_id):
    # option 1: Average of set point values in last 6 hours, option 2: Average of values in last 6 hours
    # option 3: last set point value option 4: last value

    crate = Crate.objects.get(id=crate_id)

    cooling_unit = crate.cooling_unit

    results_from_last_6_hours = CoolingUnitSpecifications.objects.filter(
            cooling_unit=cooling_unit, specification_type="TEMPERATURE",
            datetime_stamp__gte = timezone.now() - timezone.timedelta(hours=6)
        )

    if results_from_last_6_hours:

        filtered = [float(i.set_point_value) for i in results_from_last_6_hours if i.set_point_value is not None]

        if filtered:
            return sum(filtered) / len(filtered)

        return sum ([float(i.value) for i in results_from_last_6_hours]) /  len(results_from_last_6_hours)

    if crate.cooling_unit.sensor and CoolingUnitSpecifications.objects.filter(
            cooling_unit=cooling_unit, specification_type="TEMPERATURE"
        ).latest("datetime_stamp").set_point_value:
        return CoolingUnitSpecifications.objects.filter(
            cooling_unit=cooling_unit, specification_type="TEMPERATURE"
        ).latest("datetime_stamp").set_point_value


    return CoolingUnitSpecifications.objects.filter(
                cooling_unit=cooling_unit, specification_type="TEMPERATURE"
            ).latest("datetime_stamp").value


def compute_initial_ttpu_checkin(produce_id, crate_id):

    # 1. Get current produce, crate, crop id
    produce = Produce.objects.get(id=produce_id)
    crate = Crate.objects.get(id=crate_id)
    k0 = produce.crop.dependent_constant
    Ea = produce.crop.activation_energy_constant

    # 2. if there is no temperature recorded, we cannot do a check-in. (we enforce temperature addition but we can never know)
    if not CoolingUnitSpecifications.objects.filter(
        cooling_unit=crate.cooling_unit, specification_type="TEMPERATURE"
    ):
        return None

    # 3. assigns Set_T to the last_temp and T_set parameter if cooling unit has an Ecozen Sensor, otherwise set the last manual temperature in the cold room
    last_temp = float ( get_set_t( crate_id ) )

    # 4. Parse the last temperature, add the initial quality and SL_buffer as a magic number
    initial_quality = produce.harvest_date
    SL_buffer = 0.5

    # 5. Compute the TTPU
    computed_initial_TTPU = initial_TTPU(last_temp, initial_quality, SL_buffer, k0, Ea)
    initial_quality /= 100
    # 6. Update the crates properties
    Crate.objects.filter(produce=produce).update(
        remaining_shelf_life=computed_initial_TTPU,
        modified_dt=timezone.now(),
        quality_dt=initial_quality,
    )

    return computed_initial_TTPU
