import argparse
import json
import os
import sys
import warnings
from datetime import date, datetime, timedelta
from subprocess import run
from typing import Union

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from psycopg2.extensions import connection

from dataProcessor import DataProcessor
from utils import load_json_variables, replace_nans, setup_connection

warnings.filterwarnings(action="ignore", category=FutureWarning)

# Config Items
# Data types for company view
COMPANY_CONVERSIONS = {
    0: {
        "convert": lambda x: datetime.strptime(x, "%Y-%m-%d").date()
        if isinstance(x, str)
        else x
    },
    1: {"convert": lambda x: int(x)},
    5: {"convert": lambda x: int(float(x))},
    6: {"convert": lambda x: int(float(x))},
    7: {"convert": lambda x: json.dumps(x)},
    8: {"convert": lambda x: int(float(x))},
    9: {"convert": lambda x: int(float(x))},
    10: {"convert": lambda x: int(float(x))},
    11: {"convert": lambda x: int(float(x))},
    12: {"convert": lambda x: str(x)},
    13: {"convert": lambda x: int(float(x))},
    14: {"convert": lambda x: int(float(x))},
    15: {"convert": lambda x: int(float(x))},
    16: {"convert": lambda x: int(float(x))},
    17: {"convert": lambda x: float(x)},
    18: {"convert": lambda x: float(x)},
    19: {"convert": lambda x: float(x)},
    20: {"convert": lambda x: int(float(x))},
    21: {"convert": lambda x: int(float(x))},
    22: {"convert": lambda x: int(float(x))},
    23: {"convert": lambda x: int(float(x))},
    24: {"convert": lambda x: int(float(x))},
    25: {"convert": lambda x: int(float(x))},
    26: {"convert": lambda x: int(float(x))},
    27: {"convert": lambda x: int(float(x))},
    28: {"convert": lambda x: int(float(x))},
    29: {"convert": lambda x: int(float(x))},
    30: {"convert": lambda x: int(float(x))},
    31: {"convert": lambda x: int(float(x))},
    32: {"convert": lambda x: int(float(x))},
    33: {"convert": lambda x: int(float(x))},
    34: {"convert": lambda x: float(x)},
    35: {"convert": lambda x: float(x)},
}

# Data types for cooling unit view
COOLING_UNIT_CONVERSIONS = {
    0: {
        "convert": lambda x: datetime.strptime(x, "%Y-%m-%d").date()
        if isinstance(x, str)
        else x
    },
    1: {
        "convert": lambda x: datetime.strptime(x, "%Y-%m-%d").date()
        if isinstance(x, str)
        else x
    },
    2: {"convert": lambda x: int(float(x))},
    7: {"convert": lambda x: int(float(x))},
    8: {"convert": lambda x: int(float(x))},
    9: {"convert": lambda x: int(float(x))},
    20: {"convert": lambda x: int(float(x))},
    21: {
        "convert": lambda x: []
        if (isinstance(x, int) and x == 0)
        or (isinstance(x, str) and (x == "[]" or x.isdigit()))
        else [int(float(i)) for i in x]
        if isinstance(x, list) and len(x) > 0
        else []
    },
    22: {
        "convert": lambda x: []
        if (isinstance(x, int) and x == 0)
        or (isinstance(x, str) and (x == "[]" or x.isdigit()))
        or (isinstance(x, list) and len(x) == 1 and x[0] is None)
        else [
            int(float(i))
            for i in x
            if i is not None and isinstance(i, (int, float, str))
        ]
        if isinstance(x, list) and len(x) > 0
        else []
    },
    23: {
        "convert": lambda x: []
        if (isinstance(x, int) and x == 0)
        or (isinstance(x, str) and (x == "[]" or x.isdigit()))
        or (isinstance(x, list) and len(x) == 1 and x[0] is None)
        else [
            int(float(i))
            for i in x
            if i is not None and isinstance(i, (int, float, str))
        ]
        if isinstance(x, list) and len(x) > 0
        else []
    },
    24: {
        "convert": lambda x: []
        if (isinstance(x, int) and x == 0)
        or (isinstance(x, str) and (x == "[]" or x.isdigit()))
        or (isinstance(x, list) and len(x) == 1 and x[0] is None)
        else [
            int(float(i))
            for i in x
            if i is not None and isinstance(i, (int, float, str))
        ]
        if isinstance(x, list) and len(x) > 0
        else []
    },
    31: {"convert": lambda x: float(x)},
    32: {"convert": lambda x: float(x)},
    33: {"convert": lambda x: float(x)},
    34: {"convert": lambda x: json.dumps(x)},
    35: {"convert": lambda x: json.dumps(x)},
    36: {"convert": lambda x: json.dumps(x)},
    37: {"convert": lambda x: json.dumps(x)},
    38: {"convert": lambda x: float(x)},
    39: {"convert": lambda x: json.dumps(x)},
}

for i in range(13, 17):
    COOLING_UNIT_CONVERSIONS[i] = {"convert": lambda x: int(float(x))}
for i in range(17, 20):
    COOLING_UNIT_CONVERSIONS[i] = {"convert": lambda x: float(x)}
for i in range(25, 31):
    COOLING_UNIT_CONVERSIONS[i] = {"convert": lambda x: int(float(x))}

CONVERSIONS = {"company": COMPANY_CONVERSIONS, "cooling_unit": COOLING_UNIT_CONVERSIONS}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run report for specific month and year"
    )
    parser.add_argument(
        "--view",
        type=str,
        default="cooling-units",
        help="the view you want to compute metrics for",
    )
    return parser.parse_args()


def execute_query(
    conn: connection, query_path: str, params: dict[str, Union[int, str]]
) -> pd.DataFrame:
    """Given a connection object, the path towards an SQL file and a
    dictionary containing the optional parameter values, execute
    the query and return the result in a DataFrame"""
    cursor = conn.cursor()
    with open(query_path) as fp:
        try:
            # print("Executing query:", query_path)
            # print("Query parameters:", params)
            cursor.execute(fp.read(), params)
            df = pd.DataFrame(cursor.fetchall())
            if not df.empty:
                df.columns = [desc[0] for desc in cursor.description]
        finally:
            cursor.close()
    return df


def additional_processing(dfs: dict[str, pd.DataFrame], args: dict[str, int]) -> None:
    # Define data processor object
    data_processor = DataProcessor()

    if args["view"] == "aggregated-comparison":
        crate_movements = dfs["crate_movements_day"]
        crate_movements["checkout_month"] = pd.to_datetime(
            crate_movements["checkout_date"]
        ).dt.month
        crate_movements["checkout_year"] = pd.to_datetime(
            crate_movements["checkout_date"]
        ).dt.year
        crate_movements["checkout_day"] = pd.to_datetime(
            crate_movements["checkout_date"]
        ).dt.day

        checkouts = crate_movements[
            (crate_movements["checkout_month"] == args["month"])
            & (crate_movements["checkout_year"] == args["year"])
            & (crate_movements["checkout_day"] == args["day"])
        ]

        room_revenue = dfs["cooling_unit_revenue"]

        # Additional computation to calculate revenue_room
        dfs["cooling_unit_revenue"] = data_processor.revenue_room_computation(
            checkouts=checkouts, revenue_room=room_revenue
        )
    elif args["view"] == "company":
        crate_movements = dfs["crates_movement"]

        # Additional computation to calculate revenue_room
        dfs["crates_movement"] = data_processor.revenue_comp_computation(
            revenue_comp=crate_movements
        )


def extract_data(
    conn: connection,
    args: argparse.Namespace,
    queries_data: dict[str, Union[str, list]],
    dir: str = "sql_queries",
    dir2: str = "impact_queries",
    post_process: bool = True,
) -> Union[pd.DataFrame, pd.DataFrame]:
    dfs = {}
    for file_name in os.listdir(dir):
        query_name = file_name.replace(".sql", "")
        query_path = os.path.join(dir, file_name)
        dfs[query_name] = execute_query(conn, query_path, vars(args))

    empty_dfs_keys = [
        key
        for key, value in dfs.items()
        if isinstance(value, pd.DataFrame) and value.empty
    ]
    fill_in_columns = ""
    changing_cols = []

    if args.view == "impact_metrics":
        for file_name in os.listdir(dir2):
            query_name = file_name.replace(".sql", "")
            query_path = os.path.join(dir2, file_name)
            dfs[query_name] = execute_query(conn, query_path, vars(args))

        merged_df = dfs["impact_metrics_room"]
        return merged_df

    # Check if 'crates_out', 'crates_in', or both key in dfs has an empty dataframe
    if (
        isinstance(dfs.get("crates_out"), pd.DataFrame)
        and dfs.get("crates_out").empty
        and isinstance(dfs.get("crates_in"), pd.DataFrame)
        and not dfs.get("crates_in").empty
    ):
        post_process = False
        fill_in_columns = "Check-out"
    elif (
        isinstance(dfs.get("crates_out"), pd.DataFrame)
        and not dfs.get("crates_out").empty
        and isinstance(dfs.get("crates_in"), pd.DataFrame)
        and dfs.get("crates_in").empty
    ):
        post_process = True
        fill_in_columns = "Check-in"
    elif (
        isinstance(dfs.get("crates_out"), pd.DataFrame)
        and dfs.get("crates_out").empty
        and isinstance(dfs.get("crates_in"), pd.DataFrame)
        and dfs.get("crates_in").empty
    ):
        post_process = False
        fill_in_columns = "Both"
    else:
        post_process = True

    # Check if the crates_movements query was executed and make post_process true if so
    if (
        isinstance(dfs.get("crates_movement"), pd.DataFrame)
        and not dfs.get("crates_movement").empty
        and args.view == "company"
    ):
        post_process = True

    # Include Date in query
    date_object = datetime(args.year, args.month, args.day)

    # Check if there was app activity on the day
    if post_process:
        additional_processing(dfs, vars(args))
    else:
        print(
            f"No checkout activity in app for {datetime(args.year, args.month, args.day)}"
        )

    merged_df = dfs["cooling_unit"]

    if args.view == "aggregated-comparison":
        merged_df = dfs["cooling_unit"]
        for df_to_merge in [
            item
            for item in queries_data["aggregated_comparison_view"]
            if item["name"] not in empty_dfs_keys
        ]:
            df = dfs[df_to_merge["name"]]
            merged_df = pd.merge(merged_df, df, on=df_to_merge["on"], how="left")
    elif args.view == "company":
        merged_df = dfs["company"]
        for df_to_merge in [
            item
            for item in queries_data["companies_view"]
            if item["name"] not in empty_dfs_keys
        ]:
            df = dfs[df_to_merge["name"]]
            merged_df = pd.merge(merged_df, df, on=df_to_merge["on"], how="left")
        return merged_df

    # Check if active user columns are empty
    if isinstance(dfs["active_users"], pd.DataFrame) and dfs["active_users"].empty:
        merged_df = merged_df.copy()  # To reduce Dataframe Fraction
        merged_df["active_users"] = 0
        merged_df["active_user_ids"] = [[] for _ in range(len(merged_df))]
        merged_df["active_users_female"] = 0
        merged_df["active_users_male"] = 0
        merged_df["active_users_other"] = 0
        merged_df["room_beneficiary"] = 0
        merged_df["room_beneficiary_male"] = 0
        merged_df["room_beneficiary_female"] = 0

    if fill_in_columns == "Check-in":
        changing_cols = ["crates_in", "operations_in", "kg_in"]

        # Create a new DataFrame by copying to avoid fragmentation
        merged_df = merged_df.copy()
        merged_df[changing_cols] = 0

    elif fill_in_columns == "Check-out":
        changing_cols = [
            "crates_out",
            "operations_out",
            "kg_out",
            "revenue_room",
            "revenue_room_usd",
        ]

        # Create a new DataFrame by copying to avoid fragmentation
        merged_df = merged_df.copy()
        merged_df[changing_cols] = 0
    elif fill_in_columns == "Both":
        changing_cols = [
            "crates_in",
            "operations_in",
            "kg_in",
            "crates_out",
            "operations_out",
            "kg_out",
            "revenue_room",
            "revenue_room_usd",
        ]

        # Create a new DataFrame by copying to avoid fragmentation
        merged_df = merged_df.copy()
        merged_df[changing_cols] = 0

    merged_df = merged_df.assign(date=date_object)

    return merged_df


def extract_lca_data(
    con: connection,
    path: str,
) -> pd.DataFrame:
    df = execute_lca_query(con, path)

    return df


def execute_lca_query(
    con: connection,
    query_path: str,
) -> pd.DataFrame:
    """Given a connection object, the path towards an SQL file and a
    dictionary containing the optional parameter values, execute
    the query and return the result in a DataFrame"""
    cursor = con.cursor()
    with open(query_path) as fp:
        try:
            cursor.execute(fp.read())
            df = pd.DataFrame(cursor.fetchall())
            if not df.empty:
                df.columns = [desc[0] for desc in cursor.description]
        finally:
            cursor.close()
    return df


def company_aggregation(df: pd.DataFrame) -> pd.DataFrame:
    # Include the current day
    df["report_date"] = datetime.now().date()

    # The order of columns for the final company metrics dataframe
    columns_ordered = [
        # Date
        "report_date",
        # Company-specific data
        "company_id",
        "comp_name",
        "comp_logo",
        "comp_country",
        "comp_cap_tons",
        "comp_cap_num_crates",
        "cooling_unit_types",
        # Operator Information
        "comp_op",
        "comp_op_fem",
        "comp_op_ma",
        "comp_op_ot",
        "currency",
        # Demographic data - users
        "comp_reg_users",
        "comp_reg_users_ma",
        "comp_reg_users_fem",
        "comp_reg_users_ot",
        "comp_beneficiaries",
        "comp_beneficiaries_fem",
        "comp_beneficiaries_ma",
        "comp_cool_users",
        "comp_cool_users_fem",
        "comp_cool_users_ma",
        "comp_cool_users_ot",
        "comp_farmers",
        "comp_traders",
        "comp_unspec_user_type",
        # Metrics related to rooms
        "comp_crates_in",
        "comp_ops_in",
        "comp_kg_in",
        "comp_crates_out",
        "comp_ops_out",
        "comp_kg_out",
        "comp_average_room_occupancy",
        "comp_revenue",
        "comp_revenue_usd",
    ]

    # Renaming of columns for company view
    new_column_names = {
        "name": "comp_name",
        "company_logo": "comp_logo",
        "country": "comp_country",
        "total_capacity_in_metric_tons": "comp_cap_tons",
        "total_capacity_in_number_crates": "comp_cap_num_crates",
        "company_ops": "comp_op",
        "company_ops_female": "comp_op_fem",
        "company_ops_male": "comp_op_ma",
        "company_ops_other": "comp_op_ot",
        "total_registered_users": "comp_reg_users",
        "female_registered_users": "comp_reg_users_fem",
        "male_registered_users": "comp_reg_users_ma",
        "other_registered_users": "comp_reg_users_ot",
        "cooling_user_count": "comp_cool_users",
        "cooling_user_female_count": "comp_cool_users_fem",
        "cooling_user_male_count": "comp_cool_users_ma",
        "cooling_user_other_count": "comp_cool_users_ot",
        "beneficiary_count": "comp_beneficiaries",
        "beneficiary_count_male": "comp_beneficiaries_ma",
        "beneficiary_count_female": "comp_beneficiaries_fem",
        "farmers": "comp_farmers",
        "traders": "comp_traders",
        "unspecified_usertype": "comp_unspec_user_type",
        "company_crates_in": "comp_crates_in",
        "company_operations_in": "comp_ops_in",
        "company_kg_in": "comp_kg_in",
        "company_crates_out": "comp_crates_out",
        "company_operations_out": "comp_ops_out",
        "company_kg_out": "comp_kg_out",
        "average_company_room_occupancy": "comp_average_room_occupancy",
        "company_total_revenue": "comp_revenue",
        "company_total_revenue_usd": "comp_revenue_usd",
    }

    df = df.rename(columns=new_column_names)

    df = df[columns_ordered]

    return df


def cooling_units_aggregation(df: pd.DataFrame) -> pd.DataFrame:
    # The order of columns for the final cooling-units metrics dataframe

    columns_ordered = [
        # Date columns
        "date",
        "report_date",
        # Room Information
        "cooling_unit_id",
        "unit_name",
        "is_unit_deleted",
        "state",
        "cool_unit_type",
        "cap_tons",
        "cap_num_crates",
        # Company Information
        "company_id",
        "comp_name",
        "comp_pricing",
        "currency",
        # Operator Information
        "room_op",
        "room_op_fem",
        "room_op_ma",
        "room_op_ot",
        # Demographic data - users
        "room_beneficiaries",
        "room_beneficiaries_fem",
        "room_beneficiaries_ma",
        # Room Activity metrics
        "room_active_users",
        "room_active_user_ids",
        "room_active_fem",
        "room_active_ma",
        "room_active_ot",
        "room_crates_in",
        "room_ops_in",
        "room_kg_in",
        "room_crates_out",
        "room_ops_out",
        "room_kg_out",
        "average_room_occupancy",
        "room_revenue",
        "room_revenue_usd",
        # Produce statistics
        "check_in_crates_crop",
        "check_in_kg_crop",
        "check_out_crates_crop",
        "check_out_kg_crop",
    ]

    # Include the current day
    df["report_date"] = datetime.now().date()

    # Extract unique commodities from columns
    commodities = set()
    for col in df.columns:
        if "(" in col:
            if ")(" in col:
                commodity = col.rsplit("(", 1)[0]
            else:
                commodity = col.rsplit("(", 1)[0]
            commodities.add(commodity.strip())

    # Initialize the new columns
    df["Check-in"] = [{} for _ in range(len(df))]
    df["Check-in-kg"] = [{} for _ in range(len(df))]
    df["Check-out"] = [{} for _ in range(len(df))]
    df["Check-out-kg"] = [{} for _ in range(len(df))]

    for commodity in commodities:
        check_in_col = f"{commodity}(Check-in)"
        check_in_kg_col = f"{commodity}(Check-in-kg)"
        check_out_col = f"{commodity}(Check-out)"
        check_out_kg_col = f"{commodity}(Check-out-kg)"

        if check_in_col in df.columns:
            df["Check-in"] = df.apply(
                lambda row: {**row["Check-in"], commodity: row[check_in_col]}
                if row[check_in_col] != 0
                else row["Check-in"],
                axis=1,
            )
            df.drop(columns=[check_in_col], inplace=True)

        if check_in_kg_col in df.columns:
            df["Check-in-kg"] = df.apply(
                lambda row: {**row["Check-in-kg"], commodity: row[check_in_kg_col]}
                if row[check_in_kg_col] != 0
                else row["Check-in-kg"],
                axis=1,
            )
            df.drop(columns=[check_in_kg_col], inplace=True)

        if check_out_col in df.columns:
            df["Check-out"] = df.apply(
                lambda row: {**row["Check-out"], commodity: row[check_out_col]}
                if row[check_out_col] != 0
                else row["Check-out"],
                axis=1,
            )
            df.drop(columns=[check_out_col], inplace=True)

        if check_out_kg_col in df.columns:
            df["Check-out-kg"] = df.apply(
                lambda row: {**row["Check-out-kg"], commodity: row[check_out_kg_col]}
                if row[check_out_kg_col] != 0
                else row["Check-out-kg"],
                axis=1,
            )
            df.drop(columns=[check_out_kg_col], inplace=True)

    new_column_names = {
        "name": "comp_name",
        "cooling_unit_type": "cool_unit_type",
        "pricing_strategy": "comp_pricing",
        "capacity_in_metric_tons": "cap_tons",
        "capacity_in_number_crates": "cap_num_crates",
        "operators": "room_op",
        "operators_female": "room_op_fem",
        "operators_male": "room_op_ma",
        "operators_other": "room_op_ot",
        "room_beneficiary": "room_beneficiaries",
        "room_beneficiary_male": "room_beneficiaries_ma",
        "room_beneficiary_female": "room_beneficiaries_fem",
        "farmers": "room_farmers",
        "traders": "room_traders",
        "unspecified_usertype": "room_unspec_user_type",
        "active_users": "room_active_users",
        "active_users_female": "room_active_fem",
        "active_users_male": "room_active_ma",
        "active_users_other": "room_active_ot",
        "active_user_ids": "room_active_user_ids",
        "crates_in": "room_crates_in",
        "operations_in": "room_ops_in",
        "kg_in": "room_kg_in",
        "crates_out": "room_crates_out",
        "operations_out": "room_ops_out",
        "kg_out": "room_kg_out",
        "occupancy_room": "average_room_occupancy",
        "revenue_room": "room_revenue",
        "revenue_room_usd": "room_revenue_usd",
        "Check-in": "check_in_crates_crop",
        "Check-in-kg": "check_in_kg_crop",
        "Check-out": "check_out_crates_crop",
        "Check-out-kg": "check_out_kg_crop",
    }

    df = df.rename(columns=new_column_names)

    # Remove all deleted cooling units from the dataframe
    filtered_df = df[df["is_unit_deleted"] == False]

    # Order the columns according to the list above and return the dataframe
    return filtered_df[columns_ordered]


def run_co2_with_id(
    unit_id: int, day: int, month: int, year: int
) -> tuple[float, dict]:
    """Run the compute_co2 script for the specified date."""
    command = f"python3 compute_co2.py --unit_id {unit_id} --day {day} --month {month} --year {year}"
    result = run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Error in script: {result.stderr}")

    last_line = result.stdout.strip().split("\n")[-1]

    try:
        output = json.loads(last_line)
        if isinstance(output, list) and len(output) == 2:
            return tuple(output)
        else:
            raise ValueError("Script output is not a valid tuple")
    except json.JSONDecodeError as e:
        return 0.0, {}


def process_cooling_units(
    unit_ids: list[int], day: int, month: int, year: int
) -> pd.DataFrame:
    """Processes a list of cooling unit IDs and returns a DataFrame with their CO2 savings data.

    Args:
    - con (connection): Database connection object.
    - unit_ids (List[int]): A list of cooling unit IDs.
    - day (int): Day of the month for the report.
    - month (int): Month number for the report.
    - year (int): Year for the report.

    Returns:
    - pd.DataFrame: DataFrame containing CO2 savings data for each cooling unit.
    """

    # Initialize empty DataFrame with specified columns
    co2_df = pd.DataFrame(columns=["cooling_unit_id", "tot_co2", "co2_crops"])

    for unit_id in unit_ids:
        float_val, dict_val = run_co2_with_id(unit_id, day, month, year)

        if not dict_val:
            print(f"No crops in room {unit_id}")
            # Optionally, append a row with null or placeholder values if no data is found
            co2_df = co2_df.append(
                {"cooling_unit_id": unit_id, "tot_co2": None, "co2_crops": {}},
                ignore_index=True,
            )
        else:
            print(
                f"The total CO2 saved in room {unit_id} is {float_val} (kg CO2/ kg fruit) and the CO2 contributions per crop are {dict_val}"
            )
            # Append the data for the current unit to the DataFrame
            co2_df = co2_df.append(
                {
                    "cooling_unit_id": unit_id,
                    "tot_co2": float_val,
                    "co2_crops": dict_val,
                },
                ignore_index=True,
            )

    return co2_df


def convert_val(table_type, index, value):
    """Convert a value based on its index using the CONVERSIONS dict for a given table_type."""
    conversion_dict = CONVERSIONS.get(table_type, {})
    conversion = conversion_dict.get(index)

    if conversion:
        if "ignore" in conversion:
            return None
        if "convert" in conversion:
            return conversion["convert"](value)
    else:
        return str(value)  # Default conversion


def convert_and_insert_company_data(cursor, row):
    converted_row = [convert_val("company", i, val) for i, val in enumerate(row)]
    assert len(converted_row) == 36
    query = """
    INSERT INTO company_metrics(
        report_date, company_id, comp_name, comp_logo, comp_country, comp_cap_tons, comp_cap_num_crates,
        cooling_unit_types, comp_op, comp_op_fem, comp_op_ma, comp_op_ot, currency, comp_reg_users,
        comp_reg_users_ma, comp_reg_users_fem, comp_reg_users_ot, comp_beneficiaries, comp_beneficiaries_fem,
        comp_beneficiaries_ma, comp_cool_users, comp_cool_users_fem, comp_cool_users_ma, comp_cool_users_ot,
        comp_farmers, comp_traders, comp_unspec_user_type, comp_crates_in, comp_ops_in, comp_kg_in, comp_crates_out,
        comp_ops_out, comp_kg_out, comp_average_room_occupancy, comp_revenue, comp_revenue_usd
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    cursor.execute(query, tuple(converted_row))


def convert_and_insert_cooling_unit_data(cursor, row):
    converted_row = [convert_val("cooling_unit", i, val) for i, val in enumerate(row)]
    assert len(converted_row) == 40
    query = """
    INSERT INTO cooling_unit_metrics(
        date, report_date, cooling_unit_id, unit_name, is_unit_deleted, state, cool_unit_type, cap_tons,
        cap_num_crates, company_id, comp_name, comp_pricing, currency, room_op, room_op_fem, room_op_ma,
        room_op_ot, room_beneficiaries, room_beneficiaries_fem, room_beneficiaries_ma, room_active_users,
        room_active_user_ids, room_active_fem, room_active_ma, room_active_ot, room_crates_in, room_ops_in,
        room_kg_in, room_crates_out, room_ops_out, room_kg_out, average_room_occupancy, room_revenue, room_revenue_usd,
        check_in_crates_crop, check_in_kg_crop, check_out_crates_crop, check_out_kg_crop, tot_co2, co2_crops
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    cursor.execute(query, tuple(converted_row))


def convert_and_insert_impact_data(cursor, row):
    # converted_row = [convert_val("impact", i, val) for i, val in enumerate(row)]
    assert len(row) == 31

    query = """
    INSERT INTO impact_metrics(
        report_date, cooling_unit_id, unit_name, company_id, farmer_id, crop_id, first_name, last_name,
        crop_name, currency, baseline_quantity_total_month , baseline_kg_selling_price_month, baseline_kg_loss_month, baseline_perc_loss_month,
        baseline_kg_sold_month, baseline_farmer_revenue_month, monthly_kg_selling_price, monthly_kg_checkin, monthly_kg_loss,
        monthly_farmer_revenue, monthly_kg_selling_price_evolution, monthly_perc_unit_selling_price_evolution, monthly_farmer_revenue_evolution,
        monthly_perc_farmer_revenue_evolution, monthly_perc_loss, monthly_perc_foodloss_diff, monthly_perc_foodloss_evolution, latest_survey_date,
        baseline_completed_surveys_room, possible_post_checkout_survey_room, total_post_checkout_survey_unit
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s);
    """
    cursor.execute(query, tuple(row))


def make_conn_db() -> connection:
    load_dotenv()
    return setup_connection()


def get_latest_date(cursor, table_name: str, default_value = date.min) -> datetime.date:
    if table_name == "cooling_unit_metrics":
        query = f"SELECT max(date) FROM {table_name};"
        cursor.execute(query)
        result = cursor.fetchone()[0]
        return result if result else default_value
    elif table_name == "impact_metrics":
        query = f"SELECT max(report_date) FROM {table_name};"
        cursor.execute(query)
        result = cursor.fetchone()[0]
        return result if result else default_value


def set_date_args(args, date: datetime.date):
    setattr(args, "day", date.day)
    setattr(args, "month", date.month)
    setattr(args, "year", date.year)


def main() -> None:
    args = parse_arguments()
    queries_data = load_json_variables("queries_data.json")
    conn = make_conn_db()
    cursor = conn.cursor()

    if args.view not in ["company", "aggregated-comparison", "impact_metrics"]:
        print(f"Unsupported view: {args.view}")
        sys.exit()

    try:
        if args.view == "aggregated-comparison":
            try:
                latest_date = get_latest_date(cursor, "cooling_unit_metrics")
            except Exception:
                print(
                    "INFO: The cooling_unit_metrics table is empty, starting from 2022-10-01"
                )
                latest_date = datetime(2022, 9, 30).date()

            start_date = latest_date + timedelta(days=1)
            current_date = date.today()

            while start_date <= current_date:
                set_date_args(args, start_date)
                indicator_df = extract_data(conn, args, queries_data)
                replace_nans(indicator_df, list(indicator_df.columns))
                aggregated_comparison_indicator_df = cooling_units_aggregation(
                    indicator_df
                )

                # LCA computation block
                print("Computing CO2 contributions for cooling units...\n")
                base_path = os.getcwd()
                units_path = f"{base_path}/LCA/sql_queries/units.sql"
                query_cooling_units = extract_lca_data(conn, units_path)
                cooling_unit_ids = query_cooling_units["id"].tolist()
                co2_contributions = process_cooling_units(
                    cooling_unit_ids, start_date.day, start_date.month, start_date.year
                )
                merged_df = pd.merge(
                    aggregated_comparison_indicator_df,
                    co2_contributions,
                    on="cooling_unit_id",
                    how="inner",
                )
                replace_nans(merged_df, zero_na_columns=["co2_crops", "tot_co2"])
                for _, row in merged_df.iterrows():
                    convert_and_insert_cooling_unit_data(cursor, row.tolist())

                conn.commit()
                print(
                    f"Data inserted for cooling units metrics table for {start_date}."
                )
                start_date += timedelta(days=1)

        elif args.view == "company":
            current_date = date.today()
            set_date_args(args, current_date)
            indicator_df = extract_data(conn, args, queries_data)
            replace_nans(indicator_df, list(indicator_df.columns))
            company_indicator_df = company_aggregation(indicator_df)

            # Round up the values in the occupancy column
            company_indicator_df["comp_average_room_occupancy"] = np.ceil(
                company_indicator_df["comp_average_room_occupancy"]
            )

            cursor.execute("DELETE FROM company_metrics")

            for _, row in company_indicator_df.iterrows():
                convert_and_insert_company_data(cursor, row.tolist())

            conn.commit()
            print("Data inserted for company_metrics table.")

        elif args.view == "impact_metrics":
            backfill_start = datetime(2022, 1, 1).date()
            latest_date = get_latest_date(cursor, "impact_metrics",backfill_start)
            start_date = max(backfill_start, latest_date + timedelta(days=1))
            current_date = date.today()

            # Process data month by month until current date
            while start_date <= current_date:
                # Calculate the first day of the next month
                if start_date.month == 12:
                    next_month = date(start_date.year + 1, 1, 1)
                else:
                    next_month = date(start_date.year, start_date.month + 1, 1)

                # Process each month, and define arguments as PostgreSQL formatted datetime strings
                set_date_args(args, start_date)
                setattr(args, "datetime_start", start_date.strftime("%Y-%m-%d %H:%M:%S"))
                setattr(args, "datetime_end", next_month.strftime("%Y-%m-%d %H:%M:%S"))
                setattr(args, "date_end", next_month.strftime("%Y-%m-%d"))

                try:
                    indicator_df = extract_data(conn, args, queries_data)
                    replace_nans(indicator_df, list(indicator_df.columns))

                    for _, row in indicator_df.iterrows():
                      convert_and_insert_impact_data(cursor, row.tolist())

                    conn.commit()
                    print(f"Data for {start_date.year}-{start_date.month:02d} inserted in impact_metric table.")
                except Exception as e:
                    print(f"Error processing {start_date.year}-{start_date.month:02d}: {str(e)}")
                    conn.rollback()

                # Move to the next month
                start_date = next_month

            print("Impact metrics backfill completed.")

        else:
            print("The computation for the current month has already been done.")

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
