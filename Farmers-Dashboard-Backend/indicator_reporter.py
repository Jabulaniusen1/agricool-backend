import warnings
import os
import argparse
import json
from datetime import date, datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from psycopg2.extensions import connection
from utils import replace_nans, setup_connection
from typing import List, Tuple, Dict, Union

warnings.filterwarnings(action="ignore", category=FutureWarning)

# Data types for cooling unit view
FARMER_CONVERSIONS = {
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
    3: {"convert": lambda x: int(float(x))},
    5: {"convert": lambda x: int(float(x))},
    6: {"convert": lambda x: int(float(x))},
    7: {"convert": lambda x: int(float(x))},
    8: {"convert": lambda x: int(float(x))},
    9: {"convert": lambda x: int(float(x))},
    10: {"convert": lambda x: int(float(x))},
    11: {"convert": lambda x: json.dumps(x)},
    12: {"convert": lambda x: json.dumps(x)},
    13: {"convert": lambda x: json.dumps(x)},
    14: {"convert": lambda x: json.dumps(x)},
}

CONVERSIONS = {"farmer": FARMER_CONVERSIONS}


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
            cursor.execute(fp.read(), params)
            df = pd.DataFrame(cursor.fetchall())
            if not df.empty:
                df.columns = [desc[0] for desc in cursor.description]
        finally:
            cursor.close()
    return df


def extract_data(
        conn: connection,
        args: argparse.Namespace,
        dir: str = "sql_queries",
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

    # Check if 'crates_out', 'crates_in', or both key in dfs has an empty dataframe
    if (
            isinstance(dfs.get("crates_out"), pd.DataFrame)
            and dfs.get("crates_out").empty
            and isinstance(dfs.get("crates_in"), pd.DataFrame)
            and not dfs.get("crates_in").empty
    ):
        fill_in_columns = "Check-out"
    elif (
            isinstance(dfs.get("crates_out"), pd.DataFrame)
            and not dfs.get("crates_out").empty
            and isinstance(dfs.get("crates_in"), pd.DataFrame)
            and dfs.get("crates_in").empty
    ):
        fill_in_columns = "Check-in"
    elif (
            isinstance(dfs.get("crates_out"), pd.DataFrame)
            and dfs.get("crates_out").empty
            and isinstance(dfs.get("crates_in"), pd.DataFrame)
            and dfs.get("crates_in").empty
    ):
        fill_in_columns = "Both"

    # Include Date in query
    date_object = datetime(args.year, args.month, args.day)

    merged_df = pd.DataFrame()
    for df_name, df in dfs.items():
        if df_name not in empty_dfs_keys:
            if merged_df.empty:
                merged_df = df
                merged_df.set_index(["farmer_id", "cooling_unit_id"], inplace=True)
            else:
                df.set_index(["farmer_id", "cooling_unit_id"], inplace=True)
                # merged_df = pd.merge(merged_df, df, on=["farmer_id", "cooling_unit_id"], how="outer")
                merged_df = pd.concat([merged_df, df], axis=1, join='outer')

    merged_df = merged_df.copy()
    merged_df.reset_index(inplace=True)
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
            "kg_out"
        ]

        # Create a new DataFrame by copying to avoid fragmentation
        merged_df = merged_df.copy()
        merged_df[changing_cols] = 0

    merged_df = merged_df.assign(date=date_object)

    # Drop nan rows based on the farmer_id and gender column to remove any deleted user data
    merged_df = merged_df[(~pd.isna(merged_df['gender']))]
    merged_df = merged_df[(~pd.isna(merged_df['farmer_id']))]

    return merged_df


def data_aggregation(df: pd.DataFrame) -> pd.DataFrame:
    # The order of columns for the final cooling-units metrics dataframe

    columns_ordered = [
        "date",
        "report_date",
        "farmer_id",
        "cooling_unit_id",
        "gender",
        "room_crates_in",
        "room_ops_in",
        "room_kg_in",
        "room_crates_out",
        "room_ops_out",
        "room_kg_out",
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
        "crates_in": "room_crates_in",
        "operations_in": "room_ops_in",
        "kg_in": "room_kg_in",
        "crates_out": "room_crates_out",
        "operations_out": "room_ops_out",
        "kg_out": "room_kg_out",
        "Check-in": "check_in_crates_crop",
        "Check-in-kg": "check_in_kg_crop",
        "Check-out": "check_out_crates_crop",
        "Check-out-kg": "check_out_kg_crop",
    }

    df = df.rename(columns=new_column_names)

    # Order the columns according to the list above and return the dataframe
    return df[columns_ordered]


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


def convert_and_insert_data(cursor, row):
    converted_row = [convert_val("farmer", i, val) for i, val in enumerate(row)]
    assert len(row) == 15
    query = """
    INSERT INTO farmer_metrics(
        date, report_date, farmer_id, cooling_unit_id, gender, room_crates_in, room_ops_in, room_kg_in, room_crates_out, room_ops_out, room_kg_out, check_in_crates_crop, check_in_kg_crop, check_out_crates_crop, check_out_kg_crop 
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    cursor.execute(query, tuple(converted_row))


def make_conn_db() -> connection:
    load_dotenv()
    return setup_connection()


def get_latest_date(cursor, table_name: str) -> datetime.date:
    query = f"SELECT max(date) FROM {table_name};"
    cursor.execute(query)
    result = cursor.fetchone()[0]
    return result if result else None


def set_date_args(args, date: datetime.date):
    setattr(args, "day", date.day)
    setattr(args, "month", date.month)
    setattr(args, "year", date.year)


def main() -> None:
    args = parse_arguments()
    conn = make_conn_db()
    cursor = conn.cursor()

    try:

        start_date = get_latest_date(cursor, "farmer_metrics")
        if start_date is None:
            print("INFO: The farmer_metrics table is empty, starting from 2022-10-01")
            start_date = datetime(2022, 10, 1).date()

        start_date = start_date + timedelta(days=1)
        current_date = date.today()
        while start_date <= current_date:
            set_date_args(args, start_date)
            indicator_df = extract_data(conn, args)
            replace_nans(indicator_df, list(indicator_df.columns))
            aggregated_indicator_df = data_aggregation(
                indicator_df
            )

            for _, row in aggregated_indicator_df.iterrows():
                convert_and_insert_data(cursor, row.tolist())

            conn.commit()
            print(
                f"Data inserted for farmer metrics table for {start_date}."
            )
            start_date += timedelta(days=1)

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
