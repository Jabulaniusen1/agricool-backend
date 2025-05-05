import argparse
import json
import os
from subprocess import run

import pandas as pd
from dotenv import load_dotenv
from psycopg2.extensions import connection

from utils import setup_connection

# Initialize the argparse
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--day", type=int, required=True, help="Day of the month")
parser.add_argument("-m", "--month", type=int, help="Month number")
parser.add_argument("-y", "--year", type=int, default=2024, help="Year")
args = parser.parse_args()


def make_conn_db() -> connection:
    """Loads environment variables and makes a database connection."""
    load_dotenv()
    return setup_connection()


def execute_query(
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


def extract_data(
    con: connection,
    path: str,
) -> pd.DataFrame:
    df = execute_query(con, path)

    return df


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


def process_cooling_units(con, unit_ids: list[int], day: int, month: int, year: int):
    """Processes a list of cooling unit IDs, modified to use argparse values."""

    for unit_id in unit_ids:
        float_val, dict_val = run_co2_with_id(unit_id, day, month, year)
        if not dict_val:
            print(f"No crops in room {unit_id}")
        else:
            print(
                f"The total CO2 saved in room {unit_id} is {float_val} (kg CO2/ kg fruit) and the CO2 contributions "
                f"per crop are {dict_val}"
            )


base_path = os.getcwd()
conn = make_conn_db()
units_path = f"{base_path}/sql_queries/units.sql"
query_cooling_units = extract_data(conn, units_path)
cooling_unit_ids = query_cooling_units["id"].tolist()
process_cooling_units(conn, cooling_unit_ids, args.day, args.month, args.year)
