import unittest

from core.compute_co2 import CO2Calculator


class TestCO2Calculator(unittest.TestCase):
    def setUp(self):
        # Setup common to all tests
        self.calculator_coldroom = CO2Calculator(mode="coldroom")
        self.calculator_no_coldroom = CO2Calculator(mode="no-coldroom")

    def test_initialize_coldroom_components(self):
        # Test if components are initialized correctly for coldroom mode
        self.calculator_coldroom._initialize_coldroom_components()

        self.assertIsNotNone(self.calculator_coldroom.solar_panel)
        self.assertIsNotNone(self.calculator_coldroom.crop)
        self.assertIsNotNone(self.calculator_coldroom.thermal_storage)
        self.assertIsNotNone(self.calculator_coldroom.battery)
        self.assertIsNotNone(self.calculator_coldroom.room_structure)
        self.assertIsNotNone(self.calculator_coldroom.room_storage_management)
        self.assertIsNotNone(self.calculator_coldroom.room_electricity_management)
        self.assertIsNotNone(self.calculator_coldroom.room_refrigeration_system)
        self.assertIsNotNone(self.calculator_coldroom.room_food_loss_and_environment)
        self.assertIsNotNone(self.calculator_coldroom.eco_invent)

    def test_compute_coldroom_parameters(self):
        # Test if coldroom parameters are computed correctly
        self.calculator_coldroom._initialize_coldroom_components()
        self.calculator_coldroom._compute_coldroom_parameters()

        # Assertions to check if calculations are as expected
        # Storing initial values for comparison
        initial_fruit_weight = (
            self.calculator_coldroom.room_storage_management.weight_fruit_crate
            - self.calculator_coldroom.crop.weight
        )
        initial_total_weight = (
            self.calculator_coldroom.room_storage_management.weight_fruit_crate
            * self.calculator_coldroom.room_storage_management.crates_per_storage
        ) + self.calculator_coldroom.room_structure.weight

        self.assertEqual(
            self.calculator_coldroom.room_structure.total_weight, initial_total_weight
        )

        # Asserting the correct calculation of EC parameters
        expected_ec_fruit = (
            (
                self.calculator_coldroom.room_storage_management.weight_fruit_crate
                * self.calculator_coldroom.room_storage_management.crates_per_storage
                * 30
            )
            * self.calculator_coldroom.crop.CP_fruit
            * (
                self.calculator_coldroom.room_thermal_properties.Ti_storage
                - self.calculator_coldroom.room_thermal_properties.Tf_storage_cooldown
            )
            / (self.calculator_coldroom.solar_panel.daily_wattage * 3600 * 30)
        )
        self.assertEqual(self.calculator_coldroom.crop.EC_fruit, expected_ec_fruit)

        expected_ec_iceblock = (
            (self.calculator_coldroom.thermal_storage.ice_weight_per_day * 30)
            * self.calculator_coldroom.room_thermal_properties.Cp_water
            * self.calculator_coldroom.room_thermal_properties.Ti_storage
            / (self.calculator_coldroom.solar_panel.daily_wattage * 3600 * 30)
        )
        self.assertEqual(
            self.calculator_coldroom.room_thermal_properties.EC_iceblock,
            expected_ec_iceblock,
        )

        # Asserting the correct calculation of total heat removed
        expected_total_heat_removed = (
            initial_fruit_weight
            * self.calculator_coldroom.room_storage_management.crates_per_storage
            * self.calculator_coldroom.crop.CP_fruit
            * (
                self.calculator_coldroom.room_thermal_properties.Ti_storage
                - self.calculator_coldroom.room_thermal_properties.Tf_storage_cooldown
            )
            / (
                initial_fruit_weight
                * self.calculator_coldroom.room_storage_management.crates_per_storage
            )
        )
        self.assertEqual(
            self.calculator_coldroom.crop.total_heat_removed,
            expected_total_heat_removed,
        )

        expected_battery_heat_removed = (
            self.calculator_coldroom.battery.number_of_batteries
            * self.calculator_coldroom.battery.energy_storage_peak
            * 3600
            * 24
            * 0.8
        ) / (
            initial_fruit_weight
            * self.calculator_coldroom.room_storage_management.crates_per_storage
        )
        self.assertEqual(
            self.calculator_coldroom.battery.total_heat_removed,
            expected_battery_heat_removed,
        )

        expected_icepack_heat_removed = (
            self.calculator_coldroom.thermal_storage.ice_weight_per_day
            * self.calculator_coldroom.room_thermal_properties.Cp_water
            * self.calculator_coldroom.room_thermal_properties.Ti_storage
        ) / (
            initial_fruit_weight
            * self.calculator_coldroom.room_storage_management.crates_per_storage
        )
        self.assertEqual(
            self.calculator_coldroom.thermal_storage.total_heat_icepack,
            expected_icepack_heat_removed,
        )

        # Asserting the correct calculation of electricity & power cooling parameters
        expected_electricity_cooling_fruit = (
            self.calculator_coldroom.crop.total_heat_removed
            / (self.calculator_coldroom.crop.EC_fruit * 1000 * 3.6)
        )
        self.assertEqual(
            self.calculator_coldroom.room_electricity_management.electricity_cooling_fruit,
            expected_electricity_cooling_fruit,
        )

        expected_electricity_charging_battery = (
            self.calculator_coldroom.battery.total_heat_removed / (1000 * 0.9 * 3.6)
        )
        self.assertEqual(
            self.calculator_coldroom.room_electricity_management.electricity_charging_battery,
            expected_electricity_charging_battery,
        )

        expected_electricity_iceblock_produced = (
            self.calculator_coldroom.thermal_storage.total_heat_icepack
            / (
                self.calculator_coldroom.room_thermal_properties.EC_iceblock
                * 1000
                * 3.6
            )
        )
        self.assertEqual(
            self.calculator_coldroom.room_electricity_management.electricity_iceblock_produced,
            expected_electricity_iceblock_produced,
        )

        expected_power_maintain_cooling = (
            (
                0.0696 * self.calculator_coldroom.room_thermal_properties.T_amb_storage
                + 0.9691
            )
            * (
                self.calculator_coldroom.room_structure.length
                * self.calculator_coldroom.room_structure.width
                * self.calculator_coldroom.room_structure.height
            )
            / 40
        )
        self.assertEqual(
            self.calculator_coldroom.room_electricity_management.power_maintain_cooling,
            expected_power_maintain_cooling,
        )

        expected_electricity_maintain_cooling = (
            self.calculator_coldroom.room_electricity_management.power_maintain_cooling
            * (
                self.calculator_coldroom.crop.time_storage
                - self.calculator_coldroom.crop.SECT_storage_cooldown
            )
            * 24
            * 3600
        ) / (
            1000
            * (
                initial_fruit_weight
                * self.calculator_coldroom.room_storage_management.crates_per_storage
            )
            * 3.6
        )
        self.assertEqual(
            self.calculator_coldroom.room_electricity_management.electricity_maintain_cooling,
            expected_electricity_maintain_cooling,
        )

        # Asserting the correct calculation of refrigerant related parameters
        expected_amount_refrigerant = (
            0.38 / self.calculator_coldroom.room_storage_management.weight_fruit_crate
        ) * self.calculator_coldroom.room_storage_management.crates_per_storage
        self.assertEqual(
            self.calculator_coldroom.room_refrigeration_system.amount_refrigerant,
            expected_amount_refrigerant,
        )

        expected_refrigerant_cooling = (
            self.calculator_coldroom.room_refrigeration_system.amount_refrigerant
            * 0.1
            * self.calculator_coldroom.crop.time_storage
        ) / (
            365
            * initial_fruit_weight
            * self.calculator_coldroom.room_storage_management.crates_per_storage
        )
        self.assertEqual(
            self.calculator_coldroom.room_refrigeration_system.refrigerant_cooling,
            expected_refrigerant_cooling,
        )

        # Asserting the correct calculation of food-loss related parameters
        expected_food_loss_cold_room = (
            0.1
            * (
                self.calculator_coldroom.room_storage_management.weight_fruit_crate
                * self.calculator_coldroom.room_storage_management.crates_per_storage
            )
        ) / (
            self.calculator_coldroom.room_storage_management.weight_fruit_crate
            * self.calculator_coldroom.room_storage_management.crates_per_storage
        )
        self.assertEqual(
            self.calculator_coldroom.room_food_loss_and_environment.food_loss_cold_room,
            expected_food_loss_cold_room,
        )

        expected_share_landfill_operator = (
            0.01
            * (
                (
                    self.calculator_coldroom.room_storage_management.weight_fruit_crate
                    * self.calculator_coldroom.room_storage_management.crates_per_storage
                )
                - self.calculator_coldroom.room_food_loss_and_environment.food_loss_cold_room
            )
        ) / (
            30
            * 24
            * (
                self.calculator_coldroom.room_storage_management.weight_fruit_crate
                * self.calculator_coldroom.room_storage_management.crates_per_storage
            )
        )
        self.assertEqual(
            self.calculator_coldroom.room_food_loss_and_environment.share_landfill_operator,
            expected_share_landfill_operator,
        )

        # Finally, asserting the mode is set correctly
        self.assertEqual(self.calculator_coldroom.mode, "coldroom")

    def test_calculate_co2_contributions_coldroom(self):
        # Test CO2 contributions calculation for coldroom
        self.calculator_coldroom.mode = "coldroom"
        self.calculator_coldroom._initialize_coldroom_components()
        self.calculator_coldroom._compute_coldroom_parameters()

        self.assertEqual(len(self.calculator_coldroom.co2_contributors), 7)

        expected_values = [
            0.00416266092,
            0.06190981104294478,
            0.0047883369478527605,
            0.02299563472573546,
            3.2199435246659394e-05,
            0.021268517,
            2.1755075575308643e-07,
        ]

        for i, expected_value in enumerate(expected_values):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    self.calculator_coldroom.co2_contributors[i],
                    expected_value,
                    places=7,
                    msg=f"Value at index {i} is incorrect",
                )

    def test_initialize_no_coldroom_components(self):
        # Test if components are initialized correctly for no-coldroom mode
        self.calculator_coldroom._initialize_no_coldroom_components()

        self.calculator_no_coldroom._initialize_no_coldroom_components()
        self.assertIsNotNone(self.calculator_no_coldroom.room_storage_management)
        self.assertIsNotNone(self.calculator_no_coldroom.room_food_loss_and_environment)
        self.assertIsNotNone(self.calculator_no_coldroom.eco_invent)

    def test_compute_no_coldroom_parameters(self):
        # Test if no-coldroom parameters are computed correctly
        self.calculator_no_coldroom._initialize_no_coldroom_components()
        self.calculator_no_coldroom._compute_no_coldroom_parameters()

        # Assertions to check if calculations are as expected
        expected_food_loss_ambient = (
            0.5
            * (
                self.calculator_no_coldroom.room_storage_management.weight_fruit_crate
                * self.calculator_no_coldroom.room_storage_management.crates_per_storage
            )
        ) / (
            self.calculator_no_coldroom.room_storage_management.weight_fruit_crate
            * self.calculator_no_coldroom.room_storage_management.crates_per_storage
        )
        self.assertEqual(
            self.calculator_no_coldroom.room_food_loss_and_environment.food_loss_ambient,
            expected_food_loss_ambient,
        )

    def test_calculate_co2_contributions_no_coldroom(self):
        # Test CO2 contributions calculation for no-coldroom
        self.calculator_no_coldroom.mode = "no-coldroom"
        self.calculator_no_coldroom._initialize_no_coldroom_components()
        self.calculator_no_coldroom._compute_no_coldroom_parameters()

        self.assertEqual(len(self.calculator_no_coldroom.co2_contributors), 1)

        expected_value = 0.106342585

        self.assertEqual(
            self.calculator_no_coldroom.co2_contributors[0], expected_value
        )

    def test_compute_co2_emission(self):
        # Test the overall CO2 emission computation
        self.calculator_coldroom._initialize_coldroom_components()
        self.calculator_coldroom._compute_coldroom_parameters()
        coldroom_co2 = sum(self.calculator_coldroom.co2_contributors)

        self.calculator_no_coldroom._initialize_no_coldroom_components()
        self.calculator_no_coldroom._compute_no_coldroom_parameters()
        no_coldroom_co2 = sum(self.calculator_no_coldroom.co2_contributors)

        self.assertGreater(coldroom_co2, no_coldroom_co2)


if __name__ == "__main__":
    unittest.main()
