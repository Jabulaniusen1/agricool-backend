# Farmer Dashboard Data Pipeline Documentation

## Table of Contents
1. [Introduction](#Introduction)
2. [Data Pipeline Description](#data-pipeline-description)
3. [Intermediate tables](#intermediate-tables)
4. [API Documentation](#api-documentation)
5. [Further Deployment Details](#further-deployment-details-)


## Introduction

This markdown file is intended to give an overview of the endpoints for the Farmers Dashboard Backend pipeline. The code pulls data from the Coldtivate Database, computes metrics and stores them in a smaller intermediate table named `farmer_metrics`. The endpoints are exposed via a fastAPI server running inside a docker container (see instructions concerning spawning the Docker containers in README file of this repo).     


## Data Pipeline Description

The data pipeline leverages a series of structured SQL scripts, which are orchestrated by the indicator_reporter.py script. This script sources its data from the Coldtivate database. The primary role of this script is to conduct rigorous computations for the respective metrics and subsequently log these outcomes into the designated intermediate table, the specifications of which are delineated in the "Intermediate tables" section.

SQL scripts dedicated to utilization metrics are meticulously cataloged in the /sql_queries directory.

For individuals seeking to test the interfaces:

Kindly refer to the README documentation, which offers comprehensive guidelines on constructing the docker-compose project and initializing the requisite containers.
Once initialized, direct your attention to the farmer_web_api container.

### Intermediate table

- **farmer_metrics:** This table stores the metrics for individual farmers as a time series. The table is updated daily with the latest farmer utilization metrics by a running cronjob.


## Farmer table columns and their meanings 

### Farmer metrics Table

| Indicator Description  |        Computation Used         |
|------------------------|:-------------------------------:|
| date                   |               --                |
| report_date            |               --                |
| farmer_id              |          user_info.sql          |
| cooling_unit_id        |          user_info.sql          |
| gender                 |           user_info.sql           |
| room_crates_in         |          crates_in.sql          |
| room_ops_in            |          crates_in.sql          |
| room_kg_in             |          crates_in.sql          |
| room_crates_out        |         crates_out.sql          |
| room_ops_out           |         crates_out.sql          |
| room_kg_out            |         crates_out.sql          |
| check_in_crates_crop   | checkin_crop_distributions.sql  |
| check_in_kg_crop       | checkin_crop_distributions.sql  |
| check_out_kg_crop      | checkout_crop_distributions.sql |
| check_out_crates_crop  | checkout_crop_distributions.sql |

1. **indicator_reporter.py:** Executes all the sql queries and appends the data to the farmer_metrics table
2. **utils.py:** Database connection setup and configuration 
3. **DataSlicer.py:** Houses the main methods used for slicing and aggregating the intermediate table.
4. **main.py:** FastAPI server housing the endpoints


### How to create farmer_metrics table
Navigate to the project root folder, connect to the test or prod db and run the query in [create_tables.sql](create_tables.sql)

## API Documentation

### Endpoint: `/farmer-base-slice/`

<a name="endpoint-farmer-base-slice"></a>

- **Method**: POST
- **Purpose**: Fetches a slice of basic farmer information based on provided farmer ID.

- **Request**:
  - **Body**:
    - `farmer_id`: farmer ID in string format.

- **Response**: A dictionary representation of farmers and their corresponding metrics in a daily time series.

- **Example**:

  **Request**:
  ```json
  {
    "farmer_id": "10"
  }
  ```

  **Response**:
  
    ```json
    {"farmer_id":{"0":10},
     "first_name":{"0":"John"},
     "last_name":{"0":"Doe"},
     "gender":{"0":"ma"},
     "user_type":{"0":"FARMER"},
     "avg_storage_days":{"0":16.566648736527778},
      "total_storage_cost":{"0":140150.0}
     }
  ```
  
### Endpoint: `/farmer-slice/`

<a name="endpoint-farmer-slice"></a>

- **Method**: POST
- **Purpose**: Fetches a slice of farmer data based on provided farmer ID, cooling unit list and date range.

- **Request**:
  - **Body**:
    - `farmer_id`: farmer ID in string format. 
    - `unit_ids`: A comma-separated string of unit IDs.
    - `start_date`: Starting date in the format "YYYY-MM-DD".
    - `end_date`: Ending date in the format "YYYY-MM-DD".

- **Response**: A dictionary representation of farmers and their corresponding metrics in a daily time series.

  - **Example**:

    **Request**:
    ```json
    {
      "farmer_id": "4",
      "unit_ids": "4,7",
      "start_date": "2023-08-09",
      "end_date": "2023-08-31"
    }
    ```

    **Response**:
  
      ```json
      {
      "farmer_id": {
        "0": 4
      },
      "first_name": {
        "0": "User without a phone"
      },
      "last_name": {
        "0": ""
      },
      "gender": {
        "0": null
      },
      "user_type": {
        "0": "FARMER"
      },
      "avg_storage_days": {
        "0": 61.91527878706019
      },
      "total_storage_cost": {
        "0": 360000.0
      }
      },
      {
        "farmer_id": {
          "0": 4
        },
        "cooling_unit_id": {
          "0": 4
        },
        "gender": {
          "0": "ot"
        },
        "room_crates_in": {
          "0": 277
        },
        "room_ops_in": {
          "0": 50
        },
        "room_kg_in": {
          "0": 6925
        },
        "room_crates_out": {
          "0": 6
        },
        "room_ops_out": {
          "0": 2
        },
        "room_kg_out": {
          "0": 150
        },
        "check_in_crates_crop": {
          "0": {
            "Apple": 132.0,
            "Guava": 41.0,
            "Banana": 50.0,
            "Carrot": 5.0,
            "Grapes": 49.0
          }
        },
        "check_in_kg_crop": {
          "0": {
            "Apple": 3300.0,
            "Guava": 1025.0,
            "Banana": 1250.0,
            "Carrot": 125.0,
            "Grapes": 1225.0
          }
        },
        "check_out_crates_crop": {
          "0": {
            "Grapes": 6.0
          }
        },
        "check_out_kg_crop": {
          "0": {
            "Grapes": 150.0
          }
        }
      }


    ```
- **Important note**: The sub data structures in the have keys ordered in the format 0, 1.... depending on the number of cooling units in the request. Use the key "cooling_unit_id" to determine the order of the data for cooling units in the rest sub data structures

## Endpoint: `/impact-slice/`

<a name="endpoint-impact-slice"></a>

- **Method**: POST
- **Purpose**: Fetches a slice of impact data based on the provided farmer ID, list of cooling unit ids  and date range.

- **Request**:
  - **Body**:
      - `farmer_id`: A comma separated string of integers representing the cooling unit's ID. This is a required field.
      - `cooling_unit_id`: A comma separated string of integers representing the cooling unit's ID. This is a required field.
      - `start_date`: A string in the format "YYYY-MM-DD" representing the starting date.
      - `end_date`: A string in the format "YYYY-MM-DD" representing the ending date,

- **Response**: A dictionary representation of the sliced impact data.

- **Example**:

  **Request**:
  ```json
  {
      "farmer_id_2": "3",
      "cooling_unit_id": "3,4,5",
      "start_date": "2023-03-01",
      "end_date": "2024-03-05"
  }
  ```

  **Response**:

  ```json
  
    {
  "Aggregated": {
    "farmer_id": 3,
    "unit_name": "First Cooling",
    "baseline_quantity_total_month": 288.0,
    "avg_baseline_kg_selling_price_month": 11420.0,
    "baseline_kg_loss_month": 108.0,
    "baseline_kg_sold_month": 80.0,
    "avg_baseline_perc_loss_month": 37.5,
    "avg_baseline_farmer_revenue_month": 766400.0,
    "avg_monthly_kg_selling_price": 3.775659967659968,
    "monthly_kg_checkin": 2065.0,
    "monthly_kg_loss": 2624.0,
    "avg_monthly_perc_loss": 127.07021791767555,
    "avg_monthly_perc_foodloss_evolution": 238.8539144471348,
    "avg_monthly_farmer_revenue": -8610.02455994456,
    "avg_monthly_perc_revenue_increase_evolution": -101.12343744258148,
    "avg_monthly_perc_revenue_increase_evolution_2": -100.35500867046139,
    "avg_monthly_kg_selling_price_evolution": -11416.224340032339,
    "avg_monthly_perc_unit_selling_price_evolution": -99.66511552720371,
    "avg_monthly_farmer_revenue_evolution": -155002.00491198892,
    "latest_survey_date": "2023-11-23T01:12:19.430984+00:00"
  },
  "Top 5 Food Loss Evolution": {
    "Tomato": {
      "farmer_id": 3,
      "crop_id": 56,
      "crop_name": "Tomato",
      "unit_name": "First Cooling",
      "baseline_quantity_total_month": 80,
      "avg_baseline_kg_selling_price_month": 23400,
      "baseline_kg_loss_month": 16,
      "baseline_kg_sold_month": 24,
      "avg_baseline_perc_loss_month": 20,
      "avg_baseline_farmer_revenue_month": -14508000,
      "avg_monthly_kg_selling_price": 6.58581658581659,
      "monthly_kg_checkin": 1990,
      "monthly_kg_loss": 2610,
      "avg_monthly_perc_loss": 131.155778894472,
      "avg_monthly_perc_foodloss_evolution": 555.778894472362,
      "avg_monthly_farmer_revenue": -8693.2778932779,
      "avg_monthly_perc_revenue_increase_evolution": -99.9400794189876,
      "avg_monthly_kg_selling_price_evolution": -23393.4141834142,
      "avg_monthly_perc_unit_selling_price_evolution": -99.971855484676,
      "avg_monthly_farmer_revenue_evolution": 30531658.3610534,
      "latest_survey_date": "2023-11-08T10:09:48.440667+00:00"
    },
    "Spring onion": {
      "farmer_id": 3,
      "crop_id": 52,
      "crop_name": "Spring onion",
      "unit_name": "First Cooling",
      "baseline_quantity_total_month": 48,
      "avg_baseline_kg_selling_price_month": 300,
      "baseline_kg_loss_month": 12,
      "baseline_kg_sold_month": 16,
      "avg_baseline_perc_loss_month": 25,
      "avg_baseline_farmer_revenue_month": 3900,
      "avg_monthly_kg_selling_price": 4.8,
      "monthly_kg_checkin": 25,
      "monthly_kg_loss": 12,
      "avg_monthly_perc_loss": 48,
      "avg_monthly_perc_foodloss_evolution": 92,
      "avg_monthly_farmer_revenue": 62.4,
      "avg_monthly_perc_revenue_increase_evolution": -98.4,
      "avg_monthly_kg_selling_price_evolution": -295.2,
      "avg_monthly_perc_unit_selling_price_evolution": -98.4,
      "avg_monthly_farmer_revenue_evolution": 3637.4,
      "latest_survey_date": "2023-11-23T01:12:19.430984+00:00"
    },
    "Apple": {
      "farmer_id": 3,
      "crop_id": 1,
      "crop_name": "Apple",
      "unit_name": "First Cooling",
      "baseline_quantity_total_month": 176,
      "avg_baseline_kg_selling_price_month": 24361.1111111111,
      "baseline_kg_loss_month": 40,
      "baseline_kg_sold_month": 32,
      "avg_baseline_perc_loss_month": 22.7272727272727,
      "avg_baseline_farmer_revenue_month": 1169333.33333333,
      "avg_monthly_kg_selling_price": 0.453333333333333,
      "monthly_kg_checkin": 50,
      "monthly_kg_loss": 2,
      "avg_monthly_perc_loss": 4,
      "avg_monthly_perc_foodloss_evolution": -82.4,
      "avg_monthly_farmer_revenue": 20.8533333333333,
      "avg_monthly_perc_revenue_increase_evolution": -99.9982166476625,
      "avg_monthly_kg_selling_price_evolution": -24360.6577777778,
      "avg_monthly_perc_unit_selling_price_evolution": -99.9981391106043,
      "avg_monthly_farmer_revenue_evolution": 24346.5377777778,
      "latest_survey_date": "2023-11-09T08:26:01.368308+00:00"
    }
  },
  "Top 5 Revenue Evolution": {
    "Spring onion": {
      "farmer_id": 3,
      "crop_id": 52,
      "crop_name": "Spring onion",
      "unit_name": "First Cooling",
      "baseline_quantity_total_month": 48,
      "avg_baseline_kg_selling_price_month": 300,
      "baseline_kg_loss_month": 12,
      "baseline_kg_sold_month": 16,
      "avg_baseline_perc_loss_month": 25,
      "avg_baseline_farmer_revenue_month": 3900,
      "avg_monthly_kg_selling_price": 4.8,
      "monthly_kg_checkin": 25,
      "monthly_kg_loss": 12,
      "avg_monthly_perc_loss": 48,
      "avg_monthly_perc_foodloss_evolution": 92,
      "avg_monthly_farmer_revenue": 62.4,
      "avg_monthly_perc_revenue_increase_evolution": -98.4,
      "avg_monthly_kg_selling_price_evolution": -295.2,
      "avg_monthly_perc_unit_selling_price_evolution": -98.4,
      "avg_monthly_farmer_revenue_evolution": 3637.4,
      "latest_survey_date": "2023-11-23T01:12:19.430984+00:00"
    },
    "Tomato": {
      "farmer_id": 3,
      "crop_id": 56,
      "crop_name": "Tomato",
      "unit_name": "First Cooling",
      "baseline_quantity_total_month": 80,
      "avg_baseline_kg_selling_price_month": 23400,
      "baseline_kg_loss_month": 16,
      "baseline_kg_sold_month": 24,
      "avg_baseline_perc_loss_month": 20,
      "avg_baseline_farmer_revenue_month": -14508000,
      "avg_monthly_kg_selling_price": 6.58581658581659,
      "monthly_kg_checkin": 1990,
      "monthly_kg_loss": 2610,
      "avg_monthly_perc_loss": 131.155778894472,
      "avg_monthly_perc_foodloss_evolution": 555.778894472362,
      "avg_monthly_farmer_revenue": -8693.2778932779,
      "avg_monthly_perc_revenue_increase_evolution": -99.9400794189876,
      "avg_monthly_kg_selling_price_evolution": -23393.4141834142,
      "avg_monthly_perc_unit_selling_price_evolution": -99.971855484676,
      "avg_monthly_farmer_revenue_evolution": 30531658.3610534,
      "latest_survey_date": "2023-11-08T10:09:48.440667+00:00"
    },
    "Apple": {
      "farmer_id": 3,
      "crop_id": 1,
      "crop_name": "Apple",
      "unit_name": "First Cooling",
      "baseline_quantity_total_month": 176,
      "avg_baseline_kg_selling_price_month": 24361.1111111111,
      "baseline_kg_loss_month": 40,
      "baseline_kg_sold_month": 32,
      "avg_baseline_perc_loss_month": 22.7272727272727,
      "avg_baseline_farmer_revenue_month": 1169333.33333333,
      "avg_monthly_kg_selling_price": 0.453333333333333,
      "monthly_kg_checkin": 50,
      "monthly_kg_loss": 2,
      "avg_monthly_perc_loss": 4,
      "avg_monthly_perc_foodloss_evolution": -82.4,
      "avg_monthly_farmer_revenue": 20.8533333333333,
      "avg_monthly_perc_revenue_increase_evolution": -99.9982166476625,
      "avg_monthly_kg_selling_price_evolution": -24360.6577777778,
      "avg_monthly_perc_unit_selling_price_evolution": -99.9981391106043,
      "avg_monthly_farmer_revenue_evolution": 24346.5377777778,
      "latest_survey_date": "2023-11-09T08:26:01.368308+00:00"
    }
  },
      "Surveys":[{
      "farmer_id":3,
      "num_filled_baseline_surveys":32,
      "num_of_possible_baseline_surveys":5,
      "num_of_filled_postcheckout_surveys":5,
      "num_of_possible_postcheckout_surveys":5,
      "crops_with_baseline_survey_to_be_completed":"20,57,4,13"}]}
  ```

## Further Deployment Details 

There are two containers in the docker-compose project named web_api and scheduler. The first container exposes the fastAPI server to query the intermediate tables and return slices of the tables as dictionary types. The scheduler container runs cron jobs that periodically updates the intermediate tables. The cooling_unit_metrics and company_metrics tables are updated daily and the impact_view table at the end of every month.
