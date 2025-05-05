import configparser
import bz2
import pickle
import warnings
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from sklearn.ensemble import RandomForestRegressor
from typing import List, Tuple

pd.set_option('mode.chained_assignment',None)
warnings.simplefilter(action='ignore', category=FutureWarning)


class RetrainingModule:
    def __init__(self):
        """
        Initialize the RetrainingModule with necessary configurations, data and model parameters
        """
        self.config = configparser.RawConfigParser()
        self.config.optionxform = lambda option: option
        self.config.read('./config.ini')
        self.file_path = dict(self.config.items('paths'))['data']
        self.model_path = dict(self.config.items('paths'))['model']
        self.master_df = pd.read_csv(self.file_path + '/Master_encoded.csv')
        self.master_df['Date'] = pd.to_datetime(self.master_df['Date'], format='mixed')
        self.start = min(self.master_df['Date'])
        self.end = max(self.master_df['Date']) - relativedelta(months=+8)
        self.model = RandomForestRegressor(n_estimators=500, max_depth=16, n_jobs=-1)
        self.cols = ['Date', 'st_label', 'comm_label', 'Price', 'Last_Month_Price', 'Last_2M_Price', 'Last_3M_Price', 'Last_4M_Price', 'Last_5M_Price', 'CPI', 'USDtoNaira', 'state_roll']
        self.final_feat = ['Last_Month_Price', 'state_roll', 'USDtoNaira', 'CPI', 'Last_5M_Price']
        self.lagged_cols = ['Last_Month_Price', 'Last_2M_Price', 'Last_3M_Price', 'Last_4M_Price', 'Last_5M_Price']

    @staticmethod
    def mape(Y_actual: np.array, Y_Predicted: np.array) -> np.array:
        """
        Calculate the Mean Absolute Percentage Error (MAPE) between actual and predicted values
        """
        mape = np.abs((np.array(Y_actual) - np.array(Y_Predicted))/np.array(Y_actual))*100
        return mape

    def state_errors(self, df: pd.DataFrame, predictor: RandomForestRegressor) -> List[float]:
        """
        Calculate model errors for each state
        """
        rows = df.shape[0]
        V = df.copy()
        V_inter = V.iloc[[0]]
        predictions = []

        for _ in range(rows):
            V_final = V_inter[self.final_feat]
            pred = predictor.predict(V_final)
            predictions.append(pred[0])
            V_inter[self.lagged_cols] = np.column_stack([pred[0], V_inter[self.lagged_cols].values[:, :-1]])

        V['Pred'] = predictions
        dict = {'Predictions': V['Pred'], 'st_label' : V["st_label"], 'comm_label' : V["comm_label"]}
        new_pred = pd.DataFrame(dict)

        model_errors = self.mape(list(df['Price'].iloc[0:]), new_pred['Predictions'].tolist())
        return model_errors

    def train_test_split(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split the data into training and test sets
        """
        X_train = self.master_df[(self.master_df['Date'] <= self.end)][self.cols]
        y_train = self.master_df[(self.master_df['Date'] <= self.end)]['Price']
        X_train_final = X_train[self.final_feat]

        X_test = self.master_df[(self.master_df['Date'] > self.end)][self.cols]
        y_test = self.master_df[(self.master_df['Date'] > self.end)]['Price']

        return X_train_final, y_train, X_test, y_test

    def train_model(self, X_train: pd.DataFrame, y_train: pd.DataFrame) -> None:
        """
        Train a new RandomForest model with the provided training data
        """
        self.model.fit(X_train.values, y_train.values)  # Training new model
        self.model.feature_names_in_ = X_train.columns.tolist()  # Set feature

    def load_old_model(self) -> RandomForestRegressor:
        """
        Load the old model from file
        """
        old_model = bz2.BZ2File(self.model_path, 'rb')
        old_model.check_input = False
        return pickle.load(old_model)

    def evaluate_model(self, X_test: pd.DataFrame, model: RandomForestRegressor, model_name: str) -> List[List[float]]:
        """
        Evaluate a model's performance by calculating the mean absolute percentage error for each state
        """
        consolidated_errors = []
        for i in range(5):
            for j in range(37):
                df_slice = X_test.loc[(X_test['comm_label'] == i) & (X_test['st_label'] == j)]
                consolidated_errors.append(self.state_errors(df_slice, model))

        avg_errors = [sum(x) / 185 for x in zip(*consolidated_errors)]  # Average over all commodities in all states
        print('Average Monthly Mape for all markets and commodities for {} model:'.format(model_name))
        model_table = dict({'Months': X_test['Date'].unique(), 'Mape': avg_errors})
        model_table = pd.DataFrame(model_table)
        print(model_table)

        return consolidated_errors

    def compare_and_save_best_model(self, old_model_errors: List[List[float]], new_model_errors: List[List[float]],
                                    new_model: RandomForestRegressor) -> None:
        """
        Compare the performance of the old and new models, and save the better one
        """
        if np.mean(old_model_errors) < np.mean(new_model_errors):
            print('old model is better')
            print('Keeping old model...')
        else:
            print('New model is better')
            print('Saving New model...')
            with bz2.BZ2File(self.model_path, 'w') as f:
                pickle.dump(new_model, f)
        print('Done')


if __name__ == '__main__':
    module = RetrainingModule()
    X_train, y_train, X_test, y_test = module.train_test_split()
    module.train_model(X_train, y_train)
    old_model = module.load_old_model()
    old_model_errors = module.evaluate_model(X_test, old_model, 'Old')
    new_model_errors = module.evaluate_model(X_test, module.model, 'New')
    module.compare_and_save_best_model(old_model_errors, new_model_errors, module.model)
