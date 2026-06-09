# Dashboard & Reporting Services Endpoints & Integration Guide

This document describes the setup, endpoints, and data flows for the dashboards and reporting microservices of the Agricool/Coldtivate platform:
1. **Farmers-Dashboard-Backend** (FastAPI)
2. **Impact-Dashboard-Backend** (FastAPI)
3. **App-Impact-Reporting** (Flask)

---

## 1. Local Setup & Running Instructions

These services run alongside the `Base-API` and connect directly to the shared PostGIS database.

### Port Mappings (Development)
- **Farmers Dashboard Backend**: `http://localhost:8003`
- **Impact Dashboard Backend**: `http://localhost:8001`
- **App-Impact-Reporting Service**: `http://localhost:8002`

### Database Configuration Environment Variables
Each microservice reads database access parameters from the environment. Ensure these match your postgres container settings:
```ini
DB_USERNAME=base
DB_PASSWORD=base
DB_HOST=db
DB_PORT=5432
DB_NAME=base
```

---

## 2. Farmers-Dashboard-Backend (FastAPI)

Queries database tables to aggregate operational telemetry metrics specifically scoped to a farmer user's inventory.

#### 1. Home Form
- **URL**: `/`
- **Method**: `GET`
- **Response**: Serves static testing `/index.html` template.

#### 2. Get Farmer Base Slice
- **URL**: `/farmer-base-slice/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `farmer` (str, required): The ID of the farmer.
- **Response (200 OK)**:
  ```json
  {
    "farmer_id": {"0": 12},
    "farmer_name": {"0": "Ali Adebayo"},
    "total_checkins": {"0": 15},
    "total_active_weight": {"0": 240.5}
  }
  ```

#### 3. Get Farmer Analytics Slice
- **URL**: `/farmer-slice/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `farmer_id` (str, required): Farmer's lookup ID.
  - `unit_ids` (str, required): Comma-separated list of cooling unit IDs (e.g. `"1,2"`).
  - `start_date` (str, required): YYYY-MM-DD format (e.g. `"2026-01-01"`).
  - `end_date` (str, required): YYYY-MM-DD format (e.g. `"2026-06-01"`).
- **Response (200 OK)**:
  Returns two dictionaries representing base stats and utilization percentages.
  ```json
  [
    {
      "farmer_id": {"0": 12},
      "total_kg_stored": {"0": 1200.5}
    },
    {
      "cooling_unit_id": {"0": 1},
      "utilization_percentage": {"0": 45.2}
    }
  ]
  ```

#### 4. Get Farmer Impact Slices
- **URL**: `/impact-slice/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `farmer_id_2` (str, required): Farmer ID.
  - `cooling_unit_id` (str, required): Comma-separated list of unit IDs (default: `"0,1"`).
  - `start_date` (str, required): YYYY-MM-DD
  - `end_date` (str, required): YYYY-MM-DD
- **Response (200 OK)**:
  ```json
  {
    "Aggregated": {
      "baseline_quantity_total_month": 350.0,
      "baseline_kg_loss_month": 45.0,
      "avg_baseline_farmer_revenue_month": 125000.0,
      "monthly_kg_checkin": 800.0,
      "avg_monthly_farmer_revenue": 340000.0,
      "avg_monthly_perc_loss": 2.1
    },
    "Top 5 Food Loss Evolution": {
      "Tomato": {
        "dates": ["Jan", "Feb", "Mar"],
        "loss": [25.0, 18.0, 10.0]
      }
    },
    "Top 5 Revenue Evolution": {
      "Tomato": {
        "dates": ["Jan", "Feb", "Mar"],
        "revenue": [80000, 110000, 150000]
      }
    },
    "Surveys": {
      "count": 4
    }
  }
  ```

---

## 3. Impact-Dashboard-Backend (FastAPI)

Designed for company managers and cooling service providers to aggregate wider coldroom and CO2 impact parameters.

#### 1. Home Form
- **URL**: `/`
- **Method**: `GET`
- **Response**: Serves testing UI.

#### 2. Get Company Slice
- **URL**: `/company-slice/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `company_id` (int, required): Target company ID.
- **Response (200 OK)**:
  ```json
  {
    "company_id": {"0": 1},
    "total_locations": {"0": 4},
    "total_cooling_units": {"0": 8},
    "active_users": {"0": 142}
  }
  ```

#### 3. Get Cooling Unit Slice
- **URL**: `/coolingunit-slice/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `unit_ids` (str, required): Comma-separated list of unit IDs (e.g. `"1,2"`).
  - `start_date` (str, required): YYYY-MM-DD
  - `end_date` (str, required): YYYY-MM-DD
- **Response (200 OK)**:
  ```json
  {
    "cooling_unit_id": {"0": 1, "1": 2},
    "occupancy_avg": {"0": 62.5, "1": 41.2},
    "total_revenue": {"0": 180000.0, "1": 95000.0}
  }
  ```

#### 4. Get Aggregated Company Impact & CO2 Metrics
- **URL**: `/impact-slice/`
- **Method**: `POST`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Request Body**:
  - `company_id` (int, optional): Company identifier (default: `0`).
  - `cooling_unit_id` (str, required): Comma-separated unit IDs (default: `"0,1"`).
  - `start_date` (str, required): YYYY-MM-DD
  - `end_date` (str, required): YYYY-MM-DD
  - `mode` (str): `"cooling_unit"` (default) or `"company"`.
  - `view` (str): `"aggregated"` (default) or `"comparison"`.
- **Response (200 OK - View: aggregated, Mode: cooling_unit)**:
  ```json
  {
    "Impact metrics": {
      "baseline_quantity_total_month": 1200.0,
      "baseline_kg_loss_month": 180.0,
      "avg_baseline_perc_loss_month": 15.0,
      "avg_baseline_farmer_revenue_month": 500000.0,
      "monthly_kg_checkin": 3500.0,
      "monthly_kg_loss": 70.0,
      "avg_monthly_perc_loss": 2.0,
      "avg_monthly_farmer_revenue": 1450000.0,
      "avg_monthly_perc_revenue_increase_evolution": 290.0,
      "avg_monthly_perc_foodloss_evolution": -86.6
    },
    "Co2_metrics": [
      {
        "company_id": "Aggregate",
        "cooling_unit_id": "Aggregate",
        "co2_crops": {
          "co2_from": 5800.5,
          "co2_to": 1200.2
        }
      }
    ]
  }
  ```

---

## 4. App-Impact-Reporting (Flask)

Flask application providing downloads of Excel spreadsheet analysis files detailing checked-in crates, checkouts, and customer indexes.

#### 1. Download Company Cooling Users List
- **URL**: `/company/<company_id>/cusers`
- **Method**: `GET`
- **Query Parameters**:
  - `only_active` (bool): If `true`, returns only active users (default: `"True"`).
- **Response (200 OK)**:
  - **Headers**:
    - `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
    - `Content-Disposition: attachment; filename=cooling_users_comp_id_<company_id>_date_<YY-MM-DD>.xlsx`
  - **Body**: Excel sheet binary stream.

#### 2. Download Company Usage Analysis Report
- **URL**: `/company/<company_id>/usage_analysis`
- **Method**: `GET`
- **Query Parameters**:
  - `cooling_unit_ids` (str): Comma-separated list of IDs to filter on.
  - `start_date` (str): YYYY-MM-DD filter starting date.
  - `end_date` (str): YYYY-MM-DD filter ending date.
- **Response (200 OK)**:
  - **Headers**:
    - `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
    - `Content-Disposition: attachment; filename=usage_analysis_comp_id_<company_id>_date_<YY-MM-DD>.xlsx`
  - **Body**: Excel sheet binary stream listing checked-in crates, including crop types, locations, and user mappings.

#### 3. Download Company Revenue Analysis Report
- **URL**: `/company/<company_id>/revenue_analysis`
- **Method**: `GET`
- **Query Parameters**:
  - `cooling_unit_ids` (str): Comma-separated unit IDs.
  - `start_date` (str): YYYY-MM-DD
  - `end_date` (str): YYYY-MM-DD
- **Response (200 OK)**:
  - **Headers**:
    - `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
    - `Content-Disposition: attachment; filename=revenue_analysis_comp_id_<company_id>_date_<YY-MM-DD>.xlsx`
  - **Body**: Excel sheet binary stream detailing checkout crates, cooling fee charges, and prices.
