# Impact Dashboard Data Pipeline Documentation

## Table of Contents
1. [Introduction](#Introduction)
2. [Data Pipeline Description](#data-pipeline-description)
3. [Intermediate tables](#intermediate-tables)
4. [Flow & Scripts](#flow--scripts)
5. [API Documentation](#api-documentation)
6. [Further Deployment Details](#further-deployment-details-)


## Introduction

This markdown file is intended to give an overview of the endpoints for the Impact Dashboard Backend pipeline. The code pulls data from the Coldtivate Database, computes metrics and stores them in smaller intermediate tables named `company_metrics`, `cooling_unit_metrics`, and `impact_metrics`. The endpoints are exposed via a fastAPI server running inside a docker container (see instructions concerning spawning the Docker containers in README file of this repo).     


## Data Pipeline Description

The data pipeline leverages a series of structured SQL scripts, which are orchestrated by the indicator_reporter.py script. This script sources its data from the Coldtivate database. The primary role of this script is to conduct rigorous computations for the respective metrics and subsequently log these outcomes into the designated intermediate tables, the specifications of which are delineated in the "Intermediate tables" section.

SQL scripts dedicated to utilization metrics are meticulously cataloged in the /sql_queries directory, whereas those for impact metrics are housed within the /impact_queries directory.

For individuals seeking to test the interfaces:

Kindly refer to the README documentation, which offers comprehensive guidelines on constructing the docker-compose project and initializing the requisite containers.
Once initialized, direct your attention to the web_api container.
To commence the testing process, execute the provided command.
```commandline
python3 test_app.py  
```

### Intermediate tables

- **company_metrics:** This table stores the company-level metrics. Each row corresponds to the metrics for a single company.
- **cooling_unit_metrics:** This table stores the metrics for individual cooling units as a time series. The table is updated daily with the latest cold-room metrics by a running cronjob.
- **impact_metrics:** This table stores the impact metrics "food-loss evolution" and "smallholder revenue evolution" (more impact metrics to be integrated in version 2). It is indexed by Cooling unit -> crop-type -> farmer (the idea is to store and track this at the individual level). The [impact-slicer](#endpoint-impact-slice) aggregates the data to the cooling unit level and returns it. 

## Intermediate table columns and their meanings 

### Table: `company_metrics`

| Column name                 |                               Meaning                                                                   |
|-----------------------------|:-------------------------------------------------------------------------------------------------------:|
| report_date                 |                          The date the report was last updated                                           |
| currency                    |  The currency of the country the corresponding company belongs to                                       |
| cooling_unit_types          |       A dictionary with the distinct cooling unit types belonging to a company                          |
| company_id                  |                   The company id in the database                                                        |
| comp_unspec_user_type       |   The count of cooling users associated to a company that are neither farmers nor traders               |
| comp_traders                |             The count of cooling users associated to a company that are traders                         |
| comp_revenue_usd            | The total company-wide revenue generated from operations registered in Coldtivate in USD                |
| comp_revenue                |    The total company-wide revenue generated from operations registered in Coldtivate in local currency  |
| comp_reg_users_ot           |                   Total 'Other' registered employees                                                    |
| comp_reg_users_ma           |                     Total 'Male' registered employees                                                   |
| comp_reg_users_fem          |                    Total 'Female' registered employees                                                  |
| comp_reg_users              |                       Total registered employees                                                        |
| comp_ops_out                |                     Total check-out operations                                                          |
| comp_ops_in                 |                      Total check-in operations                                                          |
| comp_op_ot                  |                       Total 'Other' operators                                                           |
| comp_op_ma                  |                        Total 'Male' operators                                                           |
| comp_op_fem                 |                       Total 'Female' operators                                                          |
| comp_op                     |                           Total operators                                                               |
| comp_name                   |                            Company name                                                                 |
| comp_logo                   |                        Link to company logo                                                             |
| comp_kg_out                 |                        Total kg checked out                                                             |
| comp_kg_in                  |                         Total kg checked in                                                             |
| comp_farmers                |                       Total number of farmers                                                           |
| comp_crates_out             |                      Total crates checked out                                                           |
| comp_crates_in              |                       Total crates checked in                                                           |
| comp_country                |                           Company country                                                               |
| comp_cool_users_ot          |                     Total 'Other' cooling users                                                         |
| comp_cool_users_ma          |                      Total 'Male' cooling users                                                         |
| comp_cool_users_fem         |                     Total 'Female' cooling users                                                        |
| comp_cool_users             |                         Total cooling users                                                             |
| comp_cap_tons               |       Total capacity in metric tons across all cooling units                                            |
| comp_cap_num_crates         |     Total capacity in number of crates across all cooling units                                         |
| comp_beneficiaries_ma       |                      Total male beneficiaries                                                           |
| comp_beneficiaries_fem      |                     Total female beneficiaries                                                          |
| comp_beneficiaries          |                         Total beneficiaries                                                             |
| comp_average_room_occupancy |          Average occupancy across all rooms of a company                                                |

### Table: `cooling_unit_metrics`

| Columns name           |                            Meaning                            |
|------------------------|:-------------------------------------------------------------:|
| date                   |           The date the respective metrics refer to            |
| report_date            |               The date the report was generated               |
| cooling_unit_id        |                      The cooling unit id                      |
| room_revenue           | The room revenue for the corresponding date in local currency |
| room_revenue_usd       |      The room revenue for the corresponding date in USD       |
| check_in_crates_crop   | Dictionary with the daily check-in amount per crop in crates  |
| check_in_kg_crop       |   Dictionary with the daily check-in amount per crop in kg    |
| check_out_kg_crop      |   Dictionary with the daily check-out amount per crop in kg   |
| check_out_crates_crop  | Dictionary with the daily check-out amount per crop in crates |
| id                     |                              --                               |
| is_unit_deleted        |          Boolean indicating if room has been deleted          |
| cap_tons               |                 Room capacity in metric tons                  |
| cap_num_crates         |               Room capacity in number of crates               |
| company_id             |                        The company id                         |
| room_op                |        The number of room operators assigned to a room        |
| room_op_fem            |   The number of 'Female' room operators assigned to a room    |
| room_op_ma             |    The number of 'Male' room operators assigned to a room     |
| room_op_ot             |    The number of 'Other' room operators assigned to a room    |
| room_beneficiaries     |          The number of room beneficiaries on the day          |
| room_beneficiaries_fem |      The number of female room beneficiaries on the day       |
| room_beneficiaries_ma  |       The number of male room beneficiaries on the day        |
| room_active_users      |             The number of active users on the day             |
| room_active_user_ids   |    The distinct user ids of the corresponding active users    |
| room_active_fem        |        The number of 'Female' active users on the day         |
| room_active_ma         |         The number of 'Male' active users on the day          |
| room_active_ot         |         The number of 'Other' active users on the day         |
| room_crates_in         |              The daily check-in amount in crates              |
| room_ops_in            |            The daily check-in movement operations             |
| room_kg_in             |                The daily check-in amount in kg                |
| room_crates_out        |             The daily check-out amount in crates              |
| room_ops_out           |            The daily check-out movement operations            |
| room_kg_out            |               The daily check-out amount in kg                |
| average_room_occupancy |                     Daily room occupancy                      |
| unit_name              |                       Cooling unit name                       |
| currency               |       Cooling unit currency, inherited from the company       |
| state                  |                      Cooling unit state                       |
| cool_unit_type         |                       Cooling unit type                       |
| comp_name              |                       The company name                        |
| tot_co2                | The total amount of daily co2 contributions in Kg co2/Kg crop |
| co2_crops              |    The cropwise daily co2 contributions in Kg co2/Kg crop     |


### Table: `impact_metrics`

| Column name                               |                                          Meaning                                           |
|-------------------------------------------|:------------------------------------------------------------------------------------------:|
| latest_survey_date                        |                            The latest post-checkout survey date                            |
| company_id                                |                                       The company id                                       |
| farmer_id                                 |                                       The farmer id                                        |
| monthly_perc_loss                         |            The percentage loss for the current month from post-checkout surveys            |
| monthly_perc_foodloss_evolution           |               The food-loss evolution from the baseline to the current month               |
| cooling_unit_id                           |                                    The cooling unit id                                     |
| crop_id                                   |                                        The crop id                                         |
| baseline_quantity_total_month             |                       The baseline total produced quantity in a week                       |
| baseline_kg_selling_price_month           |                             The baseline selling price per kg                              |
| baseline_kg_loss_month                    |                             The baseline loss in kg in a week                              |
| baseline_perc_loss_month                  |                            The percentage loss for the baseline                            |
| baseline_kg_sold_month                    |                         The baseline total sold quantity in a week                         |
| baseline_farmer_revenue_month             |                  The baseline farmer revenue in local currency in a week                   |
| monthly_kg_selling_price                  | The selling price per kg in local currency for the current month from post-checkout survey |
| monthly_kg_checkin                        |                        The amount checked-in for the current month                         |
| monthly_kg_loss                           |        The total amount lost for the current month in kg from post-checkout surveys        |
| monthly_farmer_revenue                    |              The total farmer revenue in local currency for the current month              |
| monthly_kg_selling_price_evolution        |    The selling price evolution in local currency from the baseline to the current month    |
| monthly_perc_unit_selling_price_evolution |                         The selling price evolution in percentage                          |
| monthly_farmer_revenue_evolution          |   The farmer revenue evolution in local currency from the baseline to the current month    |
| monthly_perc_revenue_evolution            |                         The farmer revenue evolution in percentage                         |
| first_name                                |                                     Farmer first name                                      |
| last_name                                 |                                      Farmer last name                                      |
| crop_name                                 |                                       The crop name                                        |
| currency                                  |                                   The farmer's currency                                    |
| baseline_completed_surveys_room           |                   The total completed baseline surveys for a single room                   |
| possible_post_checkout_surveys_room       |    The total number of possible post-checkout surveys that could be filled in the room     |
| total_post_checkout_survey_unit           |           The total number of post-checkout surveys actually filled in the room            |


### Flow & Scripts

[![Data pipeline Flowchart](https://mermaid.ink/img/pako:eNqNk9tu2zAMhl-F0HXjIe1dBgxoErtNtwHp3N1sHgJFYhOhsqTq0M1t-u6j7SQ9IC3qC8OgPv40f1IPTFiJbMRWnrs1XE0_Vwbo6d8hLfv4lEc-Vw61Mtgfnf6uWHn5DUrhlYuhYn9gMPiyyf-hSBEljJsNjIlRRirBo_ULj876iD5zDdHbOuMua5607mpA4W29gQklCquluuOktcycDXHlMWSSmCUPmPH75DETtn4tNbG1ox8I8B2jVyJsYEpiM0OFa5SK9OCKLzWGp8Rpmwg5YW0yN82i7nNfI8WwYyy5sFoko-Jb4FkLzkhLHEDOhn29lml7LrUS6GGieXhGFR-i8g9BW6ljogoe4ul8BrmRzioTn2FoZGUOzL31-zKhV-RZd9ppnpDYp3CrF7f9ERQ0L_S7PShp4kjmF4T9jEqrex6VNbupwE5wX71zptVUvW3vy57v_X1b8WA_VtygLzEm91R2RmLDDCYSyBAL7Z4GRYUa8NbGbWm4IOo4gx_JgOxUBrR9RCKdorkbXCuNkNFX5ryVQAVe9HbRiXwlkZMMdlPgRtIFWqNMmsYmrImcLpgPEBz_a1C-aIYdsZqWmCtJ1_WhDVcsrrHGio3oU3J_U7HKPBLHU7RlYwQbRZ_wiCVHFwenipMLNRtdcx320Vy2ve6DtP-_rN1Bj_8BpRxUiA?type=png)](https://mermaid.live/edit#pako:eNqNk9tu2zAMhl-F0HXjIe1dBgxoErtNtwHp3N1sHgJFYhOhsqTq0M1t-u6j7SQ9IC3qC8OgPv40f1IPTFiJbMRWnrs1XE0_Vwbo6d8hLfv4lEc-Vw61Mtgfnf6uWHn5DUrhlYuhYn9gMPiyyf-hSBEljJsNjIlRRirBo_ULj876iD5zDdHbOuMua5607mpA4W29gQklCquluuOktcycDXHlMWSSmCUPmPH75DETtn4tNbG1ox8I8B2jVyJsYEpiM0OFa5SK9OCKLzWGp8Rpmwg5YW0yN82i7nNfI8WwYyy5sFoko-Jb4FkLzkhLHEDOhn29lml7LrUS6GGieXhGFR-i8g9BW6ljogoe4ul8BrmRzioTn2FoZGUOzL31-zKhV-RZd9ppnpDYp3CrF7f9ERQ0L_S7PShp4kjmF4T9jEqrex6VNbupwE5wX71zptVUvW3vy57v_X1b8WA_VtygLzEm91R2RmLDDCYSyBAL7Z4GRYUa8NbGbWm4IOo4gx_JgOxUBrR9RCKdorkbXCuNkNFX5ryVQAVe9HbRiXwlkZMMdlPgRtIFWqNMmsYmrImcLpgPEBz_a1C-aIYdsZqWmCtJ1_WhDVcsrrHGio3oU3J_U7HKPBLHU7RlYwQbRZ_wiCVHFwenipMLNRtdcx320Vy2ve6DtP-_rN1Bj_8BpRxUiA)

1. **indicator_reporter.py:** Executes all the sql queries and appends the data to the intermediate tables 
2. **dataProcessor.py:** Some functions used in the metrics computation.
3. **create_view.py:** For creating the analytics_crate_movements view (critical for computing the metrics)
4. **utils.py:** Database connection setup and configuration 
5. **DataSlicer.py:** Houses the main methods used for slicing and aggregating the intermediate tables.
6. **main.py:** FastAPI server housing the endpoints

## API Documentation

### Endpoint: `/company-slice/`

<a name="endpoint-company-slice"></a>

- **Method**: POST
- **Purpose**: Fetches a slice of company data based on the provided company ID.

- **Request**:
  - **Body**:
    - `company_id`: An integer representing the company's ID. This is a required field.

- **Response**: A dictionary representation of the sliced company data.

- **Example**:

  **Request**:
  ```json
  {
      "company_id": 3
  }
  ```

  **Response**:
  
    ```json
    {
    "report_date": {
        "0": "2023-11-17"
    },
    "company_id": {
        "0": 3
    },
    "comp_name": {
        "0": "Divine's Chillers test"
    },
    "comp_logo": {
        "0": ""
    },
    "comp_country": {
        "0": "NG"
    },
    "comp_cap_tons": {
        "0": 5.0
    },
    "comp_cap_num_crates": {
        "0": 50
    },
    "cooling_unit_types": {
        "0": {
            "FARM_GATE_STORAGE_ROOM": 1
        }
    },
    "comp_op": {
        "0": 1
    },
    "comp_op_fem": {
        "0": 0
    },
    "comp_op_ma": {
        "0": 1
    },
    "comp_op_ot": {
        "0": 0
    },
    "currency": {
        "0": "NGN"
    },
    "comp_reg_users": {
        "0": 1
    },
    "comp_reg_users_ma": {
        "0": 1
    },
    "comp_reg_users_fem": {
        "0": 0
    },
    "comp_reg_users_ot": {
        "0": 0
    },
    "comp_beneficiaries": {
        "0": 18.8
    },
    "comp_beneficiaries_fem": {
        "0": 9.31
    },
    "comp_beneficiaries_ma": {
        "0": 9.49
    },
    "comp_cool_users": {
        "0": 4
    },
    "comp_cool_users_fem": {
        "0": 1
    },
    "comp_cool_users_ma": {
        "0": 2
    },
    "comp_cool_users_ot": {
        "0": 1
    },
    "comp_farmers": {
        "0": 3
    },
    "comp_traders": {
        "0": 1
    },
    "comp_unspec_user_type": {
        "0": 0
    },
    "comp_crates_in": {
        "0": 648
    },
    "comp_ops_in": {
        "0": 128
    },
    "comp_kg_in": {
        "0": 16200
    },
    "comp_crates_out": {
        "0": 194
    },
    "comp_ops_out": {
        "0": 36
    },
    "comp_kg_out": {
        "0": 4850
    },
    "comp_average_room_occupancy": {
        "0": 9.0
    },
    "comp_revenue": {
        "0": 402350.0
    },
    "comp_revenue_usd": {
        "0": 486.61
    }
  }
  ```
  
### Endpoint: `/coolingunit-slice/`

<a name="endpoint-coolingunit-slice"></a>

- **Method**: POST
- **Purpose**: Fetches a slice of cooling unit data based on provided unit IDs and date range.

- **Request**:
  - **Body**:
    - `unit_ids`: A comma-separated string of unit IDs.
    - `start_date`: Starting date in the format "YYYY-MM-DD".
    - `end_date`: Ending date in the format "YYYY-MM-DD".

- **Response**: A dictionary representation of cooling-units and their corresponding metrics in a daily time series.

- **Example**:

  **Request**:
  ```json
  {
    "unit_ids": "4,7",
    "start_date": "2023-09-01",
    "end_date": "2024-02-26"
  }
  ```

  **Response**:
  
    ```json
  {
  "cooling_unit_id": {
    "0": 4,
    "1": 7
  },
  "unit_name": {
    "0": "Bremgarten 1.0",
    "1": "Bremgarten 2.0"
  },
  "is_unit_deleted": {
    "0": 0.0,
    "1": 0.0
  },
  "state": {
    "0": "",
    "1": ""
  },
  "cool_unit_type": {
    "0": "FARM_GATE_STORAGE_ROOM",
    "1": "MARKET_STORAGE_ROOM"
  },
  "cap_tons": {
    "0": 5.0,
    "1": 1.0
  },
  "cap_num_crates": {
    "0": 50.0,
    "1": 100.0
  },
  "company_id": {
    "0": 3,
    "1": 3
  },
  "comp_name": {
    "0": "Divine's Chillers test",
    "1": "Divine's Chillers test"
  },
  "comp_pricing": {
    "0": "Per Crate per day",
    "1": "Per Crate per day"
  },
  "currency": {
    "0": "NGN",
    "1": "NGN"
  },
  "room_op": {
    "0": 1.0,
    "1": 1.0
  },
  "room_op_fem": {
    "0": 0.0,
    "1": 0.0
  },
  "room_op_ma": {
    "0": 1.0,
    "1": 1.0
  },
  "room_op_ot": {
    "0": 0.0,
    "1": 0.0
  },
  "room_beneficiaries": {
    "0": 18.8,
    "1": 14.100000000000001
  },
  "room_beneficiaries_fem": {
    "0": 9.306000000000001,
    "1": 6.979500000000001
  },
  "room_beneficiaries_ma": {
    "0": 9.494,
    "1": 7.120500000000001
  },
  "room_active_user_ids": {
    "0": [28, 29, 30, 15],
    "1": [28, 29, 30]
  },
  "room_active_users": {
    "0": 4,
    "1": 3
  },
  "room_active_fem": {
    "0": 1,
    "1": 1
  },
  "room_active_ma": {
    "0": 2,
    "1": 2
  },
  "room_active_ot": {
    "0": 0,
    "1": 0
  },
  "room_crates_in": {
    "0": 163,
    "1": 20
  },
  "room_ops_in": {
    "0": 29,
    "1": 5
  },
  "room_kg_in": {
    "0": 4075,
    "1": 500
  },
  "room_crates_out": {
    "0": 199,
    "1": 9
  },
  "room_ops_out": {
    "0": 38,
    "1": 3
  },
  "room_kg_out": {
    "0": 4975,
    "1": 225
  },
  "average_room_occupancy": {
    "0": 920.887573964497,
    "1": 6.331360946745562
  },
  "room_revenue": {
    "0": 477250.0,
    "1": 67000.0
  },
  "room_revenue_usd": {
    "0": 5022.330299951136,
    "1": 44.88420725101605
  },
  "check_in_crates_crop": {
    "0": {
      "Apple": 58.0,
      "Banana": 23.0,
      "Cabbage": 27.0,
      "Colacasia": 20.0,
      "Bottle Gourd": 15.0,
      "Carrot": 7.0,
      "Ginger": 8.0
    },
    "1": {
      "Apple": 4.0,
      "Broccoli": 4.0,
      "Coriander": 4.0,
      "Tomato": 4.0,
      "Avocado": 4.0
    }
  },
  "check_in_kg_crop": {
    "0": {
      "Apple": 1450.0,
      "Banana": 575.0,
      "Cabbage": 675.0,
      "Colacasia": 500.0,
      "Bottle Gourd": 375.0,
      "Carrot": 175.0,
      "Ginger": 200.0
    },
    "1": {
      "Apple": 100.0,
      "Broccoli": 100.0,
      "Coriander": 100.0,
      "Tomato": 100.0,
      "Avocado": 100.0
    }
  },
  "check_out_crates_crop": {
    "0": {
      "Apple": 81.0,
      "Banana": 33.0,
      "Cabbage": 27.0,
      "Colacasia": 20.0,
      "Bottle Gourd": 15.0,
      "Guava": 12.0,
      "Carrot": 5.0,
      "Grapes": 6.0
    },
    "1": {
      "Coriander": 1.0,
      "Tomato": 4.0,
      "Apple": 4.0
    }
  },
  "check_out_kg_crop": {
    "0": {
      "Apple": 2025.0,
      "Banana": 825.0,
      "Cabbage": 675.0,
      "Colacasia": 500.0,
      "Bottle Gourd": 375.0,
      "Guava": 300.0,
      "Carrot": 125.0,
      "Grapes": 150.0
    },
    "1": {
      "Coriander": 25.0,
      "Tomato": 100.0,
      "Apple": 100.0
    }
  },
  "tot_co2":{"0":-1600.1476903482649,"1":8.054862288960159},
  "co2_crops":{"0":{"Apple":{"coldroom":10.77694027778415,"no-coldroom":19.035322715000024,"difference":8.258382437215841},"Guava":{"coldroom":22.846052845389533,"no-coldroom":19.035322715000024,"difference":-3.8107301303894197},"Lemon":{"coldroom":137.08518891825278,"no-coldroom":19.035322715000024,"difference":-118.04986620325325},"Banana":{"coldroom":13.983593257647955,"no-coldroom":19.035322715000024,"difference":5.051729457352096},"Carrot":{"coldroom":25.331433350966737,"no-coldroom":19.035322715000024,"difference":-6.296110635966701},"Grapes":{"coldroom":18.111818377666772,"no-coldroom":19.035322715000024,"difference":0.9235043373331739},"Cabbage":{"coldroom":41.203608488351854,"no-coldroom":19.035322715000024,"difference":-22.16828577335172},"Beetroot":{"coldroom":266.55620980989653,"no-coldroom":19.035322715000024,"difference":-247.52088709489726},"Cucumber":{"coldroom":93.9281819565119,"no-coldroom":19.035322715000024,"difference":-74.89285924151208},"Jackfruit":{"coldroom":162.97939309581122,"no-coldroom":19.035322715000024,"difference":-143.94407038081098},"Strawberry":{"coldroom":784.4402934727965,"no-coldroom":19.035322715000024,"difference":-765.4049707577907},"Colacasia":{"coldroom":44.43883784009072,"no-coldroom":17.971896865000023,"difference":-26.46694097509071},"Bottle Gourd":{"coldroom":57.030864502683656,"no-coldroom":17.971896865000023,"difference":-39.05896763768378},"Ginger":{"coldroom":76.05176748933016,"no-coldroom":13.824536050000017,"difference":-62.22723143933003},"Sweet Potato":{"coldroom":118.36492236008662,"no-coldroom":13.824536050000017,"difference":-104.54038631008619}},"1":{"Apple":{"coldroom":8.155441459348063,"no-coldroom":10.102545575000011,"difference":1.9471041156519455},"Broccoli":{"coldroom":8.155441459348063,"no-coldroom":10.102545575000011,"difference":1.9471041156519455},"Coriander":{"coldroom":8.155441459348063,"no-coldroom":10.102545575000011,"difference":1.9471041156519455},"Tomato":{"coldroom":4.635724618997845,"no-coldroom":5.742499590000005,"difference":1.1067749710021586},"Avocado":{"coldroom":4.635724618997845,"no-coldroom":5.742499590000005,"difference":1.1067749710021586}}}
  }

  ```

## Endpoint: `/impact-slice/`

<a name="endpoint-impact-slice"></a>

- **Method**: POST
- **Purpose**: Fetches a slice of impact data based on the provided cooling unit ID and month-year.

- **Request**:
  - **Body**:
    - `cooling_unit_id`: A comma separated list representing the cooling unit's IDs. This is a required field.
    - `company_id`: An integer representing the company's ID. This is a required field.
    - `start_date`: A string in the format "YYYY-MM-DD" representing the starting date.
    - `end_date`: A string in the format "YYYY-MM-DD" representing the ending date,
    - `mode`: str = A string representing which key to do the aggregation on (choice between "company_id" and "cooling_unit_id)
    - `view`: str = A string representing which view from the Impact Dashboard FE to return data for (choice between "aggregated" or "comparison" views)
  - **Note**:
  All request params must be filled in for the different modes and views. For company mode fix view param to "comparison"
  
- **Response**: A dictionary representation of the sliced impact data.

  - **Example (mode:"cooling_unit", view:"comparison")**:

    **Request**:
    ```json
    {
        "company_id": 0,
        "cooling_unit_id": "4,7" ,
        "start_date": "2023-08-03",
        "end_date": "2023-03-04",
        "mode": "cooling_unit", 
        "view": "comparison"
    }
    ```

    **Response**:
  
      ```json
    {"Impact metrics":{"cooling_unit_id":[{"name":"Bremgarten 1.0","value":4},{"name":"Bremgarten 2.0","value":7}],"unit_name":[{"name":"Bremgarten 1.0","value":"Bremgarten 1.0"},{"name":"Bremgarten 2.0","value":0}],"baseline_quantity_total_month":[{"name":"Bremgarten 1.0","value":116.66666666666667},{"name":"Bremgarten 2.0","value":0}],"avg_baseline_kg_selling_price_month":[{"name":"Bremgarten 1.0","value":100.0},{"name":"Bremgarten 2.0","value":0}],"baseline_kg_loss_month":[{"name":"Bremgarten 1.0","value":16.666666666666668},{"name":"Bremgarten 2.0","value":0}],"baseline_kg_sold_month":[{"name":"Bremgarten 1.0","value":83.33333333333333},{"name":"Bremgarten 2.0","value":0}],"avg_baseline_perc_loss_month":[{"name":"Bremgarten 1.0","value":14.285714285714285},{"name":"Bremgarten 2.0","value":0}],"avg_baseline_farmer_revenue_month":[{"name":"Bremgarten 1.0","value":8333.333333333332},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_kg_selling_price":[{"name":"Bremgarten 1.0","value":250.0},{"name":"Bremgarten 2.0","value":0}],"monthly_kg_checkin":[{"name":"Bremgarten 1.0","value":150.0},{"name":"Bremgarten 2.0","value":0}],"monthly_kg_loss":[{"name":"Bremgarten 1.0","value":30.0},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_perc_loss":[{"name":"Bremgarten 1.0","value":20.0},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_perc_foodloss_evolution":[{"name":"Bremgarten 1.0","value":40.000000000000014},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_farmer_revenue":[{"name":"Bremgarten 1.0","value":30000.0},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_perc_revenue_increase_evolution":[{"name":"Bremgarten 1.0","value":260.00000000000006},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_perc_revenue_increase_evolution_2":[{"name":"Bremgarten 1.0","value":260.00000000000006},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_kg_selling_price_evolution":[{"name":"Bremgarten 1.0","value":150.0},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_perc_unit_selling_price_evolution":[{"name":"Bremgarten 1.0","value":150.0},{"name":"Bremgarten 2.0","value":0}],"avg_monthly_farmer_revenue_evolution":[{"name":"Bremgarten 1.0","value":21666.666666666668},{"name":"Bremgarten 2.0","value":0}],"latest_survey_date":[{"name":"Bremgarten 1.0","value":"2023-09-11T06:34:11.879170+00:00"},{"name":"Bremgarten 2.0","value":0}],"num_post_harvest_surveys":[{"name":"Bremgarten 1.0","value":1},{"name":"Bremgarten 2.0","value":0}],"possible_post_checkout_survey_room":[{"name":"Bremgarten 1.0","value":25},{"name":"Bremgarten 2.0","value":0}],"total_post_checkout_survey_unit":[{"name":"Bremgarten 1.0","value":21},{"name":"Bremgarten 2.0","value":0}]},"Co2_metrics":[{"cooling_unit_id":"4","co2_crops":{"co2_from":308.39349650000037,"co2_to":2580.813963062355},"company_id":"3"},{"cooling_unit_id":"7","co2_crops":{"co2_from":42.32434883000005,"co2_to":34.1670073770582},"company_id":"3"}]}
    ```
    
  - **Example (mode:"cooling_unit", view:"aggregated")**:

    **Request**:
    ```json
    {
        "company_id": 3,
        "cooling_unit_id": "4,7",
        "start_date": "2023-08-03",
        "end_date": "2023-03-04",
        "mode": "cooling_unit", 
        "view": "aggregated"
    }
    ```

    **Response**:
  
      ```json
    {"Impact metrics":{"cooling_unit_id":{"name":"Aggregate","value":4},"unit_name":{"name":"Aggregate","value":"Bremgarten 1.0"},"baseline_quantity_total_month":{"name":"Aggregate","value":116.66666666666667},"avg_baseline_kg_selling_price_month":{"name":"Aggregate","value":50.0},"baseline_kg_loss_month":{"name":"Aggregate","value":16.666666666666668},"baseline_kg_sold_month":{"name":"Aggregate","value":83.33333333333333},"avg_baseline_perc_loss_month":{"name":"Aggregate","value":7.142857142857142},"avg_baseline_farmer_revenue_month":{"name":"Aggregate","value":8333.333333333332},"avg_monthly_kg_selling_price":{"name":"Aggregate","value":125.0},"monthly_kg_checkin":{"name":"Aggregate","value":150.0},"monthly_kg_loss":{"name":"Aggregate","value":30.0},"avg_monthly_perc_loss":{"name":"Aggregate","value":10.0},"avg_monthly_perc_foodloss_evolution":{"name":"Aggregate","value":20.000000000000007},"avg_monthly_farmer_revenue":{"name":"Aggregate","value":30000.0},"avg_monthly_perc_revenue_increase_evolution":{"name":"Aggregate","value":130.00000000000003},"avg_monthly_perc_revenue_increase_evolution_2":{"name":"Aggregate","value":130.00000000000003},"avg_monthly_kg_selling_price_evolution":{"name":"Aggregate","value":75.0},"avg_monthly_perc_unit_selling_price_evolution":{"name":"Aggregate","value":75.0},"avg_monthly_farmer_revenue_evolution":{"name":"Aggregate","value":21666.666666666668},"latest_survey_date":{"name":"Aggregate","value":"2023-09-11T06:34:11.879170+00:00"},"num_post_harvest_surveys":{"name":"Aggregate","value":1},"possible_post_checkout_survey_room":{"name":"Aggregate","value":25},"total_post_checkout_survey_unit":{"name":"Aggregate","value":21}},"Co2_metrics":[{"cooling_unit_id":"Aggregate","company_id":"Aggregate","co2_crops":{"co2_from":350.7178453300004,"co2_to":2614.9809704394133}}]}
    ```
    
  - **Example (mode:"company", view:"comparison")**:

    **Request**:
    ```json
    {
        "company_id": 1,
        "cooling_unit_id": 4,
        "start_date": "2023-08-03",
        "end_date": "2023-03-04",
        "mode": "company", 
        "view": "comparison"
    }
    ```

    **Response**:
  
      ```json
    {"Impact metrics":[{"company_id":3,"unit_name":"Bremgarten 1.0","baseline_quantity_total_month":116.66666666666667,"avg_baseline_kg_selling_price_month":100.0,"baseline_kg_loss_month":16.666666666666668,"baseline_kg_sold_month":83.33333333333333,"avg_baseline_perc_loss_month":14.285714285714285,"avg_baseline_farmer_revenue_month":8333.333333333332,"avg_monthly_kg_selling_price":250.0,"monthly_kg_checkin":150.0,"monthly_kg_loss":30.0,"avg_monthly_perc_loss":20.0,"avg_monthly_perc_foodloss_evolution":40.000000000000014,"avg_monthly_farmer_revenue":30000.0,"avg_monthly_perc_revenue_increase_evolution":260.00000000000006,"avg_monthly_perc_revenue_increase_evolution_2":260.00000000000006,"avg_monthly_kg_selling_price_evolution":150.0,"avg_monthly_perc_unit_selling_price_evolution":150.0,"avg_monthly_farmer_revenue_evolution":21666.666666666668,"latest_survey_date":"2023-09-11T06:34:11.879170+00:00","num_post_harvest_surveys":1,"possible_post_checkout_survey_room":25,"total_post_checkout_survey_unit":21}],"Co2_metrics":[{"company_id":"3","co2_crops":"{'co2_from': 350.7178453300004, 'co2_to': 2614.9809704394133}","cooling_unit_id":"7"}]}
    ```

## Further Deployment Details 

There are two containers in the docker-compose project named web_api and scheduler. The first container exposes the fastAPI server to query the intermediate tables and return slices of the tables as dictionary types. The scheduler container runs cron jobs that periodically updates the intermediate tables. The cooling_unit_metrics and company_metrics tables are updated daily and the impact_view table at the end of every month.
