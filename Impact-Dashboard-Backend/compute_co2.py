import argparse
import datetime as dt
import json
import os
import sys
from typing import Union

import pandas as pd
from dotenv import load_dotenv
from psycopg2.extensions import connection

from LCA.LCA import *
from utils import setup_connection


class CO2Calculator:
    def __init__(self, mode: str):
        """
        Initialize the CO2Calculator with a specific mode.
        :param mode: A string indicating the mode of operation, e.g., 'coldroom' or 'no-coldroom'.
        """
        self.eco_invent = None
        self.mode = mode
        self.co2_contributors: list[float] = []
        self.query_path = "LCA/sql_queries"

        # Run the SQL queries required for the LCA computation
        conn = self.make_conn_db()
        args = self.parse_arguments()
        self.args = args
        self.cooling_unit_data = self.extract_data(conn, args, dir=self.query_path)

        # Ambient food loss params
        self.foodloss_ambient = {"NG": 0.1, "IN": 0.05, "PH": 0.25, "OT": 0.3}

        # Data structure containing the CO2 results
        self.result = (None, None)

    @staticmethod
    def parse_arguments() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Run CO2 calculations for a single room in a day"
        )
        parser.add_argument(
            "--unit_id",
            type=int,
            help="pass in a single cooling unit id",
        )

        parser.add_argument(
            "--day",
            type=int,
            help="pass in the current day",
        )

        parser.add_argument(
            "--month",
            type=int,
            help="pass in the current month",
        )

        parser.add_argument(
            "--year",
            type=int,
            help="pass in the current year",
        )

        return parser.parse_args()

    @staticmethod
    def execute_query(
        conn: connection, query_path: str, params: dict[str, Union[int, str]]
    ) -> pd.DataFrame:
        """Given a connection object, the path towards an SQL file and a
        dictionary containing the optional parameter values, execute
        the query and return the result in a DataFrame"""
        cursor = conn.cursor()
        with open(query_path) as fp:
            try:
                cursor.execute(fp.read(), params)
                df = pd.DataFrame(cursor.fetchall())
                if not df.empty:
                    df.columns = [desc[0] for desc in cursor.description]
            finally:
                cursor.close()
        return df

    def extract_data(
        self,
        conn: connection,
        args: argparse.Namespace,
        dir: str = "sql_queries",
    ) -> Union[pd.DataFrame, pd.DataFrame]:
        dfs = {}
        for file_name in os.listdir(dir):
            query_name = file_name.replace(".sql", "")
            query_path = os.path.join(dir, file_name)
            dfs[query_name] = self.execute_query(conn, query_path, vars(args))

        return dfs

    @staticmethod
    def make_conn_db() -> connection:
        load_dotenv()
        return setup_connection()

    def compute_co2_emission(self) -> tuple[float, dict]:
        """
        Compute the CO2 emission based on the mode of operation.
        :return: Total CO2 contribution.
        """
        try:
            co2_dict = {
                crop: {"coldroom": 0, "no-coldroom": 0, "difference": 0}
                for crop in self.cooling_unit_data["crop"]["crop_name"]
                if crop != "Other"
            }
        except KeyError as e:
            print("There are no crops stored in this room currently")
            sys.exit(0)

        total_co2_saved = 0
        # Iterate over the list of crops and their respective crate weights
        for idx, crop in enumerate(self.cooling_unit_data["crop"]["crop_name"]):
            if crop == "Other":
                continue

            print(
                f"Computing the CO2 contribution for {crop} in {self.cooling_unit_data['coldroom']['name'].iloc[0]} for "
                f"{dt.datetime.today()}"
            )

            # Compute CO2 contribution with coldroom
            self._initialize_coldroom_components(self.cooling_unit_data, idx)
            self._compute_coldroom_parameters()
            coldroom_co2 = sum(self.co2_contributors)

            # Compute CO2 contribution without coldroom
            self.co2_contributors.clear()
            self._initialize_no_coldroom_components(self.cooling_unit_data, idx)
            self._compute_no_coldroom_parameters()
            no_coldroom_co2 = sum(self.co2_contributors)
            self.co2_contributors.clear()

            co2_dict[crop]["coldroom"] = coldroom_co2
            co2_dict[crop]["no-coldroom"] = no_coldroom_co2
            co2_dict[crop]["difference"] = no_coldroom_co2 - coldroom_co2
            total_co2_saved += co2_dict[crop]["difference"]

        return total_co2_saved, co2_dict

    def _initialize_coldroom_components(self, dfs, crop_idx):
        """
        Initializes components for the 'coldroom' mode.
        """

        self.solar_panel = ComponentConfigurator.configure_solar_panel(dfs)
        self.crop = ComponentConfigurator.configure_crop(dfs, crop_idx)
        self.thermal_storage = ComponentConfigurator.configure_thermal_storage(dfs)
        self.battery = ComponentConfigurator.configure_battery(dfs)
        self.room_structure = ComponentConfigurator.configure_room_structure(dfs)
        self.room_storage_management = (
            ComponentConfigurator.configure_room_storage_management(dfs, crop_idx)
        )
        self.room_thermal_properties = (
            ComponentConfigurator.configure_room_thermal_properties(dfs)
        )
        self.room_electricity_management = (
            ComponentConfigurator.configure_room_electricity_management(dfs)
        )
        self.room_refrigeration_system = (
            ComponentConfigurator.configure_room_refrigeration_system(dfs)
        )
        self.room_food_loss_and_environment = (
            ComponentConfigurator.configure_room_food_loss_and_environment(dfs)
        )
        self.eco_invent = ComponentConfigurator.configure_eco_invent(dfs)

    def _compute_coldroom_parameters(self):
        """
        Computes various parameters and CO2 contributions for the 'coldroom' mode.
        """
        # Compute the fruit weight and total room weight parameters
        weight_fruit_crate = self.room_storage_management.weight_fruit_crate or 0
        crates_per_storage = self.room_storage_management.crates_per_storage or 0
        daily_wattage = self.room_electricity_management.daily_wattage or 0
        ice_weight_per_day = self.thermal_storage.ice_weight_per_day or 0
        Cp_water = self.room_thermal_properties.Cp_water or 0
        Ti_storage = self.room_thermal_properties.Ti_storage or 0

        if weight_fruit_crate == 0 or crates_per_storage == 0 or daily_wattage == 0 or ice_weight_per_day == 0 or Cp_water == 0 or Ti_storage:
            return

        weight_of_all_crates = (weight_fruit_crate * crates_per_storage)
        iceblock = (
            ice_weight_per_day
            * Cp_water
            * Ti_storage
        )

        self.room_structure.total_weight = weight_of_all_crates + self.room_structure.weight

        # Compute the EC parameters
        self.crop.EC_fruit = (
            weight_of_all_crates
            * self.crop.CP_fruit
            * (
                self.room_thermal_properties.Ti_storage
                - self.room_thermal_properties.Tf_storage_cooldown
            )
            / (daily_wattage * 3600 * 1)
        )

        self.room_thermal_properties.EC_iceblock = (
            iceblock / (daily_wattage * 3600)
        )

        # self.crop.EC_fruit = 0.476010101  # TODO remove
        # self.crop.CP_fruit = 3.77
        # self.room_thermal_properties.EC_iceblock = 0.1407407407

        # Compute the total heat removed parameters
        self.crop.total_heat_removed = (
            weight_fruit_crate
            * crates_per_storage
            * self.crop.CP_fruit
            * (
                self.room_thermal_properties.Ti_storage
                - self.room_thermal_properties.Tf_storage_cooldown
            )
            / weight_of_all_crates
        )
        self.battery.total_heat_removed = (
            self.battery.number_of_batteries
            * self.battery.energy_storage_peak
            * 3600
            * 24
            * 0.8
        ) / weight_of_all_crates
        self.thermal_storage.total_heat_icepack = iceblock / weight_of_all_crates

        # Compute the electricity & power cooling parameters

        self.room_electricity_management.electricity_cooling_fruit = (
            self.crop.total_heat_removed / (self.crop.EC_fruit * 1000 * 3.6)
        )
        self.room_electricity_management.electricity_charging_battery = (
            self.battery.total_heat_removed / (1000 * 0.9 * 3.6)
        )
        self.room_electricity_management.electricity_iceblock_produced = (
            self.thermal_storage.total_heat_icepack
            / (self.room_thermal_properties.EC_iceblock * 1000 * 3.6)
        )
        self.room_electricity_management.power_maintain_cooling = (
            (0.0696 * self.room_thermal_properties.T_amb_storage + 0.9691)
            * (
                self.room_structure.length
                * self.room_structure.width
                * self.room_structure.height
            )
            / 40
        )

        #  SECT storage
        Y = (
            self.room_thermal_properties.T_room
            - self.room_thermal_properties.Tf_storage_cooldown
        ) / (
            self.room_thermal_properties.Ti_storage
            - self.room_thermal_properties.Tf_storage_cooldown
        )
        conn = self.make_conn_db()
        base_path = os.getcwd()
        sect_path = f"{base_path}/LCA/sect_query/sect.sql"
        sect_dict = vars(self.args)
        sect_dict.update({"Y": Y})
        sect_df = self.execute_query(conn, sect_path, vars(self.args))

        if not sect_df.empty:
            self.crop.SECT_storage_cooldown = (
                sect_df["days_to_sect"] if not None else 0.0417
            )
        else:
            self.crop.SECT_storage_cooldown = 0.0417

        self.room_electricity_management.electricity_maintain_cooling = (
            self.room_electricity_management.power_maintain_cooling
            * (self.crop.time_storage - self.crop.SECT_storage_cooldown)
            * 24
            * 3600
        ) / (
            1000 * weight_of_all_crates * 3.6
        )

        # Compute the refrigerant related parameters
        self.room_refrigeration_system.amount_refrigerant = 0.38 / weight_of_all_crates
        self.room_refrigeration_system.refrigerant_cooling = (
            self.room_refrigeration_system.amount_refrigerant
            * 0.1
            * self.crop.time_storage
        ) / (365 * weight_fruit_crate * crates_per_storage)

        # Compute the food-loss related parameters
        foodloss_df = self.cooling_unit_data["foodloss"]
        perc_foodloss_coldroom = (
            foodloss_df["average_foodloss"].iloc[0] if not foodloss_df.empty else 0.1
        )
        self.room_food_loss_and_environment.food_loss_cold_room = (
            perc_foodloss_coldroom
            * weight_of_all_crates
        ) / weight_of_all_crates

        perc_foodloss_ambient = (
            self.foodloss_ambient[self.eco_invent.country]
            if self.eco_invent.country in ["NG", "PH", "IN"]
            else self.foodloss_ambient["OT"]
        )
        perc_foodloss_ambient = 0.5  # TODO remove
        self.room_food_loss_and_environment.food_loss_ambient = (
            perc_foodloss_ambient
            * weight_of_all_crates
        ) / weight_of_all_crates
        self.room_food_loss_and_environment.share_landfill_operator = (
            0.01
            * (weight_of_all_crates - self.room_food_loss_and_environment.food_loss_cold_room)
        ) / (
            30 * 24 * weight_of_all_crates
        )

        self.mode = "coldroom"
        self._calculate_co2_contributions()

    def _calculate_co2_contributions(self):
        """
        Calculates the CO2 contributions for various components in 'coldroom' mode.
        """

        if self.mode == "coldroom":
            co2_cooling_fruit = (
                self.room_electricity_management.electricity_cooling_fruit
                * self.eco_invent.ipcc
            )
            co2_charging_battery = (
                self.room_electricity_management.electricity_charging_battery
                * self.eco_invent.ipcc
            )
            co2_iceblock_produced = (
                self.room_electricity_management.electricity_iceblock_produced
                * self.eco_invent.ipcc
            )
            co2_maintain_cooling = (
                self.room_electricity_management.electricity_maintain_cooling
                * self.eco_invent.ipcc
            )
            co2_refrigerant_cooling = (
                self.room_refrigeration_system.refrigerant_cooling
                * self.eco_invent.refrigerant
            )
            co2_food_loss_cold_room = (
                self.room_food_loss_and_environment.food_loss_cold_room
                * self.eco_invent.biowaste
            )
            co2_share_landfil_operator = (
                self.room_food_loss_and_environment.share_landfill_operator
                * self.eco_invent.garden_waste
            )

            self.co2_contributors.extend(
                [
                    co2_cooling_fruit,
                    co2_charging_battery,
                    co2_iceblock_produced,
                    co2_maintain_cooling,
                    co2_refrigerant_cooling,
                    co2_food_loss_cold_room,
                    co2_share_landfil_operator,
                ]
            )

        elif self.mode == "no-coldroom":
            co2_food_loss_ambient = (
                self.room_food_loss_and_environment.food_loss_ambient
                * self.eco_invent.biowaste
            )
            self.co2_contributors.extend([co2_food_loss_ambient])

    def _initialize_no_coldroom_components(self, dfs, crop_idx):
        """
        Initializes components for the 'no-coldroom' mode.
        """

        self.room_storage_management = (
            ComponentConfigurator.configure_room_storage_management(dfs, crop_idx)
        )
        self.room_food_loss_and_environment = (
            ComponentConfigurator.configure_room_food_loss_and_environment(dfs)
        )
        self.eco_invent = ComponentConfigurator.configure_eco_invent(dfs)

    def _compute_no_coldroom_parameters(self):
        """
        Computes various parameters and CO2 contributions for the 'no-coldroom' mode.
        """
        self.room_food_loss_and_environment.food_loss_ambient = (
            0.5
            * (
                self.room_storage_management.weight_fruit_crate
                * self.room_storage_management.crates_per_storage
            )
        ) / (
            self.room_storage_management.weight_fruit_crate
            * self.room_storage_management.crates_per_storage
        )

        self.mode = "no-coldroom"
        self._calculate_co2_contributions()


if __name__ == "__main__":
    lca = CO2Calculator(mode="coldroom")
    result = lca.compute_co2_emission()
    print(json.dumps(result))
