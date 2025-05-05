import os
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from DataSlicer import FarmerSlicer, FarmerBaseSlicer, ImpactSlicer

# Load environment variables from .env file
load_dotenv()

# Read database parameters from environment variables
DB_PARAMS = {
    "user": os.environ.get("DB_USERNAME", "base"),
    "password": os.environ.get("DB_PASSWORD", "base"),
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "base"),
}

# Initialize FastAPI application and Jinja2 templates
app = FastAPI()

# Configuring CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify specific origins instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="fastAPI")


impact_slice_aggregations = {
    'cooling_unit_id': 'first',
    'unit_name': 'first',
    'baseline_quantity_total_month': 'sum',
    'avg_baseline_kg_selling_price_month': 'average',
    'baseline_kg_loss_month': 'sum',
    'baseline_kg_sold_month': 'sum',
    'avg_baseline_perc_loss_month': 'average',
    'avg_baseline_farmer_revenue_month': 'sum',
    'avg_monthly_kg_selling_price': 'average',
    'monthly_kg_checkin': 'sum',
    'monthly_kg_loss': 'sum',
    'avg_monthly_perc_loss': 'average',
    'avg_monthly_perc_foodloss_evolution': 'average',
    'avg_monthly_farmer_revenue': 'sum',
    'avg_monthly_perc_revenue_increase_evolution': 'average',
    'avg_monthly_perc_revenue_increase_evolution_2': 'average',
    'avg_monthly_kg_selling_price_evolution': 'average',
    'avg_monthly_perc_unit_selling_price_evolution': 'average',
    'avg_monthly_farmer_revenue_evolution': 'sum',
    'latest_survey_date': 'first',
    'num_post_harvest_surveys': 'sum',
    'possible_post_checkout_survey_room': 'sum',
    'total_post_checkout_survey_unit': 'sum'
}


def aggregate_data(data, aggregations):
    """
    Aggregates data based on specified methods in the aggregations dictionary.

    Args:
    - data: The dictionary containing the data to be aggregated.
    - aggregations: A dictionary specifying the aggregation method ('sum', 'average', 'first') for each key.

    Returns:
    - A dictionary with aggregated data.
    """
    aggregated_data = {}

    for key, method in aggregations.items():
        items = data.get(key, [])

        # Initialize variables for sum and average calculations
        sum_values = 0
        count_values = 0

        for item in items:
            value = item.get('value')
            if method == 'sum' and isinstance(value, (int, float)):
                sum_values += value
            elif method == 'average' and isinstance(value, (int, float)):
                sum_values += value
                count_values += 1

        if method == 'sum':
            aggregated_data[key] = {'name': items[0]['name'], 'value': sum_values} if items else None
        elif method == 'average':
            average_value = sum_values / count_values if count_values else None
            aggregated_data[key] = {'name': items[0]['name'], 'value': average_value} if items else None
        elif method == 'first':
            aggregated_data[key] = items[0] if items else None

    return aggregated_data

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("/index.html", {"request": request})


@app.post("/farmer-base-slice/")
async def farmer_base_slice(
    farmer: str = Form(...)):

    slicer = FarmerBaseSlicer(DB_PARAMS)
    info_df = slicer.slice_table(farmer)
    slicer.close()

    if info_df.empty:
        result_dict = {col: 0 for col in info_df.columns}
    else:
        result_dict = info_df.to_dict()

    return result_dict

@app.post("/farmer-slice/")
async def farmer_slice(
    farmer_id: str = Form(...), unit_ids: str = Form(...), start_date: str = Form(...), end_date: str = Form(...)
):
    # Convert start_date and end_date from string to datetime.date
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Please use YYYY-MM-DD format."}

    # Convert start_date and end_date from string to datetime.date objects
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Compare the datetime.date objects
    if start_date_obj > end_date_obj:
        raise ValueError("Start date must be before end date")

    unit_ids_list = list(map(int, unit_ids.split(",")))
    slicer = FarmerSlicer(DB_PARAMS)
    date_range = pd.date_range(start=start_date, end=end_date)
    info_df, utilzation_df = slicer.slice_table(farmer_id, unit_ids_list, date_range)
    slicer.close()

    if info_df.empty:
        result_dict = {col: 0 for col in info_df.columns}
    else:
        result_dict = info_df.to_dict()

    if utilzation_df.empty:
        result_dict_2 = {col: 0 for col in utilzation_df.columns}
    else:
        result_dict_2 = utilzation_df.to_dict()

    return result_dict, result_dict_2


@app.post("/impact-slice/")
async def impact_slice(
    farmer_id_2: str = Form(...),
    cooling_unit_id: str = Form("0,1"),
    start_date: str = Form(...),
    end_date: str = Form(...),
):
    # Convert start_date and end_date from string to datetime.date
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Please use YYYY-MM-DD format."}

    # Convert start_date and end_date from string to datetime.date objects
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Compare the datetime.date objects
    if start_date_obj > end_date_obj:
        raise ValueError("Start date must be before end date")

    unit_ids_list = list(map(int, cooling_unit_id.split(",")))

    slicer = ImpactSlicer(DB_PARAMS)

    try:
        # Call the slice_table method with the correct parameters
        df = slicer.slice_table(
            farmer_id_2,
            unit_ids_list,
            start_date_obj,
            end_date_obj,
        )
    except Exception as e:
        slicer.close()
        return {"error": str(e)}

    # Close the database connection
    slicer.close()
    result_dict = {}

    if isinstance(df['Aggregated'][0], dict) and set(df['Aggregated'][0].keys()) != {"empty"}:
        result_dict = df['Aggregated'][0]
    elif isinstance(df['Aggregated'][0], pd.DataFrame) and df['Aggregated'][0].empty:
        result_dict = {col: 0 for col in df['Aggregated'][0].columns}
    elif isinstance(df['Aggregated'][0], pd.DataFrame) and not df['Aggregated'][0].empty:
        result_dict = df['Aggregated'][0].to_dict(orient="records")
    elif (
        isinstance(df['Aggregated'][0], dict) and set(df['Aggregated'][0].keys()) == {"empty"}
    ):
        result_dict = {col: 0 for col in df['Aggregated'][0]["empty"]["data"].columns}
    else:
        raise ValueError("Error: Data slicer returned undefined structure for Aggregated results")

    revenue_result_dict = {}
    foodloss_result_dict = {}

    for crop in df['Top 5 Revenue Evolution']:
        if isinstance(crop, dict) and set(crop.keys()) != {"empty"}:
            result_dict_buffer = crop
        elif isinstance(crop, pd.DataFrame) and crop.empty:
            result_dict_buffer = {col: 0 for col in crop.columns}
        elif isinstance(crop, pd.DataFrame) and not crop.empty:
            result_dict_buffer = crop.to_dict(orient="records")
        elif (
            isinstance(crop, dict) and set(crop.keys()) == {"empty"}
        ):
            result_dict_buffer = {col: 0 for col in crop["empty"]["data"].columns}
        else:
            raise ValueError("Error: Data slicer returned undefined structure for crop_wise results")

        revenue_result_dict[crop['crop_name']] = result_dict_buffer

    for crop in df['Top 5 Food Loss Evolution']:
        if isinstance(crop, dict) and set(crop.keys()) != {"empty"}:
            result_dict_buffer = crop
        elif isinstance(crop, pd.DataFrame) and crop.empty:
            result_dict_buffer = {col: 0 for col in crop.columns}
        elif isinstance(crop, pd.DataFrame) and not crop.empty:
            result_dict_buffer = crop.to_dict(orient="records")
        elif (
            isinstance(crop, dict) and set(crop.keys()) == {"empty"}
        ):
            result_dict_buffer = {col: 0 for col in crop["empty"]["data"].columns}
        else:
            raise ValueError("Error: Data slicer returned undefined structure for crop_wise results")

        foodloss_result_dict[crop['crop_name']] = result_dict_buffer


    result_dict_3 = df['Surveys']
    final_result = {'Aggregated': result_dict, 'Top 5 Food Loss Evolution': foodloss_result_dict, 'Top 5 Revenue '
                                                                                                  'Evolution':
        revenue_result_dict, 'Surveys': result_dict_3}

    return final_result


# Run application if the script is executed
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
