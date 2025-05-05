import pandas as pd
import numpy as np

# Error and Predicting Functions

def mape(true,pred,availability = 1):
    e = 0
    try:
        if len(availability)>1:
            if (availability.sum()!=0):
                for i in range(0,len(true)):
                    e = e + (availability.iloc[i] * abs((pred.iloc[i]-true.iloc[i])/true.iloc[i]))
                return e/availability.sum()
            else:
                #print("No true value available")
                return 0
    except:
            for i in range(0,len(true)):
                e = e + (abs((pred.iloc[i]-true.iloc[i])/true.iloc[i]))
            return e/len(true)

def MAPE_per_day(m1, pred,avail = False):                    # m1 is entire df of m1 values with availble tag, pred is df of list of forecast predictions for that day for a particular market
    mape_vals = []
    preds = pred.copy()
    if (type(preds["Predictions"].iloc[0])!=list):
        preds["Predictions"] = preds["Predictions"].apply(lambda x : x.replace('[','')).apply(lambda x : x.replace(']','')).apply(lambda x : x.split(", "))

    for i in range(0,len(preds["Predictions"].iloc[0])):
        preds["pred_{}".format(i+1)] = preds["Predictions"].apply(lambda x : float(x[i]))

    for i in range(0,len(preds["Predictions"].iloc[0])):
        m1['true_{}'.format(i+1)] = m1['Modal Price (Rs./Quintal)'].shift(-i)
        m1['avail_{}'.format(i+1)] = m1['Available'].shift(-i)

    if (avail):
        for i in range(0,len(preds["Predictions"].iloc[0])):
            if i!=0:
                mape_vals.append(mape(m1['true_{}'.format(i+1)][:-i], preds["pred_{}".format(i+1)][:-i],m1["avail_{}".format(i+1)][:-i]))

            else:
                mape_vals.append(mape(m1['true_{}'.format(i+1)], preds["pred_{}".format(i+1)],m1["avail_{}".format(i+1)]))
    else:
        for i in range(0,len(preds["Predictions"].iloc[0])):
            if i!=0:
                mape_vals.append(mape(m1['true_{}'.format(i+1)][:-i], preds["pred_{}".format(i+1)][:-i]))
            else:
                mape_vals.append(mape(m1['true_{}'.format(i+1)], preds["pred_{}".format(i+1)]))
    return mape_vals

def Market_predictions(market,model,no_days=14):
    X_test1 = market
    rows = market.shape[0]                                            # Number days in test set for that market
    pred1 = []
    iters = no_days
    model_feat = model.feature_names_
    for i in range(rows):
        X_test_inter = X_test1.iloc[[i]]                              # Day by day slice
        prediction = []                                               # Resetting predictions for new day

        for j in range(iters):

            X_test_inter['3D_avg'] = X_test_inter[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
            X_test_inter['7D_avg'] = X_test_inter[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
            X_test_inter['3D_SD'] = X_test_inter[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
            X_test_inter['7D_SD'] = X_test_inter[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)

            X_test_final = X_test_inter[model_feat]
            pred_cat = model.predict(X_test_final)                  # Prediction for the current slice
            prediction.append(pred_cat[0])                          # Appending to the 14day prediction chain for that day

            X_test_inter[base_cols] = np.column_stack([pred_cat,X_test_inter[base_cols].values[:,:-1]])       # Updating next slice with forecasted values
        pred1.append(prediction)
    return pred1

def MAPE_calculator(State,District,Market,Comm,df,Available):
    MAPEs = []
    r = df[(df['State_Label'] == State) &
      (df['District_Label'] == District) &
      (df['Market_Label'] == Market) &
      (df['Comm_Label'] == Comm)]
    if (Available):
        for i in range(1,15):
            e = mape(r['True_{}'.format(i)], r['Pred_{}'.format(i)],r['Avail_{}'.format(i)])*100
            #print("MAPE for Day {} : %.2f".format(i) % e)
            if (e < 0):
                MAPEs.append('No available true value')
            else:
                MAPEs.append(e)
        return(MAPEs)
    else:
        for i in range(1,15):
            e = mape(r['True_{}'.format(i)], r['Pred_{}'.format(i)])*100
            #print("MAPE for Day {} : %.2f".format(i) % e)
            MAPEs.append(e)
        return(MAPEs)

def moving_avg(V):
    V['3D_avg'] = V[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
    V['7D_avg'] = V[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
    V['3D_SD'] = V[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
    V['7D_SD'] = V[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
    return V

def stack(V,features,new_feat):
    V[features] = np.column_stack([new_feat,V[features].values[:,:-1]])
    return V

def Data_merge(file_path, commodities, dict_state, dict_market):
    old_df = pd.read_csv(file_path + '/Old.csv')   				                # Reading old file
    consolidated  = pd.DataFrame()								# Empty dataframe to create encoded database
    for var in commodities:
        item = pd.read_csv(file_path + '/{}_price.csv'.format(var))
        item['Date'] = pd.to_datetime(item['Reported Date'])
        item = item.sort_values(by='Date',ascending=True)
        item['year'] = pd.DatetimeIndex(item['Date']).year
        item['month'] = pd.DatetimeIndex(item['Date']).month
        item['Monthly Analysis'] = pd.DatetimeIndex(item.Date).to_period("M")
        item = item[item['State Name'].isin([x for x in dict_state])]
        item = item[item['Market Name'].isin([x for x in dict_market])]
        item['Commodity']= var
        consolidated  = pd.concat([consolidated,item])

    g = {'Arrivals (Tonnes)':'sum',
         'Modal Price (Rs./Quintal)': 'mean'
        }

    variables = ['State Name','District Name','Market Name','Commodity']
    consolidated=consolidated.groupby(['State Name','District Name','Market Name','Commodity','Date']).agg(g).reset_index()
    consolidated=consolidated.reindex(columns =["Date", "State Name","District Name","Market Name",'Commodity',"Arrivals (Tonnes)","Modal Price (Rs./Quintal)"])
    consolidated = consolidated[consolidated['Date']>'2021-09-07']
    cols = consolidated.columns
    old_df.Date = pd.to_datetime(old_df.Date)
    old_df = old_df[cols]

    consolidated = pd.concat([old_df,consolidated])

    consolidated['Date'] = pd.to_datetime(consolidated['Date'], infer_datetime_format = True)

    USD_df = pd.read_csv(file_path + '/USDINR.csv')
    Brent_df = pd.read_csv(file_path + '/Brent_csv.csv')

    USD_df.columns = ['Date' , 'USDtoINR']
    Brent_df.columns = ['Date', 'BrentOil_Price']

    USD_df['USDtoINR'].iloc[list(USD_df['USDtoINR'] == '-')] = np.nan
    USD_df['USDtoINR'] = USD_df['USDtoINR'].apply(lambda x : np.float64(x))

    Brent_df['BrentOil_Price'].iloc[list(Brent_df['BrentOil_Price'] == '-')] = np.nan
    Brent_df['BrentOil_Price'] = Brent_df['BrentOil_Price'].apply(lambda x : np.float64(x))

    USD_df['Date'] = pd.to_datetime(USD_df['Date'], format = '%Y-%m-%d')
    Brent_df['Date'] = pd.to_datetime(Brent_df['Date'], format = '%Y-%m-%d')

    date = max(consolidated.Date)
    min_date = min(consolidated.Date)
    idx = pd.date_range(min_date,date)  							#Index for all days till lastest scraped date

    consolidated = consolidated.set_index('Date').groupby(variables).apply(pd.DataFrame.reindex,idx,fill_value=np.nan).drop(variables,1).reset_index().rename(columns={'level_4':'Date'})
    consolidated = pd.merge(consolidated,USD_df,on = 'Date', how = 'left')
    consolidated = pd.merge(consolidated,Brent_df,on = 'Date', how = 'left')

    var_list1 = ['State Name','Commodity','Date']                               # for State Roll
    var_list2 = ['State Name','District Name','Commodity','Date']               # for District Roll

    g = {'Modal Price (Rs./Quintal)':'median',
        }

    consolidated = consolidated.reset_index(drop=True).set_index(var_list1)
    consolidated['State_Roll'] = consolidated.groupby(level=[0,1,2]).agg(g)
    consolidated = consolidated.reset_index()

    consolidated = consolidated.reset_index(drop=True).set_index(var_list2)
    consolidated['District_Roll'] = consolidated.groupby(level=[0,1,2,3]).agg(g)
    consolidated = consolidated.reset_index()

    consolidated['Date']=pd.to_datetime(consolidated['Date'], format = '%d-%m-%Y')
    order_cols = ['Date','State Name','District Name','Market Name','Commodity','Arrivals (Tonnes)','Modal Price (Rs./Quintal)','USDtoINR','BrentOil_Price', 'State_Roll', 'District_Roll']
    consolidated[order_cols]
    var_list = ['State Name', 'District Name', 'Market Name','Commodity','Date']

    consolidated['Available'] = (1*~(consolidated['Modal Price (Rs./Quintal)'].isna()))
    consolidated = consolidated.set_index(var_list)
    consolidated['Availability'] = consolidated.groupby(level=[0,1,2,3]).count()['Arrivals (Tonnes)']/consolidated.groupby(level=[0,1,2,3]).count()['Available']
    consolidated = consolidated.groupby(level=[0,1,2,3])['Modal Price (Rs./Quintal)','Arrivals (Tonnes)','USDtoINR','BrentOil_Price', 'State_Roll', 'District_Roll','Availability','Available'].apply(lambda x: x.interpolate(method='linear',limit_direction='both'))

    consolidated['Last_Day_Price'] = consolidated.groupby(level=[0,1,2,3])['Modal Price (Rs./Quintal)'].shift(1)
    for i in range(2,8):
        consolidated['Last_{}D_Price'.format(i)] = consolidated.groupby(level=[0,1,2,3])['Modal Price (Rs./Quintal)'].shift(i)

    for i in range(1,8):
        consolidated['Available_{}D_Price'.format(i)] = consolidated.groupby(level=[0,1,2,3])['Available'].shift(i)

    for i in range(1,15):
        consolidated['USDINR_{}D'.format(i)] = consolidated.groupby(level=[0,1,2,3])['USDtoINR'].shift(i)
        consolidated['Brent_{}D'.format(i)] = consolidated.groupby(level=[0,1,2,3])['BrentOil_Price'].shift(i)

    consolidated = consolidated.dropna().reset_index()
    consolidated["week"] = [x.week for x in consolidated["Date"]]
    consolidated["day"] = [x.weekday() for x in consolidated["Date"]]
    consolidated["month"] = [x.month for x in consolidated["Date"]]
    consolidated['USDtoINR_lag'] = consolidated['USDINR_14D']
    consolidated['BrentOil_Price_lag'] = consolidated['Brent_14D']
    consolidated['Availability_bit'] = consolidated[['Available_1D_Price', 'Available_2D_Price', 'Available_3D_Price',
           'Available_4D_Price', 'Available_5D_Price', 'Available_6D_Price', 'Available_7D_Price']].mean(axis=1)

    return consolidated

def MAPE_calculator(State,District,Market,Comm,df,Available):
    MAPEs = []
    r = df[(df['State_Label'] == State) &
    (df['District_Label'] == District) &
    (df['Market_Label'] == Market) &
    (df['Comm_Label'] == Comm)]
    if (Available):
        for i in range(1,15):
            e = mape(r['True_{}'.format(i)], r['Pred_{}'.format(i)],r['Avail_{}'.format(i)])*100
            #print("MAPE for Day {} : %.2f".format(i) % e)
            if (e < 0):
                MAPEs.append('No available true value')
            else:
                MAPEs.append(e)
        return(MAPEs)
    else:
        for i in range(1,15):
            e = mape(r['True_{}'.format(i)], r['Pred_{}'.format(i)])*100
            print("MAPE for Day {} : %.2f".format(i) % e)
            MAPEs.append(e)
        return(MAPEs)
