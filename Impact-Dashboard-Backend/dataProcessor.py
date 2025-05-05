import pandas as pd
import yfinance as yf


class DataProcessor:
    """
    Class to process data provided by SQL queries
    """

    @staticmethod
    def price(ticker, period="1d", columns=["Close"]):
        """
        Returns a DataFrame of prices for ticker from Yahoo Finance API
        """
        obj = yf.Ticker(ticker)
        return obj.history(period=period)[columns]

    def prices(self, tickers, period="1d", columns=["Close"]):
        """
        Returns a DataFrame of prices for a list of tickers from Yahoo Finance API
        """
        prices = pd.DataFrame()
        for ticker in tickers:
            ticker_prices = self.price(ticker, period, columns)

            if not ticker_prices.dropna().empty:
                prices = pd.concat([prices, ticker_prices], axis=1)
            else:
                print(f"{ticker} has no data!")
        return prices

    @staticmethod
    def revenue_room_computation(
        checkouts: pd.DataFrame, revenue_room: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute the revenue (sum of money collected for each checkout) of the room
        both in the local currency and in USD
        Parameters:
        table:
            DataFrame of create checkouts with the columns 'cooling_unit_id', 'checkout_date', 'checkout_price', 'currency'
        Returns:
            The revenue in the given currency and in USD for each cooling unit room
        """

        pd.set_option("mode.chained_assignment", None)

        # create dictonary of currencies and exchange rates
        rates = {}
        currencies = checkouts["currency"].unique()

        # Scrape the exchange rates for each unique currency
        print("Retrieving exchange rates...\n")
        for currency in currencies:
            if currency != "USD":
                try:
                    ticker = f"{currency}USD=X"
                    curr_to_usd_rate = DataProcessor.price(ticker, period="1d")[
                        "Close"
                    ].iloc[-1]
                except Exception:
                    print(f"Failed to fetch rate for {currency}, setting to 1")
                    curr_to_usd_rate = 1.0
            else:
                curr_to_usd_rate = 1.0
            rates[currency] = 1 * curr_to_usd_rate

        # Convert to USD
        unique_values = checkouts[["currency", "cooling_unit_id"]].drop_duplicates()
        unique_values["usd_exchange_rates"] = unique_values["currency"].map(rates)

        unique_values = unique_values.set_index("cooling_unit_id")
        revenue_room = revenue_room.set_index("cooling_unit_id")

        # Check if all values in revenue_room['revenue_room'] are zero
        if revenue_room["revenue_room"].sum() == 0:
            revenue_room["revenue_room_usd"] = 0.0
        else:
            # Resetting indices before multiplication
            revenue_room = revenue_room.reset_index(drop=False)
            unique_values = unique_values.reset_index(drop=False)

            revenue_room["revenue_room_usd"] = (
                revenue_room["revenue_room"].astype(float)
                * unique_values["usd_exchange_rates"]
            )
        revenue_room.reset_index(inplace=True)

        return revenue_room.fillna(0)

    @staticmethod
    def revenue_comp_computation(revenue_comp: pd.DataFrame) -> pd.DataFrame:
        pd.set_option("mode.chained_assignment", None)

        # create dictonary of currencies and exchange rates
        rates = {}
        currencies = revenue_comp["currency_crate"].unique()

        # Scrape the exchange rates for each unique currency
        print("Retrieving exchange rates...\n")
        for currency in currencies:
            if currency != "USD":
                try:
                    ticker = f"{currency}USD=X"
                    curr_to_usd_rate = DataProcessor.price(ticker, period="1d")[
                        "Close"
                    ].iloc[-1]
                except Exception:
                    print(f"Failed to fetch rate for {currency}, setting to 1")
                    curr_to_usd_rate = 1.0
            else:
                curr_to_usd_rate = 1.0
            rates[currency] = 1 * curr_to_usd_rate

        # Convert to USD
        unique_values = revenue_comp[["currency_crate", "company_id"]].drop_duplicates()
        unique_values["usd_exchange_rates"] = unique_values["currency_crate"].map(rates)

        unique_values = unique_values.set_index("company_id")
        revenue_comp = revenue_comp.set_index("company_id")

        # Resetting indices before multiplication
        revenue_comp = revenue_comp.reset_index(drop=False)
        unique_values = unique_values.reset_index(drop=False)

        revenue_comp["company_total_revenue_usd"] = (
            revenue_comp["company_total_revenue"].astype(float)
            * unique_values["usd_exchange_rates"]
        )
        revenue_comp.reset_index(inplace=True)

        return revenue_comp.fillna(0)
