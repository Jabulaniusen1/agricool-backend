import os
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from DataSlicer import CompanySlicer, CoolingUnitSlicer, ImpactSlicer

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
    "cooling_unit_id": "first",
    "unit_name": "first",
    "baseline_quantity_total_month": "sum",
    "avg_baseline_kg_selling_price_month": "average",
    "baseline_kg_loss_month": "sum",
    "baseline_kg_sold_month": "sum",
    "avg_baseline_perc_loss_month": "average",
    "avg_baseline_farmer_revenue_month": "sum",
    "avg_monthly_kg_selling_price": "average",
    "monthly_kg_checkin": "sum",
    "monthly_kg_loss": "sum",
    "avg_monthly_perc_loss": "average",
    "avg_monthly_perc_foodloss_evolution": "average",
    "avg_monthly_farmer_revenue": "sum",
    "avg_monthly_perc_revenue_increase_evolution": "average",
    "avg_monthly_perc_revenue_increase_evolution_2": "average",
    "avg_monthly_kg_selling_price_evolution": "average",
    "avg_monthly_perc_unit_selling_price_evolution": "average",
    "avg_monthly_farmer_revenue_evolution": "sum",
    "latest_survey_date": "first",
    "num_post_harvest_surveys": "sum",
    "possible_post_checkout_survey_room": "sum",
    "total_post_checkout_survey_unit": "sum",
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
            value = item.get("value")
            if method == "sum" and isinstance(value, (int, float)):
                sum_values += value
            elif method == "average" and isinstance(value, (int, float)):
                sum_values += value
                count_values += 1

        if method == "sum":
            aggregated_data[key] = (
                {"name": items[0]["name"], "value": sum_values} if items else None
            )
        elif method == "average":
            average_value = sum_values / count_values if count_values else None
            aggregated_data[key] = (
                {"name": items[0]["name"], "value": average_value} if items else None
            )
        elif method == "first":
            aggregated_data[key] = items[0] if items else None

    return aggregated_data


@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("/index.html", {"request": request})


@app.post("/company-slice/")
async def company_slice(company_id: int = Form(...)):
    slicer = CompanySlicer(DB_PARAMS)
    df = slicer.slice_table(company_id)
    slicer.close()

    if df.empty:
        result_dict = {col: 0 for col in df.columns}
    else:
        result_dict = df.to_dict()

    return result_dict


@app.post("/coolingunit-slice/")
async def coolingunit_slice(
    unit_ids: str = Form(...), start_date: str = Form(...), end_date: str = Form(...)
):
    unit_ids_list = list(map(int, unit_ids.split(",")))
    slicer = CoolingUnitSlicer(DB_PARAMS)
    date_range = pd.date_range(start=start_date, end=end_date)
    df = slicer.slice_table(unit_ids_list, date_range)
    slicer.close()

    if df.empty:
        result_dict = {col: 0 for col in df.columns}
    else:
        result_dict = df.to_dict()

    return result_dict


@app.post("/impact-slice/")
async def impact_slice(
    company_id: int = Form(0),
    cooling_unit_id: str = Form("0,1"),
    start_date: str = Form(...),
    end_date: str = Form(...),
    mode: str = Form("cooling_unit"),
    view: str = Form("aggregated"),
):
    # Convert start_date and end_date from string to datetime.date
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Please use YYYY-MM-DD format."}

    unit_ids_list = list(map(int, cooling_unit_id.split(",")))
    slicer = ImpactSlicer(DB_PARAMS)

    try:
        # Call the slice_table method with the correct parameters
        df, co2_df = slicer.slice_table(
            company_id,
            unit_ids_list,
            start_date_obj,
            end_date_obj,
            mode,
        )
    except Exception as e:
        slicer.close()
        return {"error": str(e)}

    # Close the database connection
    slicer.close()
    result_dict = {}

    if isinstance(df, pd.DataFrame) and df.empty and mode == "company":
        result_dict = {col: 0 for col in df.columns}
        result_dict["company_id"] = company_id
    elif isinstance(df, pd.DataFrame) and not df.empty and mode == "company":
        result_dict = df.to_dict(orient="records")
    elif (
        isinstance(df, dict) and set(df.keys()) == {"empty"} and mode == "cooling_unit"
    ):
        result_dict = {col: 0 for col in df["empty"]["data"].columns}
    elif (
        isinstance(df, dict) and set(df.keys()) != {"empty"} and mode == "cooling_unit"
    ):
        result_dict = {}

        for i in unit_ids_list:
            try:
                result_dict = {col: [] for col in df[i]["data"].columns}
            except Exception as e:
                continue

            if result_dict:
                break

        for key in result_dict.keys():
            for unit, metrics in df.items():
                if unit != "empty":
                    if metrics["data"].empty:
                        if key != "unit_name":
                            result_dict[key].append(
                                {"name": metrics["name"], "value": 0}
                            )
                        else:
                            result_dict["unit_name"].append(
                                {"name": metrics["name"], "value": metrics["name"]}
                            )
                        if key == "cooling_unit_id":
                            for item in result_dict[key]:
                                # Check if the 'name' in the item matches metrics['name']
                                if item["name"] == metrics["name"]:
                                    # Update the 'value' key of this item
                                    item["value"] = unit
                                    break  # Exit the loop once the item is updated
                            else:
                                result_dict[key].append(
                                    {"name": metrics["name"], "value": unit}
                                )
                    else:
                        value = metrics["data"][key].iloc[0]
                        if isinstance(value, np.generic):
                            value = value.item()  # Convert numpy types to Python types
                        elif isinstance(value, pd.Timestamp):
                            value = (
                                value.to_pydatetime().isoformat()
                            )  # Convert pandas Timestamp to ISO formatted string

                        result_dict[key].append(
                            {
                                "name": metrics["data"]["unit_name"].iloc[0],
                                "value": value,
                            }
                        )
    else:
        raise ValueError("Error: Data slicer returned undefined structure")

    co2_df["cooling_unit_id"] = co2_df["cooling_unit_id"].astype(str)
    co2_df["company_id"] = co2_df["company_id"].astype(str)
    final_results = {
        "Impact metrics": result_dict,
        "Co2_metrics": co2_df.to_dict(orient="records"),
    }
    if view == "comparison":
        return final_results
    elif view == "aggregated":
        if mode == "company":
            return final_results
        else:
            for dct, val in result_dict.items():
                for key in val:
                    key["name"] = "Aggregate"
            agg_funcs = {
                "cooling_unit_id": "first",  # For non-numeric columns, 'first' takes the first value
                "company_id": "first",
                "co2_crops": lambda x: {
                    "co2_from": sum(d.get("co2_from", 0) for d in x),
                    "co2_to": sum(d.get("co2_to", 0) for d in x),
                },
            }
            co2_df = co2_df.groupby(["company_id"]).agg(agg_funcs)

            co2_df["cooling_unit_id"] = "Aggregate"
            co2_df["company_id"] = "Aggregate"

            final_results = {
                "Impact metrics": aggregate_data(
                    result_dict, impact_slice_aggregations
                ),
                "Co2_metrics": co2_df.to_dict(orient="records"),
            }

            return final_results
    else:
        raise ValueError("Error: Data slicer returned undefined view type")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
