import datetime
import os
from typing import Any, Union

import pandas as pd
import psycopg2
from dotenv import load_dotenv


class BaseSlicer:
    """Base class for slicing tables from a database.

    Attributes:
        conn: Database connection object.
    """

    def __init__(self, db_params: dict):
        """Initialize the database connection using environment variables."""

        # Load environment variables from .env file
        load_dotenv()

        self.conn = psycopg2.connect(
            user=os.environ.get('DB_USERNAME', 'base'),
            password=os.environ.get('DB_PASSWORD', 'base'),
            host=os.environ.get('DB_HOST', 'db'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME', 'base'))

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


class CompanySlicer(BaseSlicer):
    """Slicer class for company-based tables.

    Inherits from BaseSlicer.
    """

    def slice_table(self, company_id: int) -> Union[pd.DataFrame, int]:
        """Slice a table by company ID.

        Args:
            company_id: The ID of the company to slice by.
        Returns:
            A DataFrame containing the sliced data.
        """
        query = f"SELECT * FROM company_metrics WHERE company_id = %s"
        df = pd.read_sql(query, self.conn, params=(company_id,))

        return df


class CoolingUnitSlicer(BaseSlicer):
    """Slicer class for cooling unit-based tables.

    Inherits from BaseSlicer.
    """

    def slice_table(
        self, unit_ids: list[int], date_range: pd.DatetimeIndex
    ) -> Union[pd.DataFrame, int]:
        """Slice a table by cooling unit IDs and a date range.

        Args:
            unit_ids: A list of cooling unit IDs to slice by.
            date_range: A DatetimeIndex object defining the date range.

        Returns:
            A DataFrame containing the sliced data.
        """

        query = (
            "SELECT * FROM cooling_unit_metrics "
            "WHERE cooling_unit_id IN %s AND date BETWEEN %s AND %s"
        )

        df = pd.read_sql(
            query, self.conn, params=(tuple(unit_ids), date_range[0], date_range[-1])
        )

        # Aggregation using pandas
        agg_dict = {
            "unit_name": "max",
            "is_unit_deleted": "mean",
            "state": "max",
            "cool_unit_type": "max",
            "cap_tons": "mean",
            "cap_num_crates": "mean",
            "company_id": "max",
            "comp_name": "max",
            "comp_pricing": "max",
            "currency": "max",
            "room_op": "mean",
            "room_op_fem": "mean",
            "room_op_ma": "mean",
            "room_op_ot": "mean",
            "room_beneficiaries": "sum",  # TODO Remove redundant aggregation
            "room_beneficiaries_fem": "sum",
            "room_beneficiaries_ma": "sum",
            "room_active_user_ids": self.distinct_list,
            "room_active_users": "sum",  # This is overestimating as user ids are repeated over the days
            "room_active_fem": self.distinct_list,
            "room_active_ma": self.distinct_list,
            "room_active_ot": self.distinct_list,
            "room_crates_in": "sum",
            "room_ops_in": "sum",
            "room_kg_in": "sum",
            "room_crates_out": "sum",
            "room_ops_out": "sum",
            "room_kg_out": "sum",
            "average_room_occupancy": "mean",
            "room_revenue": "sum",
            "room_revenue_usd": "sum",
            "check_in_crates_crop": self.sum_dicts,
            "check_in_kg_crop": self.sum_dicts,
            "check_out_crates_crop": self.sum_dicts,
            "check_out_kg_crop": self.sum_dicts,
            "tot_co2": "sum",
            "co2_crops": self.sum_co2_dicts_cooling_unit,
        }

        aggregated_df = df.groupby("cooling_unit_id").agg(agg_dict).reset_index()
        aggregated_df["room_active_users"] = aggregated_df[
            "room_active_user_ids"
        ].apply(len)
        aggregated_df["room_active_ma"] = aggregated_df["room_active_ma"].apply(len)
        aggregated_df["room_active_fem"] = aggregated_df["room_active_fem"].apply(len)
        aggregated_df["room_active_ot"] = aggregated_df["room_active_ot"].apply(len)

        # Calculate the room beneficiaries
        aggregated_df["room_beneficiaries"] = aggregated_df.apply(
            self.calculate_beneficiaries, axis=1
        )
        aggregated_df["room_beneficiaries_ma"] = aggregated_df.apply(
            lambda row: self.calculate_beneficiaries_gender(row, "male"), axis=1
        )
        aggregated_df["room_beneficiaries_fem"] = aggregated_df.apply(
            lambda row: self.calculate_beneficiaries_gender(row, "female"), axis=1
        )

        return aggregated_df

    def sum_dicts(self, series):
        """
        Aggregate dictionaries by summing the values of the same keys.

        Args:
            series (pd.Series): A series of dictionaries.

        Returns:
            dict: Aggregated dictionary.
        """
        aggregated_dict = {}
        for d in series:
            if len(d) != 0:
                for key, value in d.items():
                    if key in aggregated_dict:
                        aggregated_dict[key] += value
                    else:
                        aggregated_dict[key] = value
        return aggregated_dict

    @staticmethod
    def sum_co2_dicts_cooling_unit(series):
        """
        Aggregate CO2 dictionaries by summing the values of the same keys.

        Args:
            series (pd.Series): A series of dictionaries.

        Returns:
            dict: Aggregated dictionary.
        """
        aggregated_dict = {}
        for d in series:
            # Skip the loop if the dictionary is empty
            if not d:
                continue

            for key, value in d.items():
                # Ensure that 'value' is a dictionary and 'difference' key exists
                if isinstance(value, dict) and "difference" in value:
                    if key in aggregated_dict:
                        aggregated_dict[key] += value["difference"]
                    else:
                        aggregated_dict[key] = value["difference"]

        return aggregated_dict

    @staticmethod
    def distinct_list(series):
        """
        Aggregate lists by concatenating them and then getting distinct elements.

        Args:
            series (pd.Series): A series of lists.

        Returns:
            list: A list containing distinct elements from all lists in the series.
        """
        combined_list = []
        for l in series:
            if isinstance(l, list):
                combined_list.extend(l)
        return list(set(combined_list))

    @staticmethod
    def calculate_beneficiaries(row):
        if row["currency"] == "NGN":
            return row["room_active_users"] * 4.7
        elif row["currency"] == "INR":
            return row["room_active_users"] * 4.4
        elif row["currency"] == "PHP":
            return row["room_active_users"] * 4.2
        else:  # Covers other cases
            return row["room_active_users"] * 3

    @staticmethod
    def calculate_beneficiaries_gender(row, gender):
        if gender == "female":
            if row["currency"] == "NGN":
                return row["room_beneficiaries"] * 0.495
            elif row["currency"] == "INR":
                return row["room_beneficiaries"] * 0.484
            elif row["currency"] == "PHP":
                return row["room_beneficiaries"] * 0.492
            else:  # Covers other cases
                return row["room_beneficiaries"] * 0.4975
        elif gender == "male":
            if row["currency"] == "NGN":
                return row["room_beneficiaries"] * 0.505
            elif row["currency"] == "INR":
                return row["room_beneficiaries"] * 0.516
            elif row["currency"] == "PHP":
                return row["room_beneficiaries"] * 0.508
            else:  # Covers other cases
                return row["room_beneficiaries"] * 0.5025


class ImpactSlicer(BaseSlicer):
    def slice_table(
        self,
        company_id: int,
        cooling_unit_ids: list[int],
        start_date: datetime.date,
        end_date: datetime.date,
        mode: str = "cooling_unit",
    ) -> tuple[
        dict[
            Union[int, str],
            Union[
                dict[str, Union[pd.DataFrame, Any]],
                dict[str, Union[pd.DataFrame, None]],
            ],
        ],
        Any,
    ]:
        """
        Slices and aggregates data from impact metrics table for a given company or cooling units over a date range.

        Args:
            company_id: Integer representing the company ID.
            cooling_unit_ids: List of integers representing cooling unit IDs.
            start_date: Start date of the range.
            end_date: End date of the range.
            mode: Mode of slicing - either "company" or "cooling_unit".

        Returns:
            Pandas DataFrame containing aggregated data if mode is 'company'.
            Dictionary of DataFrames keyed by cooling unit ID if mode is 'cooling_unit'.

        Raises:
            ValueError: If mode is not 'company' or 'cooling_unit', or if start_date is after end_date.
        """
        if mode not in ["company", "cooling_unit"]:
            raise ValueError("Mode must be 'company' or 'cooling_unit'")
        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        group_by_field = "company_id" if mode == "company" else "cooling_unit_id"

        query_1 = f"""
                SELECT
                    {group_by_field},
                    MAX(unit_name) as unit_name,
                    SUM(baseline_quantity_total_month) as baseline_quantity_total_month,
                    AVG(baseline_kg_selling_price_month) as avg_baseline_kg_selling_price_month,
                    SUM(baseline_kg_loss_month) as baseline_kg_loss_month,
                    SUM(baseline_kg_sold_month) as baseline_kg_sold_month,
                    COALESCE(SUM(baseline_kg_loss_month) / NULLIF(SUM(baseline_quantity_total_month), 0) * 100, 0) AS avg_baseline_perc_loss_month,
                    SUM(baseline_farmer_revenue_month) as avg_baseline_farmer_revenue_month,
                    AVG(monthly_kg_selling_price) as avg_monthly_kg_selling_price,
                    SUM(monthly_kg_checkin) as monthly_kg_checkin,
                    SUM(monthly_kg_loss) as monthly_kg_loss,
                    COALESCE(SUM(monthly_kg_loss) / NULLIF(SUM(monthly_kg_checkin), 0) * 100, 0) AS avg_monthly_perc_loss,
                    COALESCE((((SUM(monthly_kg_loss) / NULLIF(SUM(monthly_kg_checkin), 0)) - (SUM(baseline_kg_loss_month) / NULLIF(SUM(baseline_quantity_total_month), 0))) / NULLIF((SUM(baseline_kg_loss_month) / SUM(baseline_quantity_total_month)), 0)) * 100, 0) as avg_monthly_perc_foodloss_evolution,
                    SUM(monthly_farmer_revenue) as avg_monthly_farmer_revenue,
                    COALESCE((SUM(monthly_farmer_revenue) - SUM(baseline_farmer_revenue_month)) / NULLIF(SUM(baseline_farmer_revenue_month), 0) * 100, 0) as avg_monthly_perc_revenue_increase_evolution,
                    AVG(monthly_perc_farmer_revenue_evolution) as avg_monthly_perc_revenue_increase_evolution_2,
                    AVG(monthly_kg_selling_price_evolution) as avg_monthly_kg_selling_price_evolution,
                    AVG(monthly_perc_unit_selling_price_evolution) as avg_monthly_perc_unit_selling_price_evolution,
                    AVG(monthly_farmer_revenue_evolution) as avg_monthly_farmer_revenue_evolution,
                    MAX(latest_survey_date) as latest_survey_date,
                    COUNT(*) as num_post_harvest_surveys,
                    MAX(possible_post_checkout_survey_room) as possible_post_checkout_survey_room,
                    MAX(total_post_checkout_survey_unit) as total_post_checkout_survey_unit
                FROM impact_metrics
                WHERE {group_by_field} = %s
                    AND latest_survey_date BETWEEN %s AND %s
                GROUP BY {group_by_field}
                """

        query_2 = f"""
                    SELECT name from storage_coolingunit scu where scu.id = %s;
        """

        if mode == "company":
            query_3 = f"""
                        SELECT cooling_unit_id, company_id, co2_crops
                        FROM cooling_unit_metrics
                        WHERE company_id = %s AND date BETWEEN %s AND %s
                        """

            co2_impact_df = pd.read_sql(
                query_3, self.conn, params=(company_id, start_date, end_date)
            )

            agg_dict = {
                "co2_crops": self.sum_co2_dicts_impact,
                "cooling_unit_id": "max",
            }

            aggregated_df = (
                co2_impact_df.groupby("company_id").agg(agg_dict).reset_index()
            )
            aggregated_dict = aggregated_df.to_dict(orient="records")

            total_no_coldroom, total_coldroom = 0, 0

            try:
                total_no_coldroom = sum(
                    item["no-coldroom"]
                    for item in aggregated_dict[0]["co2_crops"].values()
                )
                total_coldroom = sum(
                    item["coldroom"]
                    for item in aggregated_dict[0]["co2_crops"].values()
                )

                # Create and return a new dictionary with the total sums
                total_dict = {"co2_from": total_no_coldroom, "co2_to": total_coldroom}
                aggregated_df.at[0, "co2_crops"] = total_dict
            except:
                # Create and return a new dictionary with the total sums
                total_dict = {"co2_from": total_no_coldroom, "co2_to": total_coldroom}
                aggregated_df.loc[len(aggregated_df)] = [company_id, total_dict, 0]

        else:
            placeholders = ", ".join(["%s"] * len(cooling_unit_ids))
            query_3 = (
                "SELECT cooling_unit_id, company_id, co2_crops "
                "FROM cooling_unit_metrics "
                "WHERE cooling_unit_id IN ({}) AND date BETWEEN %s AND %s"
            ).format(placeholders)

            params = tuple(cooling_unit_ids) + (start_date, end_date)

            co2_impact_df = pd.read_sql(query_3, self.conn, params=params)

            agg_dict = {"co2_crops": self.sum_co2_dicts_impact, "company_id": "max"}

            aggregated_df = (
                co2_impact_df.groupby("cooling_unit_id").agg(agg_dict).reset_index()
            )

            aggregated_df["co2_crops"] = aggregated_df["co2_crops"].apply(
                lambda x: {
                    "co2_from": sum(crop["no-coldroom"] for crop in x.values()),
                    "co2_to": sum(crop["coldroom"] for crop in x.values()),
                }
            )

        if mode == "company":
            return (
                pd.read_sql(
                    query_1, self.conn, params=(company_id, start_date, end_date)
                ),
                aggregated_df,
            )
        else:
            data = {}
            for cu_id in cooling_unit_ids:
                name_df = pd.read_sql(query_2, self.conn, params=(cu_id,))
                if not name_df.empty:
                    data[cu_id] = {
                        "name": name_df.iloc[0]["name"],
                        "data": pd.read_sql(
                            query_1, self.conn, params=(cu_id, start_date, end_date)
                        ),
                    }
                else:
                    # Query the database to get an empty DataFrame with the same structure
                    empty_df = pd.read_sql(
                        query_1, self.conn, params=(cu_id, start_date, end_date)
                    ).head(0)
                    data["empty"] = {"name": None, "data": empty_df}

            return data, aggregated_df

    @staticmethod
    def sum_co2_dicts_impact(series):
        """
        Aggregate CO2 dictionaries by summing the values of the same keys.

        Args:
            series (pd.Series): A series of dictionaries.

        Returns:
            dict: Aggregated dictionary.
        """
        aggregated_dict = {}
        total_dict = {}
        for d in series:
            # Skip the loop if the dictionary is empty
            if not d:
                continue

            for key, value in d.items():
                # Initialize the nested dictionary if the key does not exist
                if key not in aggregated_dict:
                    aggregated_dict[key] = {
                        "coldroom": 0,
                        "no-coldroom": 0,
                    }

                # Assuming value is a dictionary, add to the corresponding key
                if isinstance(value, dict):
                    for subkey in ["coldroom", "no-coldroom"]:
                        if subkey in value:
                            aggregated_dict[key][subkey] += value.get(subkey, 0)

        return aggregated_dict
