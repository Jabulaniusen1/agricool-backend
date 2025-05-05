import pandas as pd
from air.utils.db_connector import DBConnector

class ImpactReporter:
    """Class to generate user reports
    Connects to the DB to fetch Coldtivate DB and then combines as well
    as formats them to return meaningful reports as Pandas DataFrames
    """

    def __init__(self):
        self.conn = DBConnector().get_connection()

    def _calc_days_in_storage(self, df):
        """ Calculate days in storage based on check-in and check-out dates
        Takes a DataFrame as input and adds a column called 'Days in Storage'
        in place to the DataFrame based on time difference between the check-in
        and check-out dates

        Args:
            df (pd.DataFram): A DataFrame that must contain the datetime
                              columns 'Check-in Date' and 'Check-out Date'
        """
        df['cout_date'] = df['Check-out Date'].dt.normalize()
        df['cin_date'] = df['Check-in Date'].dt.normalize()
        df['Days in Storage'] = (
                                    df['cout_date'] - df['cin_date']
                                ).dt.days

    def _format_dt_column(self, df, column):
        """ Formats a given datetime column of a DataFrame
        Formats the datetime object of a given column in a dataframe
        to remove the milliseconds and make it more readable. Does it inplace,
        so the column type gets converted from datetime to string.

        Args:
            df (pd.DataFrame): A pandas DataFrame with a datetime column
                               to be formatted
            column (str): Column name of the datetime column to be formatted
        """
        if len(df) == 0:
            # No data to format
            return

        df[column] = df[column].dt.tz_localize(None)
        df[column] = df[column].dt.strftime('%Y-%m-%d %H:%M:%S')

    def _get_room_df(self, company_id, cooling_unit_ids = ''):
        """ Fetch storage location information from DB for company_id
        Makes an SQL query to the database to fetch required location
        information for the given company id

        Args:
            company_id (int): Id of the corresponding company
            cooling_unit_ids (str): Comma separated list of cooling unit
                                    ids to filter the data on

        Returns:
            room_df (pd.DataFrame): DataFrame containing storage location information
                                    for the given company
        """

        # Cooling rooms - note that some could be deleted!
        # there is an issue with extracting sl.date_last_modified and sl.date_creation, probably that they are called the same as sc.date_creation and date_last modified. Anyway we don't need them, so excluding them for now
        room_sql = """
            select sc.*, sl.name as "Location Name", sl.state, sl.city, sl.zip_code,
                  sl.deleted as deleted_location
            from storage_coolingunit sc
            join storage_location sl
                on sc.location_id = sl.id
            where sl.company_id = {c_id}
            """.format(c_id=company_id)

        if cooling_unit_ids:
            room_sql += " and sc.id in ({ids})".format(ids = cooling_unit_ids)

        room_sql += " order by sc.deleted, sc.id;"

        room_df = pd.read_sql(room_sql, self.conn, coerce_float=False)
        room_df.rename(columns={'name': 'Cooling Unit Name'}, inplace=True)

        return room_df

    def _get_checkin_df(self, company_id, room_df, start_date = None, end_date = None):
        """ Fetch check in information from DB for company_id
        Makes an SQL query to the database to fetch required check-in
        information for the given company id. Start date and/or End date can
        be provided to filter the data for that particular period

        Args:
            company_id (int): Id of the corresponding company
            start_date (str): String of format "YYYY-MM-DD" to filter crates on
            end_date (str): String of format "YYYY-MM-DD" to filter crates on

        Returns:
            checkin_df (pd.DataFrame): DataFrame containing check-in information
                                       for the given company
        """
        checkin_sql = """
            select  sc.id as "Crate Id",
                    sc.cooling_unit_id as "Cooling Unit Id",
                    om.code as "Check-in Code",
                    om.date as "Check-in Date",
                    om.id as movement_id,
                    om.operator_id,
                    uf.id as farmer_id,
                    uf.user_id as farmer_id_in_user_user,
                    sp.checkin_id,
                    sp.crop_id,
                    scrop.name as "Crop Name",
                    scp.checkout_id as check_out_id,
                    sc.remaining_shelf_life,
                    sc.modified_dt,
                    sc.price_per_crate_per_pricing_type as "Price per Crate",
                    sc.currency as "Currency",
                    sc.weight as "Weight"
            from operation_movement om
            join user_operator uo
                on om.operator_id = uo.id
            join operation_checkin oc
                on om.id = oc.movement_id
            join storage_produce sp
                on oc.id = sp.checkin_id
            join storage_crate sc
                on sp.id = sc.produce_id
            join storage_crop scrop
                on sp.crop_id = scrop.id
            join user_user uu on (oc.owned_by_user_id = uu.id)
			join user_farmer uf on (uf.user_id = uu.id)
			left join (select  sc.id as crate_id,
                max(om.date) as max_checkout_date
                from storage_crate sc
                LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id)
                left join operation_checkout cko on(cko.id = scp.checkout_id)
                left outer join operation_movement om on (cko.movement_id = om.id)
                where sc.cmp_fully_checked_out = true
                group by sc.id) mc on (mc.crate_id = sc.id and mc.max_checkout_date = om.date)
            LEFT JOIN storage_cratepartialcheckout scp  on (mc.crate_id = scp.crate_id)
            where uo.company_id = {c_id}
            """.format(c_id=company_id, start_date=start_date)

        if start_date:
            checkin_sql += """ and CAST(om."date" AS DATE) >= '{start_date}' """.format(start_date=start_date)

        if end_date:
            checkin_sql += """ and CAST(om."date" AS DATE) <= '{end_date}' """.format(end_date=end_date)

        checkin_sql += " order by om.date, sc.id;"

        checkin_df = pd.read_sql(checkin_sql, self.conn, coerce_float=False)
        checkin_df = pd.merge(checkin_df, room_df[['Cooling Unit Name', 'Location Name', 'id']],
                              left_on='Cooling Unit Id', right_on='id')

        return checkin_df

    def _get_cuser_df(self, company_id):
        """ Fetch cooling user information from DB for company_id
        Makes an SQL query to the database to fetch required cooling
        user information for the given company id.

        Args:
            company_id (int): Id of the corresponding company

        Returns:
            cuser (pd.DataFrame): DataFrame containing check-in information
                                       for the given company
        """
        cuser_sql = """
            select first_name as "First Name",
                last_name as "Last Name",
                phone as "Phone Number",
                gender as "Gender",
                parent_name as "Parent Name",
                date_joined as "Date Joined",
                uu.id as my_user_id, uu.is_active
            from user_farmer uf
            join user_farmer_companies uc
                on uc.farmer_id = uf.id
            join user_user uu
                on uf.user_id = uu.id
            where first_name != 'User without a phone'
                and company_id = {c_id}
            order by uu.id;
            """.format(c_id=company_id)

        cuser_df = pd.read_sql(cuser_sql, self.conn, coerce_float=False)
        return cuser_df

    def _get_checkout_df(self, company_id, start_date = None, end_date = None):
        """ Fetch check out information from DB for company_id
        Makes an SQL query to the database to fetch required check-out
        information for the given company id. Start date and/or End date can
        be provided to filter the data for that particular period

        Args:
            company_id (int): Id of the corresponding company
            start_date (str): String of format "YYYY-MM-DD" to filter crates on
            end_date (str): String of format "YYYY-MM-DD" to filter crates on

        Returns:
            checkout_df (pd.DataFrame): DataFrame containing check-out information
                                       for the given company
        """
        # NOTE That this is more advanced that checkout_sql for survey calculation. It retrieves details needed for revenue analysis screen
        checkout_sql = """
		select  sc.id as "Crate Id",
                    scp.checkout_id as checkout_id,
                    om_cko.code as "Check-out Code",
                    om_cko.date as "Check-out Date",
                    sp.crop_id,
                    scrop.name as "Crop Name",
                    cko.cmp_total_amount as price_for_whole_checkout,
                    cko.currency as "Currency",
                    cko.payment_method as "Payment Type",
                    cko.cmp_total_cooling_fees_amount as old_price,
                    cko.discount_amount as price_discount,
                    om_cko.operator_id as checkout_operator,
                    sc.cooling_unit_id as "Cooling Unit Id",
                    sc.weight as "Weight",
                    uf.id as farmer_id,
                    uf.user_id as farmer_id_in_user_user,
                    om_cin.date as "Check-in Date"
            from storage_crate sc
            JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id)
            join operation_checkout cko
                on (scp.checkout_id = cko.id)
            join operation_movement om_cko
                on (cko.movement_id = om_cko.id)
            join user_operator uo
                on (uo.id = om_cko.operator_id)
            join storage_produce sp
                on (sc.produce_id = sp.id)
            join storage_crop scrop
                on sp.crop_id = scrop.id
            join operation_checkin oc
                on sp.checkin_id = oc.id
            join user_user uu on (oc.owned_by_user_id = uu.id)
			join user_farmer uf on (uf.user_id = uu.id)
            join operation_movement om_cin
                on oc.movement_id = om_cin.id
            inner join (select  sc.id as crate_id,
                max(om.date) as max_checkout_date
                from storage_crate sc
                LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id)
                left join operation_checkout cko on(cko.id = scp.checkout_id)
                left outer join operation_movement om on (cko.movement_id = om.id)
                where sc.cmp_fully_checked_out = true
                group by sc.id) mc on (mc.crate_id = sc.id and mc.max_checkout_date = om_cko.date)
            where uo.company_id = {c_id}
            """.format(c_id=company_id)

        if start_date:
            checkout_sql += """ and CAST(om_cko."date" AS DATE) >= '{start_date}' """.format(start_date=start_date)

        if end_date:
            checkout_sql += """ and CAST(om_cko."date" AS DATE) <= '{end_date}' """.format(end_date=end_date)

        checkout_sql += " order by om_cko.date;"

        checkout_df = pd.read_sql(checkout_sql, self.conn, coerce_float=False)
        return checkout_df

    def get_cooling_users_report(self, company_id, only_active):
        cuser_df = self._get_cuser_df(company_id)
        room_df = self._get_room_df(company_id)
        checkin_df = self._get_checkin_df(company_id, room_df)

        # Get number of crates checked in per user
        df_user_checkedin_crate = checkin_df.groupby(['farmer_id_in_user_user'])['Crate Id']\
                                            .count()\
                                            .to_frame()\
                                            .reset_index()
        cuser_df = pd.merge(cuser_df, df_user_checkedin_crate, how='left',
                            left_on='my_user_id', right_on='farmer_id_in_user_user')
        cuser_df.rename(columns={'Crate Id': 'Total Number of Checked-in Crates'}, inplace=True)

        # Get latest check in date per user
        max_checkin_date_df = checkin_df.groupby('farmer_id_in_user_user')['Check-in Date']\
                                        .max()\
                                        .reset_index()
        max_checkin_date_df.rename(columns={'Check-in Date': 'Latest Check In Date'}, inplace=True)
        cuser_df = pd.merge(cuser_df, max_checkin_date_df, how='left',
                            left_on='my_user_id', right_on='farmer_id_in_user_user')

        if only_active:
            cuser_df = cuser_df[cuser_df['is_active'] == True]

        # formate date
        self._format_dt_column(cuser_df, 'Date Joined')
        self._format_dt_column(cuser_df, 'Latest Check In Date')

        required_cols = ['First Name', 'Last Name', 'Phone Number', 'Gender', 'Parent Name',
                        'Date Joined', 'Total Number of Checked-in Crates',
                        'Latest Check In Date']
        cuser_df = cuser_df[required_cols].sort_values(by='Date Joined')

        cuser_df['#'] = range(1, len(cuser_df) + 1)
        cuser_df.set_index('#', inplace=True)

        # Also transform the total number of checked in crates to 0
        cuser_df['Total Number of Checked-in Crates'] = cuser_df['Total Number of Checked-in Crates'].fillna(0)

        return cuser_df

    def get_usage_analysis_report(self, company_id, cooling_unit_ids, start_date, end_date):
        cuser_df = self._get_cuser_df(company_id)
        req_cuser_df = cuser_df[['First Name', 'Last Name', 'Phone Number',
                                 'Gender', 'my_user_id']]

        room_df = self._get_room_df(company_id, cooling_unit_ids)
        checkin_df = self._get_checkin_df(company_id, room_df, start_date, end_date)

        usage_df = pd.merge(checkin_df, req_cuser_df,
                            right_on='my_user_id', left_on='farmer_id_in_user_user')

        # formate date
        self._format_dt_column(usage_df, 'Check-in Date')

        required_cols = ['Crate Id', 'Check-in Code', 'Check-in Date', 'Crop Name', 'Weight',
                         'Price per Crate', 'Currency', 'First Name', 'Last Name',
                         'Phone Number', 'Gender', 'Cooling Unit Name', 'Location Name']
        usage_df = usage_df[required_cols].sort_values(by=['Check-in Date', 'Crate Id'])

        usage_df['#'] = range(1, len(usage_df) + 1)
        usage_df.set_index('#', inplace=True)

        return usage_df

    def get_revenue_analysis_report(self, company_id, cooling_unit_ids, start_date, end_date):
        checkout_df = self._get_checkout_df(company_id, start_date, end_date)
        room_df = self._get_room_df(company_id, cooling_unit_ids)
        checkout_df = pd.merge(checkout_df, room_df[['Cooling Unit Name', 'Location Name', 'id']],
                               left_on='Cooling Unit Id', right_on='id')

        # using this to fix mistake when adding price discount (we have not
        # copied what was in 'price' to 'final price', in case when no discount is there)
        incorrect_cond = (checkout_df.price_for_whole_checkout==0) & (checkout_df.price_discount == 0)
        checkout_df.loc[incorrect_cond, 'price_for_whole_checkout'] = checkout_df.old_price

        # define checkout_price_per_crate and related columns for
        checkout_df['Check-out Price per Crate'] = checkout_df.price_for_whole_checkout / checkout_df.groupby('Check-out Code')['price_for_whole_checkout'].transform(lambda x: x.count())
        checkout_df['Check-out Price per Crate before Discount'] = checkout_df.old_price / checkout_df.groupby('Check-out Code')['old_price'].transform(lambda x: x.count())
        checkout_df['Price Discount per Crate'] = checkout_df.price_discount / checkout_df.groupby('Check-out Code')['price_discount'].transform(lambda x: x.count())

        cuser_df = self._get_cuser_df(company_id)
        req_cuser_df = cuser_df[['First Name', 'Last Name', 'Phone Number', 'Gender', 'my_user_id']]
        revenue_df = pd.merge(checkout_df, req_cuser_df,
                              right_on='my_user_id', left_on='farmer_id_in_user_user')

        # define number of days in storage
        self._calc_days_in_storage(revenue_df)

        # formate date
        self._format_dt_column(revenue_df, 'Check-out Date')

        required_cols = ['Crate Id', 'Check-out Code', 'Check-out Date', 'Crop Name', 'Weight',
                         'Check-out Price per Crate', 'Currency',
                         'Check-out Price per Crate before Discount', 'Price Discount per Crate',
                         'Days in Storage', 'Payment Type', 'First Name', 'Last Name',
                         'Phone Number', 'Gender', 'Cooling Unit Name', 'Location Name']

        revenue_df = revenue_df[required_cols].sort_values(by=['Check-out Date', 'Crate Id'])

        revenue_df['#'] = range(1, len(revenue_df) + 1)
        revenue_df.set_index('#', inplace=True)

        return revenue_df
