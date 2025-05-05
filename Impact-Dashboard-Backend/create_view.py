"""Creates (or replaces) a view from the statements listed in views folder

Executes the create view statement defined in the respective view/<>.sql file

Typical Usage:
    python create_view.py -v analytics_view_name
"""
import argparse

from dotenv import load_dotenv

from utils import setup_connection


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create a particular view in the DB")
    parser.add_argument(
        "-v", required=True, help="The exact name of the view to create"
    )
    return parser.parse_args()


def create_view(conn, filename):
    with conn.cursor() as cursor:
        cursor.execute(open(filename).read())
        conn.commit()


def main():
    load_dotenv()
    args = parse_arguments()
    conn = setup_connection()
    try:
        print("Creating view", args.v)
        create_view(conn, "views/" + args.v + ".sql")
        print("View", args.v, "created")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
