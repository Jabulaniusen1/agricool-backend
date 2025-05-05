# Importing required libraries
import sys
# sys.path.append('/app/data/')
from data.common import Data_merge

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import datetime
import pandas as pd
import numpy as np
import requests
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
import configparser

config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read('./config.ini')

#Config file items
dict_state = dict(config.items('dict_state'))
dict_commodities = dict(config.items('dict_commodities'))
dict_district = dict(config.items('dict_district'))
dict_market = dict(config.items('dict_market'))
file_path = dict(config.items('paths'))['data']

commodities = [commodity for commodity in dict_commodities.keys()]  #['Green Chilli', 'Apple', 'Banana', 'Tomato']

# Scraping websites

agmarknet_Path = 'https://agmarknet.gov.in/'
USD_INR_path = 'https://finance.yahoo.com/quote/USDINR%3DX/history?p=USDINR%3DX'
Brent_path = 'https://finance.yahoo.com/quote/BZ%3DF/history?p=BZ%3DF'

# Helper functions

def scrape_yahoo_finance(url, tries=10, sleep=5):
    if tries < 1:
        raise AssertionError('Tries must be a positive number.')

    for i in range(tries):
        try:
            r = requests.get(url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
            data = pd.read_html(r.text)[0]
            assert 'Date' in data.columns
        except:
            if i < tries - 1:
                print(f'Site is not available at the moment, retrying in {sleep} seconds.')
                time.sleep(sleep)
                continue
            else:
                print('Exceeded maximum number of tries. Try again later.')
                raise
        # Return data as soon as we succed
        return data

def append_new_yahoo_data(data, path):
    df = data[["Date", "Close*"]]
    df.rename(columns={"Close*": "Close"}, inplace=True)
    df = df[df.Date.str.contains('[a-zA-Z].*\s+\d{1,2},\s+\d{4}')]     # Check for date time format and select rows that match only
    df["Date"] = pd.to_datetime(df["Date"], format = "%b %d, %Y")

    df_old = pd.read_csv(path)
    df_old["Date"] = pd.to_datetime(df_old["Date"],format = "%Y-%m-%d")
    df_new = df_old.append(df[(df["Date"] > max(df_old["Date"])) & (df["Date"] <= (datetime.date.today() - datetime.timedelta(days = 1)).strftime('%Y-%m-%d'))])
    df_new = df_new.sort_values(by = "Date", ascending = True).reset_index(drop = True)
    df_new.to_csv(path, index=False)

# Setting webdriver options

chrome_options = Options()
chrome_options.add_argument('--headless')					#To run the webdriver in headless mode
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
# assert chrome_options.headless

browser = webdriver.Chrome(options=chrome_options)
update_master_encoded = False
sleep_time = 3

# Scraping Agricultural data

print("Scraping Agricultural Data")
browser.get(agmarknet_Path)

browser.find_element(By.XPATH,'//*[@id="ddlArrivalPrice"]').send_keys('Both')
time.sleep(sleep_time)
browser.find_element(By.XPATH,'//*[@id="txtDate"]').clear()
time.sleep(sleep_time)
browser.find_element(By.XPATH,'//*[@id="txtDateTo"]').clear()
time.sleep(sleep_time)

for commodity in commodities:
    old_item = pd.read_csv(file_path + '/{}_price.csv'.format(commodity))
    date = (max(pd.to_datetime(old_item['Reported Date'])) + datetime.timedelta(days = 1)).strftime('%d-%b-%Y')
    today = (datetime.date.today() - datetime.timedelta(days = 1)).strftime('%d-%b-%Y')
    time.sleep(sleep_time)
    browser.find_element(By.XPATH,'//*[@id="ddlCommodity"]').send_keys(commodity)
    dates_to_scrape = pd.date_range(date, today).strftime('%d-%b-%Y')
    if len(dates_to_scrape) != 0:
        update_master_encoded = True
        for day in dates_to_scrape:
            for state in list(dict_state.keys()):
                browser.find_element(By.XPATH,'//*[@id="ddlArrivalPrice"]').send_keys('Both')
                time.sleep(sleep_time)
                browser.find_element(By.XPATH,'//*[@id="ddlState"]').send_keys(state)
                time.sleep(sleep_time)
                browser.find_element(By.XPATH,'//*[@id="txtDate"]').clear()
                time.sleep(sleep_time)
                browser.find_element(By.XPATH,'//*[@id="txtDate"]').send_keys(day)
                time.sleep(sleep_time)
                browser.find_element(By.XPATH,'//*[@id="txtDateTo"]').clear()
                time.sleep(sleep_time)
                browser.find_element(By.XPATH,'//*[@id="txtDateTo"]').send_keys(day)
                time.sleep(sleep_time)
                browser.find_element(By.XPATH,'//*[@id="txtDateTo"]').send_keys(Keys.ENTER)
                time.sleep(sleep_time + sleep_time)

                try:
                    df = pd.read_html(browser.page_source, attrs={'id':'cphBody_GridViewBoth'})[0]  # Read the table as dataframe
                    condition = ~(df.iloc[:,0].str[0]=='-')						# Condition to remove rows that correspond to cummulative State values
                    df = df[condition]

                    if (df.iloc[0][0] == 'State Name'):
                        df.columns = df.iloc[0]
                        df = df.iloc[1:]

                    commodity_data = df.copy()
                    commodity_data.reset_index(inplace = True, drop = True)
                    commodity_data = commodity_data[~commodity_data['Reported Date'].isna()]				# Copying data corresponding to error due to merged cells

                    try:
                        commodity_data = commodity_data.drop(['Unnamed: 0'],1).drop_duplicates().reset_index(drop=True)
                    except:
                        commodity_data = commodity_data.drop_duplicates().reset_index(drop=True)

                    try:
                        commodity_data['Date'] = pd.to_datetime(commodity_data['Reported Date'], format="%d %b %Y")
                        commodity_data = commodity_data.sort_values(['Date'])

                        try:
                            old_item = pd.read_csv(file_path + '//{}_price.csv'.format(commodity))		# Reading already existing commodity database
                            new_item = commodity_data
                            master_data = pd.concat([old_item, new_item])				# Appending newly scraped data to existing database
                            master_data.to_csv(file_path + '//{}_price.csv'.format(commodity), index=False)	# Overwriting existing database with updated one

                        except:
                            commodity_data.to_csv(file_path + '/{}_price.csv'.format(commodity), index=False)
                        print("Pulled :",day,"for", commodity, "in",state)
                        time.sleep(sleep_time)
                    except:
                        print("Error in parsing the scraped data for", commodity, state, "on date :",day)
                except:
                    print("No table found for", commodity, day, state)
    else:
        print("File up to date")

print("Done scraping Agricultural Data")

print("Closing browser")
browser.quit()

# Scraping USD to INR conversion rate

print("Scraping USD conversion rate")
USD_df = pd.read_csv(file_path + '/USDINR.csv')
USD_df["Date"] = pd.to_datetime(USD_df["Date"],format = "%Y-%m-%d")

if (max(USD_df["Date"]).strftime('%Y-%m-%d') == (datetime.date.today() - datetime.timedelta(days = 1)).strftime('%Y-%m-%d')):
    print("USD price already updated")
else:
    update_master_encoded = True
    data = scrape_yahoo_finance(USD_INR_path, tries=60, sleep=5)
    append_new_yahoo_data(data, file_path + '/USDINR.csv')
    print("Done scraping USD scraping Data")

# Scraping Brent Crude Oil Prices

print("Scraping Brent Crude Oil Price")
Brent_df = pd.read_csv(file_path + '/Brent_csv.csv')
Brent_df["Date"] = pd.to_datetime(Brent_df["Date"],format = "%Y-%m-%d")

if (max(Brent_df["Date"]).strftime('%Y-%m-%d') == (datetime.date.today() - datetime.timedelta(days = 1)).strftime('%Y-%m-%d')):
    print("Brent crude oil price already updated")
else:
    update_master_encoded = True
    data = scrape_yahoo_finance(Brent_path)
    append_new_yahoo_data(data, file_path + '/Brent_csv.csv')
    print("Done scraping Brent Oil Price.")

# Master Encoded

print("Updating Master encoded file")
if not update_master_encoded:
    print("File already updated")
else:
    consolidated = Data_merge(file_path, commodities, dict_state, dict_market)

    consolidated['State_Label'] = consolidated.apply(lambda x : int(dict_state[x['State Name']]), axis=1)
    consolidated['District_Label'] = consolidated.apply(lambda x : int(dict_district[x['District Name']]), axis=1)
    consolidated['Market_Label'] = consolidated.apply(lambda x : int(dict_market[x['Market Name']]), axis=1)
    consolidated['Comm_Label'] = consolidated.apply(lambda x : int(dict_commodities[x['Commodity']]), axis=1)

    start = max(consolidated['Date']) - datetime.timedelta(200)

    cols = ['Date','State_Label','District_Label','Market_Label','Comm_Label','Arrivals (Tonnes)','Modal Price (Rs./Quintal)',
        'Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price',
        'week','day','month', 'USDtoINR','BrentOil_Price','State_Roll', 'District_Roll','Availability','Available',
        'Available_1D_Price', 'Available_2D_Price', 'Available_3D_Price', 'Available_4D_Price', 'Available_5D_Price', 'Available_6D_Price', 'Available_7D_Price',
        'USDINR_1D', 'Brent_1D', 'USDINR_2D', 'Brent_2D', 'USDINR_3D', 'Brent_3D', 'USDINR_4D', 'Brent_4D', 'USDINR_5D', 'Brent_5D', 'USDINR_6D', 'Brent_6D', 'USDINR_7D', 'Brent_7D',
        'USDINR_8D', 'Brent_8D', 'USDINR_9D', 'Brent_9D', 'USDINR_10D', 'Brent_10D', 'USDINR_11D', 'Brent_11D', 'USDINR_12D', 'Brent_12D', 'USDINR_13D', 'Brent_13D', 'USDINR_14D', 'Brent_14D',
        'USDtoINR_lag', 'BrentOil_Price_lag', 'Availability_bit']

    all_data = consolidated.reset_index()[consolidated.Date > start][cols]
    print("Saving master file")
    all_data.to_csv(file_path + '/Master_encoded.csv',index=False)
    print("Created updated Master encoded file")
