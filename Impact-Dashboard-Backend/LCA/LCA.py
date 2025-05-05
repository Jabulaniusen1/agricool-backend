import configparser
import os
from itertools import permutations


class CoolingUnitData:
    """
    A class with a dictionary storing the crate/ cooling unit data needed for an LCA computation
    """

    def __init__(self, data: dict):
        self.data = data


class SolarPanel:
    """Represents solar panels used in the cold-room of the LCA program."""

    def __init__(
        self,
        type_of_panels: str,
        number_of_panels: int,
        size: float,
        power: float,
        lifetime: int,
        daily_sunshine_hours: float,
        weight: float,
    ):
        self.type_of_panels = type_of_panels
        self.number_of_panels = number_of_panels
        self.size = size
        self.power = power
        self.lifetime = lifetime
        self.daily_sunshine_hours = daily_sunshine_hours

        assert self.daily_sunshine_hours is not None and self.power is not None

        self.daily_wattage = self.daily_sunshine_hours * self.power * 0.75
        self.weight = weight


class Crop:
    """Manages information about a specific crop in the LCA program."""

    def __init__(
        self,
        name: str,
        crop_id: int,
        total_heat_removed: float,
        electricity_cooling: float,
        weight: float,
        time_storage: float,
        sect_storage_cooldown: float,
        ec_fruit: float,
        cp_fruit: float,
        num_crates: int,
    ):
        self.name = name
        self.crop_id = crop_id
        self.total_heat_removed = total_heat_removed
        self.electricity_cooling = electricity_cooling
        self.weight = weight
        self.num_crates = num_crates
        self.time_storage = time_storage
        self.SECT_storage_cooldown = sect_storage_cooldown
        self.EC_fruit = ec_fruit
        self.CP_fruit = cp_fruit


class ThermalStorage:
    """Handles thermal storage details for the LCA program."""

    def __init__(
        self,
        type_of_storage: str,
        wax_weight_per_day: float,
        ice_weight_per_day: float,
        total_heat_icepack: float,
    ):
        self.type_of_storage = type_of_storage
        self.wax_weight_per_day = wax_weight_per_day
        self.ice_weight_per_day = ice_weight_per_day
        self.total_heat_icepack = total_heat_icepack


class Battery:
    """Encapsulates the details of the batteries used in the LCA program."""

    def __init__(
        self,
        type_of_battery: str,
        number_of_batteries: int,
        size_per_unit: float,
        storage_capacity_per_unit: float,
        max_charging_current: float,
        energy_storage_peak: float,
        weight_per_unit: float,
        total_heat_removed: float,
    ):
        self.type_of_battery = type_of_battery
        self.number_of_batteries = number_of_batteries
        self.size_per_unit = size_per_unit
        self.storage_capacity_per_unit = storage_capacity_per_unit
        self.max_charging_current = max_charging_current
        self.energy_storage_peak = energy_storage_peak
        self.weight_per_unit = weight_per_unit
        self.total_heat_removed = total_heat_removed


class RoomStructure:
    """Represents the physical structure and dimensions of the cold room."""

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        total_weight: float,
        insulator: int,
    ):
        self.length = length
        self.width = width
        self.height = height

        assert (
            self.length is not None
            and self.width is not None
            and self.height is not None
        )  # Ensure the l x w x h
        # are not Nonetypes

        self.weight = self.length * self.width * self.height * 66.7
        self.total_weight = total_weight
        self.insulator = insulator


class RoomStorageManagement:
    """Manages storage-related parameters, particularly those related to crates and fruit storage."""

    def __init__(
        self,
        packaging_type: str,
        crate_length: float,
        crate_width: float,
        crate_height: float,
        crate_weight: float,
        crates_per_storage: int,
        weight_fruit_crate: float,
        fruit_weight: float,
    ):
        self.packaging_type = packaging_type
        self.crate_length = crate_length
        self.crate_width = crate_width
        self.crate_height = crate_height
        self.crate_weight = crate_weight
        self.crates_per_storage = crates_per_storage
        self.weight_fruit_crate = weight_fruit_crate
        self.fruit_weight = fruit_weight


class RoomThermalProperties:
    """Concerned with thermal properties and calculations."""

    def __init__(
        self,
        Cp_water: float,
        T_amb_storage: float,
        Tf_storage_cooldown: float,
        Ti_storage: float,
        T_storage_maintain: float,
        T_room: float,
        EC_iceblock: float,
        total_heat: float,
    ):
        self.Cp_water = Cp_water
        self.T_amb_storage = T_amb_storage
        self.Tf_storage_cooldown = Tf_storage_cooldown
        self.Ti_storage = Ti_storage
        self.T_storage_maintain = T_storage_maintain
        self.T_room = T_room
        self.EC_iceblock = EC_iceblock
        self.total_heat = total_heat


class RoomElectricityManagement:
    """Focuses on electricity and power usage."""

    def __init__(
        self,
        electricity_cooling_fruit: float,
        electricity_charging_battery: float,
        electricity_iceblock_produced: float,
        power_maintain_cooling: float,
        electricity_maintain_cooling: float,
        daily_wattage: float,
    ):
        self.electricity_cooling_fruit = electricity_cooling_fruit
        self.electricity_charging_battery = electricity_charging_battery
        self.electricity_iceblock_produced = electricity_iceblock_produced
        self.power_maintain_cooling = power_maintain_cooling
        self.electricity_maintain_cooling = electricity_maintain_cooling
        self.daily_wattage = daily_wattage


class RoomRefrigerationSystem:
    """Manages refrigeration-related parameters."""

    def __init__(
        self,
        refrigerant_type: str,
        amount_refrigerant: float,
        refrigerant_cooling: float,
    ):
        self.refrigerant_type = refrigerant_type
        self.amount_refrigerant = amount_refrigerant
        self.refrigerant_cooling = refrigerant_cooling


class RoomFoodLossAndEnvironment:
    """Handles parameters related to food loss and environmental impact."""

    def __init__(
        self,
        food_loss_cold_room: float,
        food_loss_ambient: float,
        share_landfill_operator: float,
    ):
        self.food_loss_cold_room = food_loss_cold_room
        self.food_loss_ambient = food_loss_ambient
        self.share_landfill_operator = share_landfill_operator


class RoomTimeManagement:
    """Manages time-related parameters."""

    def __init__(self, time_storage: float):
        self.time_storage = time_storage


class ComponentConfigurator:
    @staticmethod
    def get_value(dfs, component, attribute, default):
        if attribute in ["crate_length", "crate_width", "crate_height"]:
            return (
                (dfs[component][attribute].iloc[0] / 100)
                if dfs[component].get(attribute) is not None
                else default
            )
        else:
            return (
                dfs[component][attribute].iloc[0]
                if dfs[component].get(attribute) is not None
                and dfs[component][attribute].iloc[0] is not None
                else default
            )

    @staticmethod
    def get_crop(dfs, idx, default):
        return (
            dfs["crop"]["crop_name"].iloc[idx]
            if dfs["crop"].get("crop_name") is not None
            and dfs["crop"]["crop_name"].iloc[idx] is not None
            else default
        )

    @staticmethod
    def get_crate(dfs, idx, default):
        return (
            dfs["crop"]["kg_checkin"].iloc[idx]
            if dfs["crop"].get("kg_checkin") is not None
            and dfs["crop"]["kg_checkin"].iloc[idx] is not None
            else default
        )

    @staticmethod
    def get_heat_capacity(name, default):
        config = configparser.RawConfigParser()
        config.optionxform = lambda option: option
        base_path = os.getcwd()
        print(base_path)
        config.read(f"{base_path}/heat_capacity.ini")
        heat_capacities = dict(config.items("crops"))

        try:
            heat_capacity = (
                float(heat_capacities[name])
                if heat_capacities[name] != "unk"
                else default
            )
        except KeyError:
            heat_capacity = default

        return heat_capacity

    @staticmethod
    def determine_energy_source(
        energy_source,
        percent_solar,
        percent_biomass,
        percent_grid,
        percent_diesel,
        POWER_SOURCES,
    ):
        # Direct mapping for "pv panels"
        if energy_source == "pv panels":
            return "solar"

        # For the "hybrid" energy source, we construct and check permutations
        if energy_source == "hybrid":
            components = []
            if percent_solar > 0:
                components.append("solar")
            if percent_biomass > 0:
                components.append("biomass")
            if percent_grid > 0:
                components.append("grid")
            if percent_diesel > 0:
                components.append("generator")  # Assuming 'generator' represents diesel

            for combo in permutations(components, len(components)):
                potential_key = "-".join(combo)
                if potential_key in POWER_SOURCES:
                    return potential_key

        # Default to "solar" if no matching key is found
        return "solar"

    @staticmethod
    def configure_solar_panel(dfs):
        return SolarPanel(
            type_of_panels=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "pv_panel_type", "Solar Panels (Mono-SI)"
            ),
            number_of_panels=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "pv_panel_count", 5
            ),
            power=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "pv_panel_max_power", 5.5
            ),
            lifetime=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "lifetime", 25
            ),
            daily_sunshine_hours=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "daily_sunshine_hours", 6
            ),
            weight=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "pv_panel_weight", 200
            ),
            size=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "pv_panel_size", 16000
            ),
        )

    @staticmethod
    def configure_crop(dfs, crop_idx):
        name = ComponentConfigurator.get_crop(dfs, crop_idx, "Tomato")
        return Crop(
            name=name,
            crop_id=ComponentConfigurator.get_value(dfs, "crop", "crop_id", 5),
            total_heat_removed=ComponentConfigurator.get_value(
                dfs, "crop", "total_heat_removed", 0
            ),
            electricity_cooling=ComponentConfigurator.get_value(
                dfs, "crop", "electricity_cooling", 0
            ),
            weight=ComponentConfigurator.get_value(dfs, "crop", "kg_checkin", 1.96),
            num_crates=ComponentConfigurator.get_value(dfs, "crop", "num_crates", 1),
            time_storage=ComponentConfigurator.get_value(
                dfs, "crop", "time_storage", 1
            ),
            sect_storage_cooldown=ComponentConfigurator.get_value(
                dfs, "crop", "sect_storage_cooldown", 0.96
            ),
            cp_fruit=ComponentConfigurator.get_heat_capacity(name=name, default=3.77),
            ec_fruit=ComponentConfigurator.get_value(dfs, "crop", "ec_fruit", 0),
        )

    @staticmethod
    def configure_thermal_storage(dfs):
        return ThermalStorage(
            type_of_storage=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "thermal_storage_method", "ice"
            ),
            wax_weight_per_day=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "wax_weight_per_day", 100
            ),
            ice_weight_per_day=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "ice_weight_per_day", 100
            ),
            total_heat_icepack=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "total_heat_icepack", 0
            ),
        )

    @staticmethod
    def configure_battery(dfs):
        return Battery(
            type_of_battery=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_type", "Lithium"
            ),
            number_of_batteries=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_count", 1
            ),
            size_per_unit=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_size", 0.01
            ),
            storage_capacity_per_unit=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_capacity", 100
            ),
            max_charging_current=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_max_current", 10
            ),
            energy_storage_peak=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_peak_energy_storage", 15
            ),
            weight_per_unit=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "battery_weight", 11.1
            ),
            total_heat_removed=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "total_heat_removed", 0
            ),
        )

    @staticmethod
    def configure_room_structure(dfs):
        return RoomStructure(
            length=ComponentConfigurator.get_value(dfs, "units", "room_length", 3),
            width=ComponentConfigurator.get_value(dfs, "units", "room_width", 3),
            height=ComponentConfigurator.get_value(dfs, "units", "room_height", 2),
            total_weight=ComponentConfigurator.get_value(
                dfs, "units", "room_weight", 0
            ),
            insulator=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "room_insulator", 5
            ),
        )

    @staticmethod
    def configure_room_storage_management(dfs, idx):
        return RoomStorageManagement(
            packaging_type=ComponentConfigurator.get_value(
                dfs, "coldroom", "packaging_type", "plastic"
            ),
            crate_length=ComponentConfigurator.get_value(
                dfs, "coldroom", "crate_length", 1.96
            ),
            crate_width=ComponentConfigurator.get_value(
                dfs, "coldroom", "crate_width", 1.96
            ),
            crate_height=ComponentConfigurator.get_value(
                dfs, "coldroom", "crate_height", 1.96
            ),
            crate_weight=ComponentConfigurator.get_value(
                dfs, "coldroom", "crate_weight", 1.96
            ),
            crates_per_storage=ComponentConfigurator.get_value(
                dfs, "crop", "num_crates", 37.5
            ),
            weight_fruit_crate=ComponentConfigurator.get_crate(dfs, idx, 25),
            fruit_weight=ComponentConfigurator.get_value(
                dfs, "coldroom", "fruit_weight", 0
            ),
        )

    @staticmethod
    def configure_room_thermal_properties(dfs):
        return RoomThermalProperties(
            Cp_water=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "Cp_water", 4.18
            ),
            T_amb_storage=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "t_amb_storage", 30
            ),
            Tf_storage_cooldown=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "tf_storage_cooldown", 5
            ),
            Ti_storage=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "ti_storage", 30
            ),
            T_storage_maintain=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "t_storage_maintain", 3.5
            ),
            T_room=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "t_room", 8
            ),
            EC_iceblock=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "EC_iceblock", 0
            ),
            total_heat=ComponentConfigurator.get_value(
                dfs, "room_sensor_temperature", "total_heat", 0
            ),
        )

    @staticmethod
    def configure_room_electricity_management(dfs):
        return RoomElectricityManagement(
            electricity_cooling_fruit=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "electricity_cooling_fruit", 0
            ),
            electricity_charging_battery=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "electricity_charging_battery", 0
            ),
            electricity_iceblock_produced=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "electricity_iceblock_produced", 0
            ),
            power_maintain_cooling=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "power_maintain_cooling", 0
            ),
            electricity_maintain_cooling=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "electricity_maintain_cooling", 0
            ),
            daily_wattage=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "daily_room_wattage", 10.65
            ),
        )

    @staticmethod
    def configure_room_refrigeration_system(dfs):
        return RoomRefrigerationSystem(
            refrigerant_type=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "refrigerant_type", "ice"
            ),
            amount_refrigerant=ComponentConfigurator.get_value(
                dfs, "coldroom", "amount_refrigerant", 0
            ),
            refrigerant_cooling=ComponentConfigurator.get_value(
                dfs, "coldroom", "refrigerant_cooling", 0
            ),
        )

    @staticmethod
    def configure_room_food_loss_and_environment(dfs):
        return RoomFoodLossAndEnvironment(
            food_loss_cold_room=ComponentConfigurator.get_value(
                dfs, "foodloss", "average_foodloss", 0.07
            ),
            food_loss_ambient=ComponentConfigurator.get_value(
                dfs, "foodloss", "food_loss_ambient", 0.5
            ),
            share_landfill_operator=ComponentConfigurator.get_value(
                dfs, "foodloss", "share_landfill_operator", 0
            ),
        )

    @staticmethod
    def configure_eco_invent(dfs):
        return EcoInvent(
            country=ComponentConfigurator.get_value(dfs, "coldroom", "country", "IN"),
            energy_source=ComponentConfigurator.get_value(
                dfs, "coldroom_power", "power_source", "PV Panels"
            ),
            percentages=dfs,
        )


class EcoInvent:
    """
    Represents the static ecoinvent parameters used for LCA computation.

    Attributes:
        country (str): The country for which the LCA is computed.
        energy_source (str): The type of energy source used.
        ipcc (float): IPCC parameter value.
        refrigerant (float): Refrigerant parameter value.
        biowaste (float): Biowaste parameter value.
        garden_waste (float): Garden waste parameter value.
    """

    def __init__(self, country, energy_source, percentages):
        self.country = country

        if self.country not in ["NG", "IN", "PH"]:
            self.country = "OT"

        self.percentages = percentages
        self.energy_source = energy_source.lower()
        configurator = ComponentConfigurator
        percent_solar = configurator.get_value(
            percentages, "coldroom_power", "power_source_pv_percent", 0.4
        )
        percent_biomass = configurator.get_value(
            percentages, "coldroom_power", "power_source_biomass_percent", 0.3
        )
        percent_grid = configurator.get_value(
            percentages, "coldroom_power", "power_source_grid_percent", 0.2
        )
        percent_diesel = configurator.get_value(
            percentages, "coldroom_power", "power_source_diesel_percent", 0.1
        )
        self.POWER_SOURCES = {
            "solar": {
                "ipcc": 0.075684744,
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "biomass": {
                "ipcc": 0.0428233784311287,
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "grid": {
                "NG": {
                    "ipcc": 0.595619099308445,
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": 1.43615373284955,
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": 0.975919279276615,
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "generator": {
                "ipcc": 0.02870450767,
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "grid-biomass": {
                "NG": {
                    "ipcc": (0.595619099308445 * percent_grid)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": (0.975919279276615 * percent_grid)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "grid-solar": {
                "NG": {
                    "ipcc": (0.595619099308445 * percent_grid)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": (0.975919279276615 * percent_grid)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "solar-biomass": {
                "ipcc": (0.0428233784311287 * percent_biomass)
                + (0.075684744 * percent_solar),
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "generator-grid": {
                "NG": {
                    "ipcc": ((0.103336227604507 / 3.6) * percent_diesel)
                    + (0.595619099308445 * percent_grid),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": ((0.103336227604507 / 3.6) * percent_diesel)
                    + (1.43615373284955 * percent_grid),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": ((0.103336227604507 / 3.6) * percent_diesel)
                    + (0.975919279276615 * percent_grid),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": ((0.103336227604507 / 3.6) * percent_diesel)
                    + (1.43615373284955 * percent_grid),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "generator-solar": {
                "ipcc": ((0.103336227604507 * percent_diesel) / 3.6)
                + (0.075684744 * percent_solar),
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "generator-biomass": {
                "ipcc": ((0.103336227604507 * percent_diesel) / 3.6)
                + (0.0428233784311287 * percent_biomass),
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "generator-grid-solar": {
                "NG": {
                    "ipcc": (0.595619099308445 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": (0.975919279276615 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "generator-grid-biomass": {
                "NG": {
                    "ipcc": (0.595619099308445 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": (0.975919279276615 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "grid-solar-biomass": {
                "NG": {
                    "ipcc": (0.595619099308445 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": (0.975919279276615 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.075684744 * percent_solar)
                    + (0.0428233784311287 * percent_biomass),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
            "solar-biomass-generator": {
                "ipcc": (0.103336227604507 * percent_diesel / 3.6)
                + (0.0428233784311287 * percent_biomass)
                + (0.075684744 * percent_solar),
                "refrigerant": 15.12399,
                "biowaste": 0.21268517,
                "garden_waste": 0.015667136,
            },
            "generator-grid-solar-biomass": {
                "NG": {
                    "ipcc": (0.595619099308445 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "IN": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "PH": {
                    "ipcc": (0.975919279276615 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
                "OT": {
                    "ipcc": (1.43615373284955 * percent_grid)
                    + (0.0428233784311287 * percent_biomass)
                    + ((0.103336227604507 / 3.6) * percent_diesel)
                    + (0.075684744 * percent_solar),
                    "refrigerant": 15.12399,
                    "biowaste": 0.21268517,
                    "garden_waste": 0.015667136,
                },
            },
        }

        self.energy_source = configurator.determine_energy_source(
            energy_source.lower(),
            percent_solar,
            percent_biomass,
            percent_grid,
            percent_diesel,
            self.POWER_SOURCES,
        )

        self.initialize_parameters()

    def initialize_parameters(self):
        """Initializes the environmental parameters based on energy source and country."""
        try:
            parameters = self.POWER_SOURCES[self.energy_source]

            # For energy sources under 'grid', country-specific values are used
            if self.energy_source in [
                "grid",
                "grid-biomass",
                "grid-solar",
                "generator-grid",
                "generator-grid-solar",
                "genenrator-grid-biomass",
                "grid-solar-biomass",
                "generator-grid-solar-biomass",
            ]:
                parameters = parameters[self.country]

            self.ipcc = parameters["ipcc"]
            self.refrigerant = parameters["refrigerant"]
            self.biowaste = parameters["biowaste"]
            self.garden_waste = parameters["garden_waste"]

        except KeyError:
            raise ValueError(
                f"Invalid country or energy source: {self.country}, {self.energy_source}"
            )

    def __str__(self):
        return f"EcoInvent(country={self.country}, energy_source={self.energy_source}, ipcc={self.ipcc}, refrigerant={self.refrigerant}, biowaste={self.biowaste}, garden_waste={self.garden_waste})"
