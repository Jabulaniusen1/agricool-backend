import sys
sys.path.append('/Retraining-module/data/')
from data.common import mape, MAPE_per_day, Data_merge

import pandas as pd
import numpy as np
from datetime import timedelta
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
from sklearn.preprocessing import LabelEncoder
from catboost import CatBoostRegressor
import pickle
import configparser
from datetime import datetime


# Read from config file

print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), ": In Retraining")
comm = ['Apple', 'Banana', 'Green Chilli', 'Tomato']					#Config file items
config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read('./config.ini')

dict_state = dict(config.items('dict_state'))					#Config file items
dict_commodities = dict(config.items('dict_commodities'))
dict_district = dict(config.items('dict_district'))
dict_market = dict(config.items('dict_market'))
file_path = dict(config.items('paths'))['data']
model_path = dict(config.items('paths'))['model']

# Read archived data

all_data_filled = Data_merge(file_path, comm, dict_state, dict_market)

# Label Encoding & Dictionary Updation

#label encoding the three categorical features

le_state = LabelEncoder()
le_district = LabelEncoder()
le_market = LabelEncoder()
le_commo = LabelEncoder()

le_state_train = le_state.fit(all_data_filled['State Name'])
le_district_train = le_district.fit(all_data_filled['District Name'])
le_market_train = le_market.fit(all_data_filled['Market Name'])
le_commo_train = le_commo.fit(all_data_filled['Commodity'])

all_data_filled['State_Label'] = le_state_train.transform(all_data_filled['State Name'])
all_data_filled['District_Label'] = le_district_train.transform(all_data_filled['District Name'])
all_data_filled['Market_Label'] = le_market_train.transform(all_data_filled['Market Name'])
all_data_filled['Comm_Label'] = le_commo_train.transform(all_data_filled['Commodity'])

#mapping_state = dict(zip(le_state.classes_, range(len(le_state.classes_))))
#mapping_district = dict(zip(le_district.classes_, range(len(le_district.classes_))))
#mapping_market = dict(zip(le_market.classes_, range(len(le_market.classes_))))
#mapping_comm = dict(zip(le_commo.classes_, range(len(le_commo.classes_))))

# Check if updation of the config file is requried

cols = ['Date','State_Label','District_Label','Market_Label','Comm_Label','Arrivals (Tonnes)','Modal Price (Rs./Quintal)',
'Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price',
'week','day','month', 'USDtoINR','BrentOil_Price','State_Roll', 'District_Roll','Availability','Available',
'Available_1D_Price', 'Available_2D_Price', 'Available_3D_Price', 'Available_4D_Price', 'Available_5D_Price', 'Available_6D_Price', 'Available_7D_Price',
'USDINR_1D', 'Brent_1D', 'USDINR_2D', 'Brent_2D', 'USDINR_3D', 'Brent_3D', 'USDINR_4D', 'Brent_4D', 'USDINR_5D', 'Brent_5D', 'USDINR_6D', 'Brent_6D', 'USDINR_7D', 'Brent_7D',
'USDINR_8D', 'Brent_8D', 'USDINR_9D', 'Brent_9D', 'USDINR_10D', 'Brent_10D', 'USDINR_11D', 'Brent_11D', 'USDINR_12D', 'Brent_12D', 'USDINR_13D', 'Brent_13D', 'USDINR_14D', 'Brent_14D',
'USDtoINR_lag', 'BrentOil_Price_lag', 'Availability_bit']

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
order = location_features + base_cols + time_features + price_features + USD_lagged_feat + Brent_lagged_feat
final_feat = location_features + time_features + derived_features + price_features

all_data_filled = all_data_filled[cols]


# Retraining
# Defining the start and end period for Training and Test set

start = max(all_data_filled['Date']) - timedelta(1095)           # 3 Years back
end = max(all_data_filled['Date']) - timedelta(200)              # 0.5 Year Back

# Train test split

X_train = all_data_filled[(all_data_filled['Date']>start) & (all_data_filled['Date']<=end)][order]
y_train = all_data_filled[(all_data_filled['Date']>start) & (all_data_filled['Date']<=end)][target]
X_train['3D_avg'] = X_train[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
X_train['7D_avg'] = X_train[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
X_train['3D_SD'] = X_train[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
X_train['7D_SD'] = X_train[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
X_train_final = X_train[final_feat]


X_test = all_data_filled[(all_data_filled['Date']>end)][order + ['Available','Availability','Date']]
y_test = all_data_filled[(all_data_filled['Date']>end)][target + location_features + ['Available','Availability','Date']]

# Selected model - Catboost

model_new = CatBoostRegressor(depth=6, l2_leaf_reg= 3, learning_rate = 0.1, n_estimators = 300)
model_new.fit(X_train_final,y_train, verbose = False)                                 # Training new model

model = pickle.load(open(model_path,'rb'))
old_model_feat = model.feature_names_
print("Old Model features :",model.feature_names_)
print("New Model features :", model_new.feature_names_)


# New Model Predictions

print("Forecasting using new model")
V = X_test.copy()
for j in range(1,15):
    V['3D_avg'] = V[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
    V['7D_avg'] = V[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
    V['3D_SD'] = V[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
    V['7D_SD'] = V[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)

    pred_cat = model_new.predict(V[final_feat])

    V['Pred {}'.format(j)] = pred_cat

    V[base_cols] = np.column_stack([pred_cat,V[base_cols].values[:,:-1]])
    V[USD_lagged_feat] = np.column_stack([V['USDINR_14D'],V[USD_lagged_feat].values[:,:-1]])
    V['USDtoINR_lag'] = V['USDINR_14D']
    V[Brent_lagged_feat] = np.column_stack([V['Brent_14D'],V[Brent_lagged_feat].values[:,:-1]])
    V['BrentOil_Price_lag'] = V['Brent_14D']
V['Pred'] = V[['Pred {}'.format(i) for i in range(1,15)]].values.tolist()
dates = V["Date"]
leState = V["State_Label"]
leDistrict = V["District_Label"]
leMarket = V["Market_Label"]
leComm = V["Comm_Label"]
dict = {'Date': dates, 'Predictions': V['Pred'], 'State_Label' : leState, 'District_Label' : leDistrict, 'Market_Label' : leMarket,'Comm_Label' : leComm}
new_pred = pd.DataFrame(dict)

# New Prediction Errors

new_prediction_df = [d for _, d in new_pred.groupby(['State_Label','District_Label','Market_Label','Comm_Label'],sort=False)]

print("Calculating error using new model")
leState = []
leDistrict = []
leMarket = []
leComm = []
mapes = []

for i in range(0,len(new_prediction_df)):
    if (i%100 ==0):
        print("Calculating error for Market no :",i)
    pv = new_prediction_df[i]
    tv = y_test[(y_test["State_Label"] == pv['State_Label'].iloc[0]) &
            (y_test["District_Label"] == pv['District_Label'].iloc[0]) &
            (y_test["Market_Label"] == pv['Market_Label'].iloc[0]) &
            (y_test["Comm_Label"] == pv['Comm_Label'].iloc[0])]

    leState.append(pv["State_Label"].iloc[0])
    leDistrict.append(pv["District_Label"].iloc[0])
    leMarket.append(pv["Market_Label"].iloc[0])
    leComm.append(pv["Comm_Label"].iloc[0])
    mapes.append(MAPE_per_day(tv,pv,avail = False))

new_mapes_markets = pd.DataFrame({'State' : leState,
                'District' : leDistrict,
                'Market' : leMarket,
                'Comm' : leComm,
                'MAPE' : mapes})

for i in range(0,len(new_mapes_markets['MAPE'].iloc[0])):
    new_mapes_markets['MAPE_Day_{}'.format(i+1)] = new_mapes_markets['MAPE'].apply(lambda x : x[i]*100)


# Old Model Predictions

print("Forecasting using old model")
V = X_test.copy()
for j in range(1,15):
    V['3D_avg'] = V[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
    V['7D_avg'] = V[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].mean(axis=1)
    V['3D_SD'] = V[['Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)
    V['7D_SD'] = V[['Last_Day_Price','Last_2D_Price','Last_3D_Price','Last_4D_Price','Last_5D_Price','Last_6D_Price','Last_7D_Price']].std(axis=1)

    pred_cat = model.predict(V[old_model_feat])

    V['Pred {}'.format(j)] = pred_cat

    V[base_cols] = np.column_stack([pred_cat,V[base_cols].values[:,:-1]])
    V[USD_lagged_feat] = np.column_stack([V['USDINR_14D'],V[USD_lagged_feat].values[:,:-1]])
    V['USDtoINR_lag'] = V['USDINR_14D']
    V[Brent_lagged_feat] = np.column_stack([V['Brent_14D'],V[Brent_lagged_feat].values[:,:-1]])
    V['BrentOil_Price_lag'] = V['Brent_14D']

V['Pred'] = V[['Pred {}'.format(i) for i in range(1,15)]].values.tolist()
dates = V["Date"]
leState = V["State_Label"]
leDistrict = V["District_Label"]
leMarket = V["Market_Label"]
leComm = V["Comm_Label"]
dict = {'Date': dates, 'Predictions': V['Pred'], 'State_Label' : leState, 'District_Label' : leDistrict, 'Market_Label' : leMarket,'Comm_Label' : leComm}
old_pred = pd.DataFrame(dict)

old_prediction_df = [d for _, d in old_pred.groupby(['State_Label','District_Label','Market_Label','Comm_Label'],sort=False)]


# Old Prediction Errors

print("Calculating error using old model")
leState = []
leDistrict = []
leMarket = []
leComm = []
mapes = []

for i in range(0,len(old_prediction_df)):
    if (i%100 ==0):
        print("Calculating error for Market no :",i)
    pv = old_prediction_df[i]
    tv = y_test[(y_test["State_Label"] == pv['State_Label'].iloc[0]) &
            (y_test["District_Label"] == pv['District_Label'].iloc[0]) &
            (y_test["Market_Label"] == pv['Market_Label'].iloc[0]) &
            (y_test["Comm_Label"] == pv['Comm_Label'].iloc[0])]

    leState.append(pv["State_Label"].iloc[0])
    leDistrict.append(pv["District_Label"].iloc[0])
    leMarket.append(pv["Market_Label"].iloc[0])
    leComm.append(pv["Comm_Label"].iloc[0])
    mapes.append(MAPE_per_day(tv,pv,avail = False))

old_mapes_markets = pd.DataFrame({'State' : leState,
                'District' : leDistrict,
                'Market' : leMarket,
                'Comm' : leComm,
                'MAPE' : mapes})

for i in range(0,len(old_mapes_markets['MAPE'].iloc[0])):
    old_mapes_markets['MAPE_Day_{}'.format(i+1)] = old_mapes_markets['MAPE'].apply(lambda x : x[i]*100)

old_df = pd.DataFrame(old_mapes_markets.drop(['State','District', 'Market','Comm'],axis = 1 ).mean())
old_df.columns = ["MAPE"]
old_df = pd.concat([old_df, pd.DataFrame({"MAPE" : old_df['MAPE'].mean()},index = ['Total Average'])])

new_df = pd.DataFrame(new_mapes_markets.drop(['State','District', 'Market','Comm'],axis = 1 ).mean())
new_df.columns = ["MAPE"]
new_df = pd.concat([new_df, pd.DataFrame({"MAPE" : new_df['MAPE'].mean()},index = ['Total Average'])])

# Check for better model based on predictions

overall_old = []
for i in range(1,15):
    overall_old.append(old_mapes_markets['MAPE_Day_{}'.format(i)].mean())
    print("Error Day {}: ".format(i),old_mapes_markets['MAPE_Day_{}'.format(i)].mean())
print("Overall mean error: ",np.mean(overall_old))

overall_new = []
for i in range(1,15):
    overall_new.append(new_mapes_markets['MAPE_Day_{}'.format(i)].mean())
    print("Error Day {}: ".format(i),new_mapes_markets['MAPE_Day_{}'.format(i)].mean())
print("Overall mean error: ",np.mean(overall_new))

if (np.mean(overall_new) < np.mean(overall_old)):
    print('new model is better')
    pickle.dump(model_new, open(model_path, 'wb'))
else:
    print('old is better')
