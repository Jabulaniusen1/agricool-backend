import datetime
import os
from typing import Union, Tuple, Dict

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
            user=os.environ.get("DB_USERNAME", "base"),
            password=os.environ.get("DB_PASSWORD", "base"),
            host=os.environ.get("DB_HOST", "db"),
            port=os.environ.get("DB_PORT", "5432"),
            database=os.environ.get("DB_NAME", "base"),
        )

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


class FarmerBaseSlicer(BaseSlicer):
    """Slicer class for Farmer metrics tables.

    Inherits from BaseSlicer.
    """

    def slice_table(
            self, farmer_id):
        """Get farmer basic information.

        Args:
            farmer_id: An intehger representing the farmer id

        Returns:
            A DataFrame containing the farmer data.
        """

        query = (
            """
            WITH user_details as (
                SELECT uf.id as farmer_id,
                       MAX(first_name) as first_name,
                       MAX(last_name) as last_name,
                       MAX(gender) as gender,
                       MAX(user_type) as user_type
                FROM user_farmer uf
                LEFT JOIN user_user uu on uu.id = uf.user_id
                LEFT JOIN user_farmersurvey ufs on ufs.farmer_id = uf.id
                GROUP BY uf.id)

            SELECT
                acm.survey_farmer AS farmer_id,
                MAX(first_name) as first_name,
                MAX(last_name) as last_name,
                MAX(gender) as gender,
                MAX(user_type) as user_type,
                CEIL(EXTRACT(EPOCH FROM AVG(acm.checkout_date - acm.checkin_date)) / 86400) AS avg_storage_days,
                SUM(acm.total_crate_cooling_fee) AS total_storage_cost
            FROM
                analytics_crate_movements acm
            LEFT JOIN user_details ud on acm.survey_farmer = ud.farmer_id
            WHERE
                acm.survey_farmer = %s AND
                acm.checkin_date BETWEEN '2022-10-01' AND CURRENT_DATE AND
                acm.cooling_unit_id BETWEEN 1 AND 100
            GROUP BY
                acm.survey_farmer

            """
        )

        df = pd.read_sql(
            query, self.conn, params=(farmer_id, )
        )

        return df


class FarmerSlicer(BaseSlicer):
    """Slicer class for Farmer metrics tables.

    Inherits from BaseSlicer.
    """

    def slice_table(
            self, farmer_id, unit_ids: list[int], date_range: pd.DatetimeIndex
    ) -> Tuple[Union[pd.DataFrame, int],Union[pd.DataFrame, int]]:
        """Slice farmer_metrics table by farmer_id, cooling unit IDs and a date range.

        Args:
            farmer_id: An intehger representing the farmer id
            unit_ids: A list of cooling unit IDs to slice by.
            date_range: A DatetimeIndex object defining the date range.

        Returns:
            A DataFrame containing the sliced data.
        """

        query = (
            "SELECT * FROM farmer_metrics "
            "WHERE farmer_id = %s AND cooling_unit_id IN %s AND date BETWEEN %s AND %s"
        )

        query_2 = (
            """
            WITH user_details as (
                SELECT uf.id as farmer_id,
                       MAX(first_name) as first_name,
                       MAX(last_name) as last_name,
                       MAX(gender) as gender,
                       MAX(user_type) as user_type
                FROM user_farmer uf
                LEFT JOIN user_user uu on uu.id = uf.user_id
                LEFT JOIN user_farmersurvey ufs on ufs.farmer_id = uf.id
                GROUP BY  uf.id)

                SELECT
                    acm.survey_farmer AS farmer_id,
                    MAX(first_name) as first_name,
                    MAX(last_name) as last_name,
                    MAX(gender) as gender,
                    MAX(user_type) as user_type
                FROM
                    analytics_crate_movements acm
                LEFT JOIN user_details ud on acm.survey_farmer = ud.farmer_id
                WHERE
                    farmer_id = %s AND
                    acm.checkin_date BETWEEN %s AND %s
                    AND cooling_unit_id in %s
                GROUP BY
                    acm.survey_farmer
            """
        )

        query_3 = """
                    SELECT id as unit_id,
                           name as unit_name
                    FROM storage_coolingunit scu
                    WHERE scu.id in %s
                  """


        df_1 = pd.read_sql(
            query, self.conn, params=(farmer_id, tuple(unit_ids), date_range[0], date_range[-1])
        )

        df_2 = pd.read_sql(
            query_2, self.conn, params=(farmer_id, date_range[0], date_range[-1], tuple(unit_ids))
        )

        room_names = pd.read_sql(query_3, self.conn, params=(tuple(unit_ids),))

        # Aggregation using pandas
        agg_dict = {
            "gender": "max",
            "room_crates_in": "sum",
            "room_ops_in": "sum",
            "room_kg_in": "sum",
            "room_crates_out": "sum",
            "room_ops_out": "sum",
            "room_kg_out": "sum",
            "check_in_crates_crop": self.sum_dicts,
            "check_in_kg_crop": self.sum_dicts,
            "check_out_crates_crop": self.sum_dicts,
            "check_out_kg_crop": self.sum_dicts,
        }

        group_list = ["farmer_id", "cooling_unit_id"]
        aggregated_df = df_1.groupby(group_list).agg(agg_dict).reset_index()

        relevant_cooling_units = aggregated_df['cooling_unit_id'].unique().tolist()
        mask = room_names['unit_id'].isin(relevant_cooling_units)
        room_names = room_names[mask]

        aggregated_df['unit_name'] = room_names['unit_name'].tolist()

        return df_2, aggregated_df

    @staticmethod
    def sum_dicts(series):
        """
        Aggregate dictionaries by summing the values of the same keys.

        Args:
            series (pd.Series): A series of dictionaries.

        Returns:
            dict: Aggregated dictionary.
        """
        aggregated_dict = {}
        for d in series:
            for key, value in d.items():
                if key in aggregated_dict:
                    aggregated_dict[key] += value
                else:
                    aggregated_dict[key] = value
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


class ImpactSlicer(BaseSlicer):
    def slice_table(
            self,
            farmer_id,
            cooling_unit_ids: list[int],
            start_date: datetime.date,
            end_date: datetime.date,
    ) -> Union[pd.DataFrame, Dict[int, pd.DataFrame]]:
        """
        Slices and aggregates data from impact metrics table for a given farmer and a list cooling unit ids over a date range.

        Args:
            farmer_id_2: Integer representing the Farmer ID.
            cooling_unit_ids: List of integers representing cooling unit IDs.
            start_date: Start date of the range.
            end_date: End date of the range.

        Returns:
            Pandas DataFrame containing aggregated data for the farmer

        Raises:
            ValueError: If start_date is after end_date.
        """

        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        query_1 = f"""
                SELECT
                    farmer_id,
                    crop_id,
                    MAX(crop_name) as crop_name,
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
                    AVG(monthly_kg_selling_price_evolution) as avg_monthly_kg_selling_price_evolution,
                    AVG(monthly_perc_unit_selling_price_evolution) as avg_monthly_perc_unit_selling_price_evolution,
                    AVG(monthly_farmer_revenue_evolution) as avg_monthly_farmer_revenue_evolution,
                    MAX(latest_survey_date) as latest_survey_date
                FROM impact_metrics
                WHERE farmer_id = %s
                AND cooling_unit_id in %s
                AND latest_survey_date BETWEEN %s AND %s
                GROUP BY farmer_id, crop_id
                """

        query_2 = f"""
                        SELECT
                            farmer_id,
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
                            AVG(monthly_kg_selling_price_evolution) as avg_monthly_kg_selling_price_evolution,
                            AVG(monthly_perc_unit_selling_price_evolution) as avg_monthly_perc_unit_selling_price_evolution,
                            AVG(monthly_farmer_revenue_evolution) as avg_monthly_farmer_revenue_evolution,
                            MAX(latest_survey_date) as latest_survey_date
                        FROM impact_metrics
                        WHERE farmer_id = %s
                        AND cooling_unit_id in %s
                        AND latest_survey_date BETWEEN %s AND %s
                        GROUP BY farmer_id
                        """
        # Farmer survey information CTE
        query_3 = f"""
                    WITH baseline_filled_survey_count AS (
                                    SELECT
                                        ufs.farmer_id AS farmer_id,
                                        COUNT(DISTINCT ufsc.crop_id) AS num_filled_baseline_surveys
                                    FROM
                                        user_farmersurvey ufs
                                    JOIN user_farmersurveycommodity ufsc ON ufs.id = ufsc.farmer_survey_id
                                    JOIN user_farmer uf on ufs.farmer_id = uf.id
                                    WHERE
                                        ufs.farmer_id = %s
                                    GROUP BY
                                        ufs.farmer_id
                                    ),
                        baseline_possible_survey_count AS (
                            WITH SurveyedCrops AS (
                                SELECT
                                    distinct ufsc.crop_id AS crop_id_survey_filled_in,
                                    ufs.farmer_id as farmer_id
                                FROM
                                    user_farmersurvey ufs
                                JOIN user_farmersurveycommodity ufsc ON ufs.id = ufsc.farmer_survey_id
                                JOIN user_farmer uf ON ufs.farmer_id = uf.id
                                WHERE
                                    ufs.farmer_id = %s
                            ),
                            CrateMovementCrops AS (
                                SELECT
                                    distinct crop_id,
                                    acm.checkin_farmer as farmer_id
                                FROM
                                    analytics_crate_movements acm
                                WHERE
                                    acm.checkin_farmer = %s
                            ),
                            CombiningCases as (
                            -- Finding crops only in surveyed crops (i.e. 0 checkins were done)
                            SELECT
                                sc.crop_id_survey_filled_in AS crop_id,
                                'surveyed crop with 0 check-ins' as reason,
                                sc.farmer_id as farmer_id
                            FROM
                                SurveyedCrops sc
                            LEFT JOIN
                                CrateMovementCrops cmc ON sc.crop_id_survey_filled_in = cmc.crop_id
                            WHERE
                                cmc.crop_id IS null
                            UNION
                            -- Finding crops in crate movements (i.e. 1 checkin done)
                            SELECT
                                cmc.crop_id AS crop_id,
                                'crop with check-in done' as reason,
                                cmc.farmer_id as farmer_id
                            FROM
                                CrateMovementCrops cmc
                            order by crop_id)
                            select farmer_id, COUNT(DISTINCT crop_id) AS num_of_possible_baseline_surveys
                            FROM CombiningCases
                            group by farmer_id
                        ),
                        post_checkout_filled_survey_count AS (
                            SELECT
                                acm.checkin_farmer AS farmer_id,
                                COUNT(DISTINCT oms.id) AS num_of_filled_postcheckout_surveys
                            FROM
                                operation_marketsurvey oms
                            JOIN
                                operation_marketsurvey_checkout omsc ON oms.id = omsc.marketsurvey_id
                            JOIN
                                analytics_crate_movements acm ON acm.checkout_id = omsc.checkout_id AND acm.crop_id = oms.crop_id
                            WHERE
                                date_filled_in >= '2024-01-01' AND acm.checkin_farmer = %s
                            GROUP BY
                                acm.checkin_farmer
                        ),
                        possible_post_checkout_survey_count AS (
                           SELECT
                                om.farmer_id AS farmer_id,
                                COUNT(DISTINCT om.id) AS num_of_possible_postcheckout_surveys,
                                COUNT(DISTINCT om.crop_id) AS distinct_crops
                            FROM
                                operation_marketsurveypreprocessing om
                            WHERE
                                om.modified_at >= '2024-01-01' AND om.farmer_id = %s
                            GROUP BY
                                om.farmer_id
                        ),
                        crops_missing_baseline_survey AS (
                        WITH SurveyedCrops AS (
                                    SELECT
                                        distinct ufsc.crop_id AS crop_id_survey_filled_in
                                    FROM
                                        user_farmersurvey ufs
                                    JOIN user_farmersurveycommodity ufsc ON ufs.id = ufsc.farmer_survey_id
                                    JOIN user_farmer uf ON ufs.farmer_id = uf.id
                                    WHERE
                                        ufs.farmer_id = %s
                                ),
                                CrateMovementCrops AS (
                                    SELECT DISTINCT
                                        crop_id,
                                        acm.checkin_farmer
                                    FROM
                                        analytics_crate_movements acm
                                    WHERE
                                        acm.checkin_farmer = %s
                                )
                                SELECT
                                    string_agg(cmc.crop_id::text, ',') AS crops_with_baseline_survey_to_be_completed,
                                    cmc.checkin_farmer as farmer_id
                                FROM
                                    CrateMovementCrops cmc
                                LEFT JOIN
                                    SurveyedCrops sc ON cmc.crop_id = sc.crop_id_survey_filled_in
                                WHERE
                                    sc.crop_id_survey_filled_in IS null
                                group by cmc.checkin_farmer
                        )
                        SELECT
                            COALESCE(bfs.farmer_id, bps.farmer_id, pcfsc.farmer_id, ppcs.farmer_id) AS farmer_id,
                            num_filled_baseline_surveys,
                            num_of_possible_baseline_surveys,
                            COALESCE(num_of_filled_postcheckout_surveys,0) AS num_of_filled_postcheckout_surveys,
                            num_of_possible_postcheckout_surveys,
                            crops_with_baseline_survey_to_be_completed
                        FROM
                            baseline_filled_survey_count bfs
                        FULL JOIN baseline_possible_survey_count bps ON bfs.farmer_id = bps.farmer_id
                        FULL JOIN post_checkout_filled_survey_count pcfsc ON bfs.farmer_id = pcfsc.farmer_id
                        FULL JOIN possible_post_checkout_survey_count ppcs ON bfs.farmer_id = ppcs.farmer_id
                        FULL JOIN crops_missing_baseline_survey cmbs ON bfs.farmer_id = cmbs.farmer_id
                    """

        data = pd.read_sql(
            query_1, self.conn, params=(int(farmer_id), tuple(cooling_unit_ids), start_date, end_date)
        )

        data_2 = pd.read_sql(
            query_2, self.conn, params=(int(farmer_id), tuple(cooling_unit_ids), start_date, end_date)
        )

        data_3 = pd.read_sql(
                    query_3, self.conn, params=(int(farmer_id), int(farmer_id), int(farmer_id), int(farmer_id), int(farmer_id), int(farmer_id), int(farmer_id))
                )

        if data.empty:
            zero_row_df = pd.DataFrame({col: [0] for col in data.columns})

            # Append zero_row_df to existing_df
            data = data.append(zero_row_df, ignore_index=True)

        if data_2.empty:
            zero_row_df = pd.DataFrame({col: [0] for col in data_2.columns})

            # Append zero_row_df to existing_df
            data_2 = data_2.append(zero_row_df, ignore_index=True)

        if data_3.empty:
            zero_row_df = pd.DataFrame({col: [0] for col in data_3.columns})

            # Append zero_row_df to existing_df
            data_3 = data_3.append(zero_row_df, ignore_index=True)

        top_5_revenue = data.sort_values(by="avg_monthly_perc_revenue_increase_evolution", ascending=False).head(5)
        top_5_foodloss = data.sort_values(by="avg_monthly_perc_foodloss_evolution", ascending=False).head(5)

        # Convert the new DataFrames to dictionaries
        top_5_revenue_dict = top_5_revenue.to_dict(orient="records")
        top_5_foodloss_dict = top_5_foodloss.to_dict(orient="records")

        final_results = {
            'Aggregated': data_2.to_dict(orient="records"),
            'Surveys': data_3.to_dict(orient="records"),
            'Top 5 Revenue Evolution': top_5_revenue_dict,
            'Top 5 Food Loss Evolution': top_5_foodloss_dict
        }

        return final_results
