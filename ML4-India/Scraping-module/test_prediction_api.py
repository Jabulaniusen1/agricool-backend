import pandas as pd
import numpy as np
import time
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
from subprocess import Popen
import json


d = pd.read_csv('data/validMarkets.csv', index_col=False)
j = d.to_json(orient = 'records')
parsed = json.loads(j)
commodities = ["Green Chilli", "Apple", "Banana", "Tomato"]

for r in parsed:
    for commodity in commodities:
        r.update({"commodity": commodity, "Available_values": 1})
        k = str(r).replace("\'","\"")
        lan = "curl -X POST -H \"Content-Type: application/json\" -d "+"\'" + k + "\'" + " http://localhost:5000/prediction >> output.txt"
        Popen(lan, shell=True)
        time.sleep(3)
