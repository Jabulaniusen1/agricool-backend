# Importing required libraries
import sys
import time
import re
import requests
import datetime
import calendar
import os
import glob
import openpyxl
from dateutil.relativedelta import relativedelta
import warnings
import configparser
import pandas as pd
import shutil
import logging
from typing import *
from bs4 import BeautifulSoup
from sklearn.preprocessing import LabelEncoder
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from requests.exceptions import ConnectionError, HTTPError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from selenium.webdriver.chrome.service import Service
from data_foward_fill import ForwardFill
from difflib import SequenceMatcher

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
pd.set_option('mode.chained_assignment', None)


class SheetNotFoundError(Exception):
    pass


class ColumnNotFoundError(Exception):
    pass


class DataScraper:
    def __init__(self, file_path, webdriver_path, sleep_time=5):
        # Configuration attributes
        self.file_path = file_path
        self.sleep_time = sleep_time

        # Commodity and state information
        self.comm = [
            "tomato",
            "onion",
            "ripe_plantain",
            "unripe_plantain",
            "sweet_potato",
            "irish_potato",
        ]
        self.state_names = [
            "ABIA",
            "ADAMAWA",
            "AKWA IBOM",
            "ANAMBRA",
            "BAUCHI",
            "BAYELSA",
            "BENUE",
            "BORNO",
            "CROSS RIVER",
            "DELTA",
            "EBONYI",
            "EDO",
            "EKITI",
            "ENUGU",
            "GOMBE",
            "IMO",
            "JIGAWA",
            "KADUNA",
            "KANO",
            "KATSINA",
            "KEBBI",
            "KOGI",
            "KWARA",
            "LAGOS",
            "NASARAWA",
            "NIGER",
            "OGUN",
            "ONDO",
            "OSUN",
            "OYO",
            "PLATEAU",
            "RIVERS",
            "SOKOTO",
            "TARABA",
            "YOBE",
            "ZAMFARA",
            "ABUJA",
        ]
        self.comm_index_list = {
            "tomato": "Tomato",
            "onion": "Onion bulb",
            "ripe_plantain": "Plantain(ripe)",
            "unripe_plantain": "Plantain(unripe)",
            "sweet_potato": "Sweet potato",
            "irish_potato": "Irish potato",
        }

        # Relevant URLs
        self.NBS_URL = "https://nigerianstat.gov.ng/elibrary"
        self.USD_NGN_URL = "https://finance.yahoo.com/quote/NGN%3DX/history?p=NGN%3DX"

        # Date attributes
        self.start_date = datetime.date(2017, 1, 1)
        self.current_date = datetime.date.today()
        self.end_date = self.current_date - relativedelta(months=1)
        self.endMonthString = None
        self.month_year_string = None
        self.month_year_string_cpi = None
        self.master_df_date = pd.read_csv(f"{self.file_path}/Master_dataframe.csv")
        self.master_df_date["Date"] = pd.to_datetime(self.master_df_date["Date"], format='mixed')
        self.scraping_logger = self.master_df_date["Date"].max().date()
        self.scrape_date = None
        self.date_range = pd.date_range(self.scraping_logger, self.end_date, freq="MS")
        self.currentYear = datetime.datetime.now().year

        # Initialize browser
        self.browser = None

        # Logger
        # Create a custom logger
        self.logger = logging.getLogger(__name__)

        # Set the level of the logger. This can be DEBUG, INFO, WARNING, ERROR, or CRITICAL
        self.logger.setLevel(logging.INFO)

        # Create handlers
        self.c_handler = logging.StreamHandler()
        self.f_handler = logging.FileHandler('file.log')
        self.c_handler.setLevel(logging.INFO)
        self.f_handler.setLevel(logging.ERROR)

        # Create formatters and add it to handlers
        self.c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        self.f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.c_handler.setFormatter(self.c_format)
        self.f_handler.setFormatter(self.f_format)

        # Add handlers to the logger
        self.logger.addHandler(self.c_handler)
        self.logger.addHandler(self.f_handler)

    def get_correct_link(self, links, pattern) -> Optional[str]:
        """
        This function uses regular expressions to locate the appropriate links
        for downloading the commodity prices and CPI features from the NMS site.

        Args:
            links (list): A list of links to search.
            pattern (str): A regular expression pattern to match against the links.

        Returns:
            str: The first link that matches the pattern, or None if no match is found.
        """
        compiled_pattern = re.compile(pattern)

        for link in links:
            if compiled_pattern.match(link):
                return link

        return None

    def scrape_nbs(self, data, matching_string, rename_string, save_string, save_message, pattern) -> None:
        """
        Function for scraping the NBS site.

        Args:
            data (str): Name of the data being scraped.
            matching_string (str): String for locating the commodity prices/CPI file on the NBS website.
            rename_string (str): String for locating the downloaded excel file from within the system directory
            save_string (str): String used to save the downloaded file with a new name.
            save_message (str): Message to print after successful scraping.
            pattern (str): Regular expression pattern used to find the correct link.
        """
        self.logger.info(f"Scraping the {data}")
        self.browser.get(self.NBS_URL)
        time.sleep(self.sleep_time)

        # Get the data table from the website
        df = pd.read_html(self.browser.page_source, attrs={'id': 'data-table-basic'})[0]

        # Locate the row of the html table containing the download link for the commodity prices/CPI excel
        current_row = df[df['Report Name'] == matching_string].index.values

        # Loop to click next page button till the desired file is found
        for _ in range(1, 10):
            if not current_row.size:
                next_page_path = '//*[@id="data-table-basic_next"]'
                next_page = self.browser.find_element(By.XPATH, next_page_path)
                next_page.click()
                time.sleep(self.sleep_time)
                df = pd.read_html(self.browser.page_source, attrs={'id': 'data-table-basic'})[0]
                current_row = df[df['Report Name'] == matching_string].index.values
            else:
                break

        # True row number is +1 because python indexing starts from 0
        current_row = str(current_row + 1)
        current_path = f'//*[@id="tabledata"]/tr{current_row}/td[8]/a'
        commodities = self.browser.find_element(By.XPATH, current_path)
        commodities.click()
        time.sleep(self.sleep_time)

        # Collect all links on the page
        links = self.browser.find_elements(By.XPATH, "//a")
        time.sleep(self.sleep_time)
        link_list = [str(link.get_attribute("href")) for link in links]

        # Get a list of all files in the download directory before starting the download
        files_before = os.listdir(self.file_path)

        # Find the correct link and navigate to it
        correct_link = self.get_correct_link(link_list, pattern)
        self.browser.get(correct_link)
        time.sleep(self.sleep_time)

        # Wait for a new file to appear in the download directory
        while True:
            files_after = os.listdir(self.file_path)
            new_files = set(files_after) - set(files_before)
            if new_files:
                # A new file has appeared, so the download is complete
                break
            time.sleep(1)  # Wait for 1 second before checking again

        shutil.move(f"{self.file_path}/{new_files.pop()}", f"{self.file_path}{save_string}")



    def scrape_yahoo(self, current_month) -> Tuple[datetime.datetime, float]:
        """
        Function for scraping the yahoo finances site for USDtoNaira exchange rates.

        Args:
            current_month (datetime.datetime): The month for which exchange rates are being scraped.

        Returns:
            Tuple[datetime.datetime, float]: A tuple containing the exchange date and the average exchange rate.
        """
        self.logger.info("Scraping USDtoNaira exchange rates...")

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 '
                          'Safari/537.36'}

        # Request the webpage and create a BeautifulSoup object
        response = requests.get(self.USD_NGN_URL, headers=headers, timeout=5)
        if not response.ok:
            # print('Status code:', response.status_code)
            self.logger.error('Status code:', response.status_code)
            raise Exception('Failed to load page {}'.format(self.USD_NGN_URL))

        page_content = response.text
        doc = BeautifulSoup(page_content, 'html.parser')

        # Find the table and its rows
        table = doc.find_all("table")
        rows = table[0].find_all("tr")

        # Extract data from the rows
        data = []
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue
            date_str = cols[0].text.strip()
            date_obj = datetime.datetime.strptime(date_str, "%b %d, %Y")

            if date_obj.month == current_month.month:
                close = float(cols[4].text.strip())
                data.append({"Date": date_obj, "Close": close})

        data = pd.DataFrame(data)

        # Calculate the average exchange rate
        current_exchange_price = data.agg({'Close': 'mean'})[0]

        exchange_date = current_month
        self.logger.info(" -> Done scraping USDtoNaira exchange rates")

        return exchange_date, current_exchange_price

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(10), retry=retry_if_exception_type((ConnectionError, HTTPError)),
           retry_error_callback=lambda retry_state: (print(
               "Error: Reached maximum number of retries, the NBS website is not available at the moment.\nScraping "
               "will commence later \nExiting..."),
                                                     sys.exit(1)))
    def check_stability(self):
        try:
            response = requests.get(self.NBS_URL)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Error: {e}. Retrying...")
            raise e

        soup = BeautifulSoup(response.content, 'html.parser')
        table_body = soup.find('tbody', {'id': 'tabledata'})
        rows = table_body.find_all('tr')

        data = []
        for row in rows:
            cols = row.find_all('td')
            cols = [col.text.strip() for col in cols]
            data.append([col for col in cols if col])

        df = pd.DataFrame(data)

        if len(df):
            self.logger.info("Connection is stable...")

        return df

    def site_checker(self, date) -> None:
        """
        Function to check if the NBS site is available (Website fluctuates occasionally).

        Args:
            date (datetime.datetime): The date for which data is being scraped.

        Returns:
            None
        """

        try:
            self.logger.info(f"Attempting to scrape data for {date.strftime('%d-%b-%Y')}")
            self.logger.info("Running checks for NBS e-library...")
            self.logger.info("----------------------------------------------------------")

            self.browser.get(self.NBS_URL)

            wait = WebDriverWait(self.browser, self.sleep_time)

            max_page_count = 5

            report_1_found = False
            report_2_found = False

            for page_num in range(max_page_count):
                # Wait for the table to load
                wait.until(EC.presence_of_element_located((By.ID, 'data-table-basic')))
                df = pd.read_html(self.browser.page_source, attrs={'id': 'data-table-basic'})[0]

                report_1_found, report_2_found = self.is_data_available(df, report_1_found, report_2_found)

                if report_1_found and report_2_found:
                    self.logger.info(
                        f"All features on the NBS site for {date.strftime('%d-%b-%Y')} are available for scraping")
                    return

                # Try to go to the next page
                next_page_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="data-table-basic_next"]')))
                next_page_button.click()

            self.end_scraping()

        except Exception as e:
            self.logger.error(f"Error occurred during scraping: {e}")
            self.end_scraping()

    def is_data_available(self, df, report_1_found, report_2_found):
        report_names = df['Report Name']

        if not report_1_found:
            # Check if the first report is present
            report_1_found = any('Selected Food Prices Watch' + self.month_year_string in name for name in report_names)

        if not report_2_found:
            # Check if the second report is present
            report_2_found = any(
                'CPI and Inflation Report' + self.month_year_string_cpi in name for name in report_names)

        return report_1_found, report_2_found

    def end_scraping(self):
        self.logger.info("All features are not yet available for scraping on the NBS site")
        self.logger.info("Scraping will commence again in the next days")
        self.logger.info("Closing module...")
        self.logger.info("End")
        self.browser.quit()
        sys.exit()

    def update_commodity_prices(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Update commodity prices and features in the provided files.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]: A tuple containing the updated dataframes
            for master, CPI, exchange rates, and crude oil prices.
        """

        self.logger.info("Updating section")
        self.logger.info("----------------------------------------------------------\n")
        self.logger.info("Updating commodity prices and features...")
        # Read dataframes from files
        master_df = pd.read_csv(f"{self.file_path}/Master_dataframe.csv")
        cpi_df = pd.read_csv(f"{self.file_path}/CPI.csv")
        exchange_df = pd.read_csv(f"{self.file_path}/USDtoNaira.csv")

        # Update the commodity prices
        for var in self.comm:
            # Read existing commodity excel files
            old_file = pd.read_excel(f"{self.file_path}/{var}.xlsx", engine='openpyxl')
            current_column = []

            for i in range(37):  # Number of states

                # Load the workbook
                workbook = openpyxl.load_workbook(f"{self.file_path}/FOOD_PRICES_NBS.xlsx", read_only=True)

                # Get a list of all sheet names
                sheet_names = workbook.sheetnames

                # Find the first sheet name that contains "state" (case insensitive)
                target_sheet_name = next((name for name in sheet_names if 'state' in name.lower()), None)

                if target_sheet_name is not None:
                    # Read the target sheet into a DataFrame
                    food_prices_df = pd.read_excel(f"{self.file_path}/FOOD_PRICES_NBS.xlsx",
                                                   sheet_name=target_sheet_name, engine='openpyxl')
                else:
                    foward_fill = ForwardFill()
                    foward_fill.fill_commodity_data()
                    self.logger.warning(
                        "Commodity prices (NBS) csv adjustment detected: No sheet with 'state' in its name found in "
                        "commodity prices file from NBS. Data has been forward-filled for this month.")
                    return master_df, cpi_df, exchange_df

                row_index = food_prices_df.applymap(lambda x: 'ITEM' in str(x)).any(axis=1).idxmax()
                food_prices_df.columns = food_prices_df.iloc[row_index]

                # Convert all column names to lowercase
                try:
                    food_prices_df.columns = map(str.lower, food_prices_df.columns)
                except Exception as e:
                    self.logger.error(f"{e}")
                    foward_fill = ForwardFill()
                    foward_fill.fill_commodity_data()
                    self.logger.warning(
                        "Commodity prices (NBS) csv adjustment detected: Change in header row index and"
                        "further unforeseen modifications.")
                    return master_df, cpi_df, exchange_df

                # Find the column name that contains 'item'
                item_column_name = next((col for col in food_prices_df.columns if 'item' in col), None)

                if item_column_name is not None:
                    # Get current price and append it to the current_column list
                    current_price = food_prices_df.loc[
                        food_prices_df[item_column_name] == self.comm_index_list[var.lower()], self.state_names[
                            i].lower()].values[0]
                    current_column.append(current_price)
                else:
                    raise ColumnNotFoundError(
                        "Commodity prices (NBS) csv adjustment detected: No column with 'item' in its name found")

            # Update the old_file dataframe with the new data
            old_file[self.scrape_date] = current_column
            old_file.to_excel(f"{self.file_path}/{var}.xlsx", index=False)

        return master_df, cpi_df, exchange_df

    def update_exogenous_features(self, cpi_df, exchange_df, exchange_date: datetime.datetime,
                                  current_exchange_price,
                                  ) -> None:
        """
        Update the exogenous variable files (CPI, USDtoNaira, and crude prices).

        Args:
            cpi_df (pd.DataFrame): CPI dataframe.
            exchange_df (pd.DataFrame): Exchange rates dataframe.
            exchange_date (str): Date of the exchange rate.
            current_exchange_price (float): Current exchange price.
        """
        # Update CPI
        cpi_nbs = pd.read_excel(f"{self.file_path}/CPI_NBS.xlsx", engine='openpyxl')
        cpi_index = cpi_nbs.index[
            cpi_nbs['Table 1 Composite Consumer Price Index (Base September 1985 = 100)'] == 2017].tolist()
        cpi_nbs = cpi_nbs[cpi_index[0]:]  # Index where data from 2017 begins in dataframe
        current_cpi = cpi_nbs[cpi_nbs['Unnamed: 1'] == self.endMonthString].index.values
        new_cpi_row = pd.DataFrame([[self.scrape_date, cpi_nbs['Unnamed: 2'].loc[current_cpi.max()]]],
                                   columns=['Date', 'Monthly'])
        cpi_df = pd.concat([cpi_df, new_cpi_row])
        # Drop nan rows from cpi_df
        cpi_df = cpi_df.dropna()
        cpi_df.to_csv(f"{self.file_path}/CPI.csv", index=False)
        self.logger.info(" -> CPI file updated successfully")

        # Update Exchange rates
        new_exchange_row = pd.DataFrame([[exchange_date, current_exchange_price]], columns=['Date', 'USDtoNaira'])
        exchange_df = pd.concat([exchange_df, new_exchange_row])
        # Drop nan rows from exchange_df
        exchange_df = exchange_df.dropna()
        exchange_df.to_csv(f"{self.file_path}/USDtoNaira.csv", index=False)
        self.logger.info(" -> USDtoNaira file updated successfully")

    def add_row(self, x: pd.DataFrame, price: float, comm_name: str,
                state_name: str, exchange_df: pd.DataFrame, cpi_df: pd.DataFrame,
                ) -> pd.DataFrame:
        """
        Update the master dataframe with the latest scraped data and features.

        Args:
            x (pd.DataFrame): Master dataframe.
            price (float): Current commodity price.
            comm_name (str): Commodity name.
            state_name (str): State name.
            exchange_df (pd.DataFrame): Exchange rates dataframe.
            cpi_df (pd.DataFrame): CPI dataframe.

        Returns:
            pd.DataFrame: Updated master dataframe.
        """
        new_row = {
            'Date': self.scrape_date,
            'Comm_Name': comm_name,
            'State_Name': state_name,
            'Price': price,
            'Last_Month_Price': x['Price'].iloc[-1],
            'Last_2M_Price': x['Last_Month_Price'].iloc[-1],
            'Last_3M_Price': x['Last_2M_Price'].iloc[-1],
            'Last_4M_Price': x['Last_3M_Price'].iloc[-1],
            'Last_5M_Price': x['Last_4M_Price'].iloc[-1],
            'USDtoNaira': exchange_df['USDtoNaira'].iloc[-1],
            'CPI': cpi_df['Monthly'].iloc[-1],
            'state_roll': x.state_roll.iloc[0]
        }

        x = x._append(new_row, ignore_index=True)
        return x

    def update_master_dataframe(self, master_df, exchange_df, cpi_df,
                                ) -> None:
        """
        Update the master dataframe with the latest commodity prices and features.

        Args:
            master_df (pd.DataFrame): The master dataframe.
            exchange_df (pd.DataFrame): Exchange rates dataframe.
            cpi_df (pd.DataFrame): CPI dataframe.
        """
        # Create a copy of the master Dataframe and clear its content
        new_master_df = master_df.copy()
        new_master_df.drop(new_master_df.index[:], inplace=True)

        # Load updated commodity files
        commodity_files = {
            'Tomato': pd.read_excel(f"{self.file_path}/tomato.xlsx", engine='openpyxl'),
            'Onion': pd.read_excel(f"{self.file_path}/onion.xlsx", engine='openpyxl'),
            'Plantain': pd.read_excel(f"{self.file_path}/plantain.xlsx", engine='openpyxl'),
            'Irish potato': pd.read_excel(f"{self.file_path}/irish_potato.xlsx", engine='openpyxl'),
            'Sweet potato': pd.read_excel(f"{self.file_path}/sweet_potato.xlsx", engine='openpyxl')
        }

        # Update plantain prices with average of ripe and unripe plantain prices
        ripe_plantain_df = pd.read_excel(f"{self.file_path}/ripe_plantain.xlsx", engine='openpyxl')
        unripe_plantain_df = pd.read_excel(f"{self.file_path}/unripe_plantain.xlsx", engine='openpyxl')
        commodity_files['Plantain'][self.scrape_date] = (ripe_plantain_df[self.scrape_date] + unripe_plantain_df[
            self.scrape_date]) / 2
        commodity_files['Plantain'].to_excel(f"{self.file_path}/plantain.xlsx", index=False)

        self.logger.info("\nUpdating Master dataframe file...")
        groups = master_df.groupby(['Comm_Name', 'State_Name'])

        for name, group in groups:
            comm_file = commodity_files[name[0]]
            price_buffer = comm_file[comm_file[' STATE '] == name[1]].iloc[:, -1:].values[0][0]
            new_master_df = pd.concat([new_master_df,
                                       self.add_row(group, price_buffer, name[0], name[1], exchange_df, cpi_df)],
                                      ignore_index=True)

        # Compute state_roll feature (average price of a single commodity across all states)
        new_master_df = new_master_df.set_index(['State_Name', 'Comm_Name', 'Date'])
        new_master_df['state_roll'] = new_master_df.groupby(level=[0, 1]).agg({'Price': 'mean'})
        new_master_df.reset_index(inplace=True)

        new_master_df = new_master_df[
            ['Date', 'State_Name', 'Comm_Name', 'Price', 'Last_Month_Price', 'Last_2M_Price', 'Last_3M_Price',
             'Last_4M_Price', 'Last_5M_Price', 'USDtoNaira', 'CPI', 'state_roll']]

        # Save updated master dataframe
        self.logger.info("Saving Master dataframe file...")
        new_master_df.to_csv(f"{self.file_path}/Master_dataframe.csv", index=False)
        self.logger.info(" -> Done saving Master dataframe file")

    def label_encode_master_dataframe(self, date) -> None:
        """
        Label encode the categorical features of the master dataframe.

        Args:
            date (datetime): Date for which the data was scraped.
        """
        # Load the master dataframe
        new_master_df = pd.read_csv(f"{self.file_path}/Master_dataframe.csv")
        self.logger.info("Label encoding Master dataframe...")

        # Initialize label encoders for state and commodity names
        le_state = LabelEncoder()
        le_comm = LabelEncoder()

        # Fit and transform the categorical features
        new_master_df['st_label'] = le_state.fit_transform(new_master_df['State_Name'])
        new_master_df['comm_label'] = le_comm.fit_transform(new_master_df['Comm_Name'])

        # Drop unnecessary columns
        new_master_df.drop(columns=['State_Name', 'Comm_Name'], inplace=True)

        # Save the encoded master dataframe
        self.logger.info("Saving Master encoded file...")
        new_master_df.to_csv(f"{self.file_path}/Master_encoded.csv", index=False)
        self.logger.info(f" -> Done Scraping data for {str(date.strftime('%d-%b-%Y'))}. \n")

    def run(self) -> None:  # Function to run the script
        # Check for scraping
        if self.scraping_logger.month == self.end_date.month:  # Check if the data in the file system is updated
            self.logger.info("Data has been scraped for this month!")
            self.logger.info("---------------------------------------")
            self.logger.info("All files are up to date.")
            sys.exit()
        else:
            # Check if the master dataframe is updated. If so then no scraping will occur
            if self.scraping_logger.strftime('%Y-%m-%d') in self.date_range:
                self.date_range = self.date_range.drop(self.scraping_logger)

            for date in self.date_range:

                self.scrape_date = date

                # Initialize browser
                chrome_options = Options()
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-dev-shm-usage')
                prefs = {
                    'download.default_directory': self.file_path,
                    'download.prompt_for_download': False,
                    "download.directory_upgrade": True}  # Specify the file system for default downloads by the webdriver
                chrome_options.add_experimental_option('prefs', prefs)

                service = Service()
                self.browser = webdriver.Chrome(service=service, options=chrome_options)

                self.endMonthString = calendar.month_name[date.month]  # The month string for the data to be scraped
                link_month = str(
                    self.endMonthString)  # month part of the link/string for downloading the commodity prices and CPI
                link_year = str(date.year)  # year part of the link/string for downloading the commodity prices and CPI
                self.month_year_string = f' ({link_month} {link_year})'  # String pattern for commodity price scraping
                self.month_year_string_cpi = f' {link_month} {link_year}'  # String pattern for CPI scraping

                # Check if the NBS site is stable
                self.check_stability()

                # Check if the latest data is available on the NBS site
                self.site_checker(date)

                # Scraping the Selected Food prices
                self.logger.info("Scraping section")
                self.logger.info("----------------------------------------------------------\n")
                self.scrape_nbs(data="commodity prices...",
                                matching_string=f"Selected Food Prices Watch{self.month_year_string}",
                                rename_string=f"Selected Food Prices Watch{self.month_year_string}",
                                save_string="/FOOD_PRICES_NBS.xlsx", save_message=" -> Done scraping commodity prices",
                                pattern=r'.*SELECTED.*')

                # Scraping Consumer Price Index
                time.sleep(self.sleep_time)
                self.scrape_nbs(data="Consumer Price Indexes...",
                                matching_string=f"CPI and Inflation Report{self.month_year_string_cpi}",
                                rename_string=f"cpi_1New{datetime.datetime.now().strftime('%B').upper()}{datetime.datetime.now().strftime('%Y')}",
                                save_string="/CPI_NBS.xlsx", save_message=" -> Done scraping Consumer Price Indexes",
                                pattern=r'.*cpi.*')

                # Scraping Monthly USD/NAIRA exchange rates
                time.sleep(self.sleep_time)
                exchange_date, current_exchange_price = self.scrape_yahoo(
                    date)

                # Update section
                try:
                    master_df, cpi_df, exchange_df = self.update_commodity_prices()  # Update the individual
                except Exception as e:
                    self.logger.error(f"Terminating program due to error: {e}")
                    sys.exit(1)

                # commodity excel sheets
                self.update_exogenous_features(cpi_df, exchange_df, exchange_date,
                                               current_exchange_price)  # Update individual

                # Load updated files
                exchange_df = pd.read_csv(f"{self.file_path}/USDtoNaira.csv")
                cpi_df = pd.read_csv(f"{self.file_path}/CPI.csv")

                # exogenous variable files(excel sheets and csv)
                self.update_master_dataframe(master_df, exchange_df, cpi_df)  # Update the master dataframe

                # List of files to remove (to clean up data directory)
                files_to_remove = ["FOOD_PRICES_NBS.xlsx", "CPI_NBS.xlsx"]
                for filename in files_to_remove:
                    try:
                        os.remove(f"{self.file_path}/{filename}")
                        self.logger.info(f"File {filename} has been deleted.")
                    except FileNotFoundError:
                        self.logger.info(f"No outdated file {filename} to remove.")

                # Label encoding section
                self.label_encode_master_dataframe(date)  # Label encode the master dataframe

            # Terminate script
            self.logger.info("Closing module...")
            self.logger.info("End")


def main():
    # Importing required initial values
    config = configparser.RawConfigParser()
    config.optionxform = lambda option: option
    config.read('./config.ini')
    file_path = dict(config.items('paths'))['data']  # Path for saving files
    webdriver_path = dict(config.items('paths'))['webdriver']  # Path to chromedriver

    scraper = DataScraper(file_path, webdriver_path)
    scraper.run()


if __name__ == "__main__":
    main()
