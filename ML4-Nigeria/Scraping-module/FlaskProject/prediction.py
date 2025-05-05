import warnings
import configparser
import pickle
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_caching import Cache
import hashlib
import json
import bz2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
pd.set_option('mode.chained_assignment', None)

app = Flask(__name__)
app.config.from_prefixed_env()

config = configparser.RawConfigParser()
config.optionxform = lambda option: option
config.read('./config.ini')

# Config file items
dict_state = dict(config.items('dict_state'))
dict_comm = dict(config.items('dict_comm'))
model_path = dict(config.items('paths'))['model']
data_path = dict(config.items('paths'))['master_data_encoded']

# Read the master dataframe
master_df = pd.read_csv(data_path)

# Load the serialized model from file system
logging.info("Loading Model")
with bz2.BZ2File(model_path, 'rb') as file:
    model = pickle.load(file)
    model.check_input = False

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
    req = request.get_json()
    if not req:
        return jsonify({'error': 'Missing data'}), 400

    state_name = req.get('state')
    commodity_name = req.get('commodity')

    if not state_name or not commodity_name:
        return jsonify({'error': 'State or commodity missing from request'}), 400

    state_map = int(dict_state.get(state_name, -1))
    commodity_map = int(dict_comm.get(commodity_name, -1))

    if state_map == -1 or commodity_map == -1:
        return jsonify({'error': 'Invalid state or commodity'}), 400

    df_slice = master_df.loc[(master_df['st_label'] == state_map) & (master_df['comm_label'] == commodity_map)]

    model_feat = ['Last_Month_Price', 'state_roll', 'USDtoNaira', 'CPI', 'Last_5M_Price']
    lagged_cols = ['Last_Month_Price', 'Last_2M_Price', 'Last_3M_Price', 'Last_4M_Price', 'Last_5M_Price']

    try:
        X_test_inter = df_slice.iloc[[-1]]
    except IndexError:
        logging.error(f"Invalid state-commodity combination for state: {state_name}, commodity: {commodity_name}")
        return jsonify({'Request': {'State': state_name, 'commodity': commodity_name},
                        'Result': "Not a valid state-commodity combination"}), 400

    predictions_horizon = 8
    lag = 1
    iters = predictions_horizon + lag

    Dates = []
    X_test_inter['Date'] = pd.to_datetime(X_test_inter['Date'])
    for i in range(iters):
        current_date = X_test_inter['Date'].iloc[0] + relativedelta(months=+(i + 1))
        Dates.append(current_date.strftime("%b, %Y"))

    predictions = []
    for j in range(iters):
        X_test_final = X_test_inter[model_feat]
        pred = model.predict(X_test_final)
        predictions.append(pred[0])
        X_test_inter[lagged_cols] = np.column_stack([pred[0], X_test_inter[lagged_cols].values[:, :-1]])

    return jsonify({
        'Predictions': predictions[lag:],
        'Dates': Dates[lag:],
        'Request': {'State': state_name, 'Commodity': commodity_name},
        'Result': "Done"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0')
