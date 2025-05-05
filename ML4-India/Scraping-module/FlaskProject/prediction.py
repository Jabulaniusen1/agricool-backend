import sys
sys.path.append('/app/data/')
from data.common import moving_avg, stack, MAPE_calculator

from flask import Flask, request, jsonify
from flask_caching import Cache
import hashlib
import json
import pickle
import pandas as pd
import configparser
import datetime
import warnings
import time
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

app = Flask(__name__)
app.config.from_prefixed_env()

config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read('./config.ini')

#Config file items
dict_state = dict(config.items('dict_state'))
dict_commodities = dict(config.items('dict_commodities'))
dict_district = dict(config.items('dict_district'))
dict_market = dict(config.items('dict_market'))
model_path = dict(config.items('paths'))['model']
file_path = dict(config.items('paths'))['data']
data_path = dict(config.items('paths'))['masterdata']

print("Restarting Model")
model = pickle.load(open(model_path,'rb'))

df = pd.read_csv(data_path)
base_cols =['Last_Day_Price', 'Last_2D_Price', 'Last_3D_Price', 'Last_4D_Price','Last_5D_Price', 'Last_6D_Price', 'Last_7D_Price']
location_features = ['State_Label', 'District_Label', 'Market_Label','Comm_Label', 'Arrivals (Tonnes)']
time_features =['week','day','month']
USD_lagged_feat = ['USDINR_1D', 'USDINR_2D', 'USDINR_3D',
                   'USDINR_4D',  'USDINR_5D', 'USDINR_6D',
                   'USDINR_7D',  'USDINR_8D',  'USDINR_9D',
                   'USDINR_10D', 'USDINR_11D', 'USDINR_12D',
                   'USDINR_13D', 'USDINR_14D']
Brent_lagged_feat = ['Brent_1D',  'Brent_2D', 'Brent_3D',
                    'Brent_4D', 'Brent_5D', 'Brent_6D',
                    'Brent_7D', 'Brent_8D', 'Brent_9D',
                   'Brent_10D', 'Brent_11D', 'Brent_12D',
                    'Brent_13D', 'Brent_14D']
derived_features = ['3D_avg','7D_avg','3D_SD','7D_SD']
target = ['Modal Price (Rs./Quintal)']

### Model features : Lagged USD & Brent + Rollup + Availability
price_features = ['USDtoINR_lag','BrentOil_Price_lag','Availability_bit','State_Roll', 'District_Roll']
order_6 = location_features + base_cols + time_features + price_features + USD_lagged_feat + Brent_lagged_feat

# Setup flask cache
cache = Cache(app)

def make_cache_key():
    data = request.get_json()
    if data:
        key = json.dumps(data, sort_keys=True)
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return key_hash
    return request.full_path

@app.route('/prediction', methods=['POST'])
@cache.cached(timeout=60, key_prefix=make_cache_key)
def predict():
    start_time = time.time()
    req = request.get_json()
    state_map = int(dict_state[req["state"]])
    district_map = int(dict_district[req["district"]])
    market_map = int(dict_market[req["market"]])
    commodity_mapping = int(dict_commodities[req["commodity"]])
    error_with_interpolated_values = int(req["Available_values"]) # Change

    df = pd.read_csv(data_path)

    df_slice = df.loc[(df['State_Label']==state_map) &
                      (df['District_Label']==district_map) &
                      (df['Market_Label']==market_map) &
                      (df['Comm_Label']==commodity_mapping)]
    val = len(df_slice)

    model_features = model.feature_names_

    X_test1 = df_slice.copy()

    try:
        X_dropped = X_test1.iloc[[val-1]]
    except:
        return jsonify({'Request': {'State': req["state"], 'District': req["district"], 'Market': req["market"], 'Commodity': req["commodity"]}, 'Result': "Not a valid state-district-market-commodity combination"})

    iters = 14
    prediction = []

    for i in range(iters):

        X_test_inter = X_dropped.copy()
        X_test_inter = moving_avg(X_test_inter)
        X_test_final = X_test_inter[model_features]

        pred = model.predict(X_test_final)
        prediction.append(pred[0])

        X_test_inter = stack(X_test_inter,base_cols,pred)
        X_test_inter = stack(X_test_inter,USD_lagged_feat,X_test_inter['USDINR_14D'])
        X_test_inter = stack(X_test_inter,Brent_lagged_feat,X_test_inter['Brent_14D'])

        X_test_inter['USDtoINR_lag'] = X_test_inter['USDINR_14D']
        X_test_inter['BrentOil_Price_lag'] = X_test_inter['Brent_14D']
    output = prediction

    # Error Module
    df_slice['Date'] = pd.to_datetime(df_slice['Date'])
    start = max(df_slice['Date']) - datetime.timedelta(75)                    # 2.5 months

    V = df_slice[df_slice['Date']>start].copy()
    for j in range(1,15):
        V = moving_avg(V)

        pred_cat = model.predict(V[model_features])

        V['Pred_{}'.format(j)] = pred_cat
        V = stack(V,base_cols,pred_cat)
        V = stack(V,USD_lagged_feat,V['USDINR_14D'])
        V = stack(V,Brent_lagged_feat,V['Brent_14D'])
        V['USDtoINR_lag'] = V['USDINR_14D']
        V['BrentOil_Price_lag'] = V['Brent_14D']

    V = V.set_index(['State_Label', 'District_Label', 'Market_Label', 'Comm_Label','Date'])
    for i in range(0,14):
        V['True_{}'.format(i+1)] = V.groupby(level=[0,1,2,3])['Modal Price (Rs./Quintal)'].shift(-(i))
        V['Avail_{}'.format(i+1)] = V.groupby(level=[0,1,2,3])['Available'].shift(-(i))

    V = V.reset_index().dropna()


    Mapes = {}
    output = MAPE_calculator(state_map,district_map,market_map,commodity_mapping,V,error_with_interpolated_values)
    availability = V.Availability.iloc[0] *100

    for i in range(0,14):
        Mapes['Day {}'.format(i+1)] = output[i]

    #Error with last available value

    V = df_slice
    last_date_data = V.iloc[-1].Date
    prediction_dates = pd.date_range(last_date_data, (last_date_data + datetime.timedelta(days = 13)).strftime('%d-%b-%Y')).shift(1) # predictions start from the following day to the last available data point date

    try:
        V_last_loc = V[V['Available'] == 1].iloc[[-1]].index[0]                                         # Check for the most recent available value in the master encoded
        pred1 = []

        for j in range(14):
            V_curr = V.loc[[V_last_loc-j]]
            prediction = []
            for k in range(0,j+1):
                V_curr = moving_avg(V_curr)

                V_final = V_curr[model.feature_names_]
                pred_cat = model.predict(V_final)                  # Prediction for the current slice
                prediction.append(pred_cat[0])                          # Appending to the 14day prediction chain for that day

                V_curr = stack(V_curr,base_cols,pred_cat)
                V_curr = stack(V_curr,USD_lagged_feat,V_curr['USDINR_14D'])
                V_curr = stack(V_curr,Brent_lagged_feat,V_curr['Brent_14D'])
                V_curr['USDtoINR_lag'] = V_curr['USDINR_14D']
                V_curr['BrentOil_Price_lag'] = V_curr['Brent_14D']
            pred1.append(prediction[-1])

        target = V.loc[V_last_loc]['Modal Price (Rs./Quintal)']
        last_date = V.loc[V_last_loc]['Date'].strftime("%d-%m-%Y")


        error_percentage = abs(pred1 - target)/target * 100
        end_time = time.time() - start_time
        dict = {'Request': {'State': req["state"], 'District': req["district"], 'Market': req["market"], 'Commodity': req["commodity"]}, 'Dates': list(prediction_dates.strftime("%d-%b-%Y")), 'Predictions': prediction, 'Last Available Error Observed': list(error_percentage), 'Last Available Value': target, 'Last Available Date': last_date, 'Last 2-month Error': output, 'Data Availability': availability, 'Prediction Time': end_time, 'Result': "Done"}
        return jsonify(dict)

    except:
        print("No Available values in the last 6 months for: ", req["state"], req["district"], req["market"], req["commodity"] )
        return jsonify({'Request': {'State': req["state"], 'District': req["district"], 'Market': req["market"], 'Commodity': req["commodity"]} , 'Dates': list(prediction_dates.strftime("%d-%b-%Y")), 'Predictions': prediction, 'Result' : "No real data in the last 6 months, use predictions with caution"})


if __name__ == '__main__':
    app.run(host='0.0.0.0')
