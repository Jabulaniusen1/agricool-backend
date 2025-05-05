import sys
sys.path.append("..")
sys.path.append("../air")

import datetime
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from unittest.mock import patch, Mock
from air.reporters.impact_reporter import ImpactReporter


class TestImpactReporter(unittest.TestCase):

    @patch('air.reporters.impact_reporter.DBConnector')
    def setUp(self, mock_connector):
        super().setUp()
        self.mock_connection = Mock()
        mock_connector.return_value.get_connection.return_value = self.mock_connection
        self.reporter = ImpactReporter()

    def test_calc_days_in_storage(self):
        check_in_dates = ['2023-09-13 08:00:00', '2023-09-13 10:08:46', '2023-09-13 19:37:09']
        check_out_dates = ['2023-09-13 09:37:46', '2023-09-15 17:17:38', '2023-09-14 10:38:23']


        df = pd.DataFrame({
            'Check-in Date': pd.to_datetime(check_in_dates),
            'Check-out Date': pd.to_datetime(check_out_dates)
        })
        self.reporter._calc_days_in_storage(df)

        # Same day checkout
        self.assertEqual(df['Days in Storage'].iloc[0], 0, 'Incorrect days in storage for same day checkout')

        # Post multi day checkout
        self.assertEqual(df['Days in Storage'].iloc[1], 2, 'Incorrect days in storage for future date checkout')

        # Next day, but less than 24 hours difference
        self.assertEqual(df['Days in Storage'].iloc[2], 1, 'Incorrect days in storage for next day checkout')

    def test_format_dt_column(self):
        dates = ['2023-09-13 08:22:34', datetime.datetime(2023, 9, 1, 18), pd.to_datetime(1490195805, unit='s')]
        df = pd.DataFrame({'Dates': pd.to_datetime(dates)})

        self.reporter._format_dt_column(df, 'Dates')

        self.assertEqual(df['Dates'].iloc[0], '2023-09-13 08:22:34', 'Incorrect format of date column')
        self.assertEqual(df['Dates'].iloc[1], '2023-09-01 18:00:00', 'Incorrect format of date column')
        self.assertEqual(df['Dates'].iloc[2], '2017-03-22 15:16:45', 'Incorrect format of date column')

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_room_df_without_cooling_unit_ids(self, mock_read_sql):
        room_df = pd.DataFrame({'name': ['A', 'B']})
        mock_read_sql.return_value = room_df

        returned_room_df = self.reporter._get_room_df(17364)

        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('sl.company_id = 17364', call_args[0])
        self.assertIn('select sc.*, sl.name as "Location Name", sl.state, sl.city, sl.zip_code',call_args[0])
        # self.assertIn('sl.latitude, sl.longitude, sl.deleted as deleted_location', call_args[0])

        self.assertNotIn('and sc.id in', call_args[0])

        expected_room_df = pd.DataFrame({'Cooling Unit Name': ['A', 'B']})
        assert_frame_equal(returned_room_df, expected_room_df)

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_room_df_with_cooling_unit_ids(self, mock_read_sql):
        room_df = pd.DataFrame({'name': ['A', 'B']})
        mock_read_sql.return_value = room_df

        self.reporter._get_room_df(84939, "1,2,3")

        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('sl.company_id = 84939', call_args[0])
        self.assertIn('and sc.id in (1,2,3)', call_args[0])

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_checkin_df_without_dates(self, mock_read_sql):
        room_df = pd.DataFrame({'Cooling Unit Name': ['A', 'B'],
                                'Location Name': ['L1', 'L2'],
                                'id': ['44', '75']
                                })
        checkin_df = pd.DataFrame({'Cooling Unit Id': ['44', '78'],
                                   'Check-in Code': ['36A', '94B']
                                   })
        mock_read_sql.return_value = checkin_df

        returned_checkin_df = self.reporter._get_checkin_df(1001, room_df)
        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('uo.company_id = 1001', call_args[0])

        select_elements = ['sc.id as "Crate Id",','sc.cooling_unit_id as "Cooling Unit Id",',
                           'om.code as "Check-in Code",', 'om.date as "Check-in Date",', 'om.id as movement_id,',
                           'om.operator_id,', 'uf.id as farmer_id,', 'uf.user_id as farmer_id_in_user_user,',
                           'sp.checkin_id,','sp.crop_id,', 'scrop.name as "Crop Name",','scp.checkout_id as check_out_id,',
                           'sc.remaining_shelf_life,','sc.modified_dt,',
                           'sc.price_per_crate_per_pricing_type as "Price per Crate",',
                           'sc.currency as "Currency",', 'sc.weight as "Weight"']
        for element in select_elements:
            self.assertIn(element, call_args[0])

        expected_checkin_df = pd.DataFrame({'Cooling Unit Id': ['44'],
                                            'Check-in Code': ['36A'],
                                            'Cooling Unit Name': ['A'],
                                            'Location Name': ['L1'],
                                            'id': ['44']
                                            })
        assert_frame_equal(returned_checkin_df, expected_checkin_df)

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_checkin_df_with_dates(self, mock_read_sql):
        room_df = pd.DataFrame({'Cooling Unit Name': ['A', 'B'],
                                'Location Name': ['L1', 'L2'],
                                'id': ['44', '75']
                                })
        checkin_df = pd.DataFrame({'Cooling Unit Id': ['44', '78']})
        mock_read_sql.return_value = checkin_df

        self.reporter._get_checkin_df(1001, room_df, '2023-09-11', '2023-09-20')
        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('uo.company_id = 1001', call_args[0])

        self.assertIn("""and CAST(om."date" AS DATE) >= '2023-09-11'""", call_args[0])
        self.assertIn("""and CAST(om."date" AS DATE) <= '2023-09-20'""", call_args[0])

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_cuser_df(self, mock_read_sql):
        cuser_df = pd.DataFrame({'First Name': ['A', 'B']})
        mock_read_sql.return_value = cuser_df

        returned_cuser_df = self.reporter._get_cuser_df(2002)

        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('company_id = 2002', call_args[0])

        select_elements = ['first_name as "First Name",', 'last_name as "Last Name",',
                           'phone as "Phone Number",', 'gender as "Gender",',
                           'parent_name as "Parent Name",', 'date_joined as "Date Joined",',
                           'uu.id as my_user_id, uu.is_active']
        for element in select_elements:
            self.assertIn(element, call_args[0])

        assert_frame_equal(returned_cuser_df, cuser_df)

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_checkout_df_without_dates(self, mock_read_sql):
        checkout_df = pd.DataFrame({'Check-out Code': ['36A', '94B']})
        mock_read_sql.return_value = checkout_df

        returned_checkout_df = self.reporter._get_checkout_df(3003)
        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('uo.company_id = 3003', call_args[0])

        select_elements = ['sc.id as "Crate Id",', 'scp.checkout_id as checkout_id,',
                           'om_cko.code as "Check-out Code",', 'om_cko.date as "Check-out Date",',
                           'sp.crop_id,', 'scrop.name as "Crop Name",',
                           'cko.cmp_total_amount as price_for_whole_checkout,', 'cko.currency as "Currency",',
                           'cko.payment_method as "Payment Type",', 'cko.cmp_total_cooling_fees_amount as old_price,',
                           'cko.discount_amount as price_discount,', 'om_cko.operator_id as checkout_operator,',
                           'sc.cooling_unit_id as "Cooling Unit Id",','sc.weight as "Weight", ',
                           'uf.id as farmer_id,', 'uf.user_id as farmer_id_in_user_user,',
                           'om_cin.date as "Check-in Date"']
        for element in select_elements:
            self.assertIn(element, call_args[0])

        assert_frame_equal(returned_checkout_df, checkout_df)

    @patch('air.reporters.impact_reporter.pd.read_sql')
    def test_get_checkout_df_with_dates(self, mock_read_sql):
        self.reporter._get_checkout_df(3003, '2023-09-11', '2023-09-20')
        mock_read_sql.assert_called_once()
        call_args, _kwd_args = mock_read_sql.call_args

        self.assertEqual(call_args[1], self.mock_connection)
        self.assertIn('uo.company_id = 3003', call_args[0])

        self.assertIn("""and CAST(om_cko."date" AS DATE) >= '2023-09-11'""", call_args[0])
        self.assertIn("""and CAST(om_cko."date" AS DATE) <= '2023-09-20'""", call_args[0])

    @patch('air.reporters.impact_reporter.ImpactReporter._get_cuser_df')
    @patch('air.reporters.impact_reporter.ImpactReporter._get_room_df')
    @patch('air.reporters.impact_reporter.ImpactReporter._get_checkin_df')
    def test_get_cooling_users_report(self, mock_get_checkin, mock_get_room, mock_get_cuser):
        # Setup mocked values
        cuser_data = [[1,True,'A','B','+12345678', 'F', 'Mom', datetime.datetime(2023, 9, 1, 18)],
                      [2,False,'C','D','+87654321', 'M', 'Dad', datetime.datetime(2023, 7, 1, 10)]
                      ]
        cuser_columns = ['my_user_id', 'is_active', 'First Name', 'Last Name', 'Phone Number', 'Gender', 'Parent Name', 'Date Joined']
        cuser_df = pd.DataFrame(cuser_data, columns=cuser_columns)

        # Multiple check in rows helps test the grouping as well as the latest check in date
        checkin_data = [[1, 100, datetime.datetime(2023, 9, 10, 18)],
                        [1, 101, datetime.datetime(2023, 9, 11, 18)],
                        [2, 102, datetime.datetime(2023, 8, 8, 8)]
                        ]
        checkin_columns = ['farmer_id_in_user_user', 'Crate Id', 'Check-in Date']
        checkin_df = pd.DataFrame(checkin_data, columns=checkin_columns)

        mock_get_cuser.return_value = cuser_df
        mock_get_checkin.return_value = checkin_df

        # Show inactive as well
        returned_cusers_df = self.reporter.get_cooling_users_report(1001, False)

        expected_data = [[1, 'C', 'D', '+87654321', 'M', 'Dad', '2023-07-01 10:00:00', 1, '2023-08-08 08:00:00'],
                         [2, 'A', 'B', '+12345678', 'F', 'Mom', '2023-09-01 18:00:00', 2, '2023-09-11 18:00:00']
                         ]
        expected_columns = ['#', 'First Name', 'Last Name', 'Phone Number', 'Gender',
                            'Parent Name', 'Date Joined',
                            'Total Number of Checked-in Crates', 'Latest Check In Date']
        expected_cusers_df = pd.DataFrame(expected_data, columns=expected_columns)
        expected_cusers_df.set_index('#', inplace=True)

        assert_frame_equal(returned_cusers_df, expected_cusers_df)

        # Show only active
        returned_cusers_df = self.reporter.get_cooling_users_report(1001, True)

        expected_data = [[1, 'A', 'B', '+12345678', 'F', 'Mom', '2023-09-01 18:00:00', 2, '2023-09-11 18:00:00']
                         ]
        expected_cusers_df = pd.DataFrame(expected_data, columns=expected_columns)
        expected_cusers_df.set_index('#', inplace=True)

        assert_frame_equal(returned_cusers_df, expected_cusers_df)

    @patch('air.reporters.impact_reporter.ImpactReporter._get_cuser_df')
    @patch('air.reporters.impact_reporter.ImpactReporter._get_room_df')
    @patch('air.reporters.impact_reporter.ImpactReporter._get_checkin_df')
    def test_get_usage_analysis_report(self, mock_get_checkin, mock_get_room, mock_get_cuser):
        # Set up mock values
        cuser_data = [[1,True,'A','B','+12345678', 'F'],
                      [2,False,'C','D','+87654321', 'M']
                      ]
        cuser_columns = ['my_user_id', 'is_active', 'First Name', 'Last Name', 'Phone Number', 'Gender']
        cuser_df = pd.DataFrame(cuser_data, columns=cuser_columns)

        checkin_data = [[1, 100, 'Code 1',datetime.datetime(2023, 9, 10, 18), 'Crop X', 20.0, 25.0, 'INR', 'CU 1', 'City A'],
                        [1, 101, 'Code 1',datetime.datetime(2023, 9, 10, 18), 'Crop X', 10.0, 25.0, 'INR', 'CU 1', 'City A'],
                        [2, 102, 'Code 2',datetime.datetime(2023, 8, 8, 8), 'Crop Z', 10.0, 25.0, 'INR', 'CU 2', 'City B'],
                        ]

        checkin_columns = ['farmer_id_in_user_user', 'Crate Id', 'Check-in Code', 'Check-in Date',
                           'Crop Name', 'Weight', 'Price per Crate', 'Currency', 'Cooling Unit Name',
                           'Location Name']
        checkin_df = pd.DataFrame(checkin_data, columns=checkin_columns)

        mock_get_cuser.return_value = cuser_df
        mock_get_checkin.return_value = checkin_df

        # Test return value
        returned_usage_df = self.reporter.get_usage_analysis_report(1001, '', None, None)

        expected_data = [[1, 102, 'Code 2', '2023-08-08 08:00:00', 'Crop Z', 10.0, 25.0, 'INR', 'C', 'D', '+87654321', 'M', 'CU 2', 'City B'],
                         [2, 100, 'Code 1', '2023-09-10 18:00:00', 'Crop X', 20.0, 25.0, 'INR', 'A', 'B', '+12345678', 'F', 'CU 1', 'City A'],
                         [3, 101, 'Code 1', '2023-09-10 18:00:00', 'Crop X', 10.0, 25.0, 'INR', 'A', 'B', '+12345678', 'F', 'CU 1', 'City A'],
                         ]
        expected_columns = ['#', 'Crate Id', 'Check-in Code', 'Check-in Date', 'Crop Name', 'Weight',
                         'Price per Crate', 'Currency', 'First Name', 'Last Name',
                         'Phone Number', 'Gender', 'Cooling Unit Name', 'Location Name']
        expected_cusers_df = pd.DataFrame(expected_data, columns=expected_columns)
        expected_cusers_df.set_index('#', inplace=True)

        assert_frame_equal(returned_usage_df, expected_cusers_df)

    @patch('air.reporters.impact_reporter.ImpactReporter._get_cuser_df')
    @patch('air.reporters.impact_reporter.ImpactReporter._get_room_df')
    @patch('air.reporters.impact_reporter.ImpactReporter._get_checkout_df')
    def test_get_revenue_analysis_report(self, mock_get_checkout, mock_get_room, mock_get_cuser):
        # Set up mock values
        cuser_data = [[1,True,'A','B','+12345678', 'F'],
                      [2,False,'C','D','+87654321', 'M']
                      ]
        cuser_columns = ['my_user_id', 'is_active', 'First Name', 'Last Name', 'Phone Number', 'Gender']
        cuser_df = pd.DataFrame(cuser_data, columns=cuser_columns)

        room_data = [['CU 1', 'City A', 1],
                     ['CU 2', 'City B', 2]]
        room_columns = ['Cooling Unit Name', 'Location Name', 'id']
        room_df = pd.DataFrame(room_data, columns=room_columns)

        # checkout_data = [[1, 100, 'Code 1',datetime.datetime(2023, 9, 10, 18), 'Crop X', 20.0, 25.0, 'INR', 'CU 1', 'City A'],
        #                 ]
        checkout_data = [[601, 'Code X', datetime.datetime(2023, 10, 4, 7), 2, 2, 0.0, 0.0, 50.0, datetime.datetime(2023, 9, 23, 16), 'Crop X', 20.0, 'INR', 'CASH'],
                         [602, 'Code X', datetime.datetime(2023, 10, 4, 7), 2, 2, 0.0, 0.0, 50.0, datetime.datetime(2023, 9, 24, 16), 'Crop X', 10.0, 'INR', 'CASH'],
                         [654, 'Code Y', datetime.datetime(2023, 10, 1, 7, 45), 1, 1, 40.0, 10.0, 50.0, datetime.datetime(2023, 9, 27, 17), 'Crop Y', 10.0, 'INR', 'CASH'],
                         [655, 'Code Y', datetime.datetime(2023, 10, 1, 7, 45), 1, 1, 40.0, 10.0, 50.0, datetime.datetime(2023, 9, 27, 17), 'Crop Y', 10.0, 'INR', 'CASH'],
                         ]
        checkout_columns = ['Crate Id', 'Check-out Code', 'Check-out Date', 'farmer_id_in_user_user', 'Cooling Unit Id',
                            'price_for_whole_checkout', 'price_discount', 'old_price', 'Check-in Date', 'Crop Name',
                            'Weight', 'Currency', 'Payment Type']
        checkout_df = pd.DataFrame(checkout_data, columns=checkout_columns)

        datetime.datetime(2023, 9, 23, 16)
        datetime.datetime(2023, 9, 24, 16)
        datetime.datetime(2023, 9, 27, 17)
        datetime.datetime(2023, 9, 27, 17)

        mock_get_cuser.return_value = cuser_df
        mock_get_room.return_value = room_df
        mock_get_checkout.return_value = checkout_df

        # Test return value
        returned_revenue_df = self.reporter.get_revenue_analysis_report(1001, '', None, None)

        expected_data = [[1, 654, 'Code Y', '2023-10-01 07:45:00', 'Crop Y', 10.0, 20.0, 'INR', 25.0, 5.0, 4,  'CASH', 'A', 'B', '+12345678', 'F', 'CU 1', 'City A'],
                         [2, 655, 'Code Y', '2023-10-01 07:45:00', 'Crop Y', 10.0, 20.0, 'INR', 25.0, 5.0, 4,  'CASH', 'A', 'B', '+12345678', 'F', 'CU 1', 'City A'],
                         [3, 601, 'Code X', '2023-10-04 07:00:00', 'Crop X', 20.0, 25.0, 'INR', 25.0, 0.0, 11, 'CASH', 'C', 'D', '+87654321', 'M', 'CU 2', 'City B'],
                         [4, 602, 'Code X', '2023-10-04 07:00:00', 'Crop X', 10.0, 25.0, 'INR', 25.0, 0.0, 10, 'CASH', 'C', 'D', '+87654321', 'M', 'CU 2', 'City B'],
                         ]
        expected_columns = ['#', 'Crate Id', 'Check-out Code', 'Check-out Date', 'Crop Name', 'Weight',
                         'Check-out Price per Crate', 'Currency',
                         'Check-out Price per Crate before Discount', 'Price Discount per Crate',
                         'Days in Storage', 'Payment Type', 'First Name', 'Last Name',
                         'Phone Number', 'Gender', 'Cooling Unit Name', 'Location Name']
        expected_cusers_df = pd.DataFrame(expected_data, columns=expected_columns)
        expected_cusers_df.set_index('#', inplace=True)

        assert_frame_equal(returned_revenue_df, expected_cusers_df)

if __name__ == '__main__':
    unittest.main()
