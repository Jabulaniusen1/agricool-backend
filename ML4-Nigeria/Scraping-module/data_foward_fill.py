import configparser
import pandas as pd
import os
import configparser
from typing import Dict

config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read('/app/config.ini')
file_path = dict(config.items('paths'))['data']

class ForwardFill:
    def __init__(self):
        self.config = config
        self.file_path = file_path

    def fill_commodity_data(self) -> None:
        """
        Forward fills data for the previous month for the commodity excel files in the data folder.

        Returns:
        - dict: A dictionary containing dataframes for each commodity with the forward filled data.
        """

        # Load the commodity files
        commodity_files = {
            'tomato': pd.read_excel(f"{self.file_path}/tomato.xlsx", engine='openpyxl'),
            'onion': pd.read_excel(f"{self.file_path}/onion.xlsx", engine='openpyxl'),
            'ripe_plantain': pd.read_excel(f"{self.file_path}/ripe_plantain.xlsx", engine='openpyxl'),
            'unripe_plantain': pd.read_excel(f"{self.file_path}/unripe_plantain.xlsx", engine='openpyxl'),
            'irish_potato': pd.read_excel(f"{self.file_path}/irish_potato.xlsx", engine='openpyxl'),
            'sweet_potato': pd.read_excel(f"{self.file_path}/sweet_potato.xlsx", engine='openpyxl')
        }

        updated_dataframes = {}

        for crop, df in commodity_files.items():
            # Extract the last column's name (date) and convert it to a datetime object
            last_date = pd.to_datetime(df.columns[-1], format="%d.%m.%Y")

            # Compute the next month's date and format it back to string
            next_month_date = (last_date + pd.DateOffset(months=1))

            # Assign data from the last column to the new column
            df[next_month_date] = df[df.columns[-1]]

            updated_dataframes[crop] = df

        for k, v in updated_dataframes.items():

            if k.lower() in ["tomato", "unripe_plantain", "ripe_plantain", "onion", "irish_potato", "sweet_potato"]:
                updated_dataframes[k].to_excel(f"{self.file_path}/{k.lower()}.xlsx", index=False)

        return
