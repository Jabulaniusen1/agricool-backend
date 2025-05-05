import json
import os

import psycopg2
from pandas import DataFrame
from psycopg2._psycopg import connection


def setup_connection() -> connection:
    """Opens the connection to the coldivate database using the configuration
       from the environment variables. Requires DB_USERNAME and DB_PASSWORD
       in .env file

    Returns:
        A psycopg2 connection object connecting to the coldivate database
    """

    connection = psycopg2.connect(
        user=os.environ.get("DB_USERNAME", "base"),
        password=os.environ.get("DB_PASSWORD", "base"),
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "base"),
    )

    return connection


def load_json_variables(filename: str) -> dict:
    """Loads variables from json file to dictionary"""
    with open(filename) as fp:
        vars = json.load(fp)
    return vars


def replace_nans(df: DataFrame, zero_na_columns: list) -> None:
    """Replace NaNs in columns with zeros where this makes sense inplace"""
    df.fillna(value={col: 0 for col in zero_na_columns}, inplace=True)
