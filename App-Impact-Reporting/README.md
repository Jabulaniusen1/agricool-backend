# App-Impact-Reporting

Repository to provide utilisation and impact reports for Coldtivate companys to be accessible in the Coldtivate app.


## 1. Repository content
Folder Structure:
    |
    |- air: App Impact Reporting Python Module
    |   |- main.py: Entry point plus service endpoint configuration and logic
    |   |- reporters: Classes to fetch and create the reports
    |   |- utils: Utility classes such as a DB connector
    |- test: Unit tests
    |- requirements.txt: Python packages requirements file
    |- Dockerfile & compose.yaml: Docker files to build and run the app


## 2. Requirements
You should create a virtual environment using conda (or similar) and the requirement.txt file. You also need to contact app@yourvcca.org to get credentials to access the PostgreSQL database on Azure.
Additionally if you wish to run it on Docker, docker needs to be installed.

## 3. Execution
### Local Execution without Docker:
The app can be brought up locally without docker by running it with flask directly. To do so first set the path of the flask app via:

`export FLASK_APP='./air/main.py'`

Then bring up the flask server via:

`flask run --debug`

### Execution with Docker:
The compose.yaml file specifies how to build and load the image. It can be run by using the command:

`docker-compose up`

### Running Unit tests:
The unit tests can be run by the following command:

`python -m unittest discover tests`

## 4. API Documentation

### Endpoint: /company/<company_id>/cusers

- **Method**: GET

- **Purpose**: Fetches a list of users for the given company. A query parameter can be used to filter the report to show only active users.

- **Request**:
    - Path Parameters:
        - company_id:  An integer representing the company's ID.
    - Query Parameters:
        - only_active: A boolean indicating if the report should contain only active users. **Default value is True**.

- **Response**: An xlsx file as an attachment with the reponse content_type as 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'. The xlsx file has the following columns:
    - First Name
    - Last Name
    - Phone Number
    - Gender
    - Parent Name
    - Date Joined
    - Total Number of Checked-in Crates
    - Latest Check In Date

- **Examples**:
    - /company/100/cusers
    - /company/100/cusers?only_active=False


### Endpoint: /company/<company_id>/usage_analysis

- **Method**: GET

- **Purpose**: Fetches the list of crates checked in for a given company. Query parameters can be used to filter the report for particular cooling units and/or for a given time frame.

- **Request**:
    - Path Parameters:
        - company_id:  An integer representing the company's ID.
    - Query Parameters:
        - cooling_unit_ids: A list of integers corresponding to cooling unit ids to filter on. If not provided, check-ins for all the cooling units for the company will be returned.
        - start_date: A date used to filter check-ins for the report. If provided, only check-ins on or after this date will be shown in the report. **The date should be in the formate "YYYY-MM-DD".**
        - end_date: A date used to filter check-ins for the report. If provided, only check-ins on or before this date will be shown in the report. **The date should be in the formate "YYYY-MM-DD".**

- **Response**: An xlsx file as an attachment with the reponse content_type as 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'. The xlsx file has the following columns:
    - Crate Id
    - Check-in Code
    - Check-in Date
    - Crop Name
    - Weight
    - Price per Crate
    - Currency
    - First Name
    - Last Name
    - Phone Number
    - Gender
    - Cooling Unit Name
    - Location Name

- **Examples**:
    - /company/100/usage_analysis
    - /company/100/usage_analysis?cooling_unit_ids=1,2,3
    - /company/100/usage_analysis?start_date=2023-08-13&end_date=2023-07-04
    - /company/100/usage_analysis?end_date=2023-10-29&cooling_unit_ids=15


### Endpoint: /company/<company_id>/revenue_analysis

- **Method**: GET

- **Purpose**: Fetches the list of crates checked out for a given company along with reveune collected. Query parameters can be used to filter the report for particular cooling units and/or for a given time frame.

- **Request**:
    - Path Parameters:
        - company_id:  An integer representing the company's ID.
    - Query Parameters:
        - cooling_unit_ids: A list of integers corresponding to cooling unit ids to filter on. If not provided, check-outs for all the cooling units for the company will be returned.
        - start_date: A date used to filter check-outs for the report. If provided, only check-outs on or after this date will be shown in the report. **The date should be in the formate "YYYY-MM-DD".**
        - end_date: A date used to filter check-outs for the report. If provided, only check-outs on or before this date will be shown in the report. **The date should be in the formate "YYYY-MM-DD".**

- **Response**: An xlsx file as an attachment with the reponse content_type as 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'. The xlsx file has the following columns:
    - Crate Id
    - Check-out Code
    - Check-out Date
    - Crop Name
    - Weight'
    - Check-out Price per Crate
    - Currency'
    - Check-out Price per Crate before Discount
    - Price Discount per Crate'
    - Days in Storage
    - Payment Type
    - First Name
    - Last Name
    - Phone Number
    - Gender
    - Cooling Unit Name
    - Location Name

- **Examples**:
    - /company/100/revenue_analysis
    - /company/100/revenue_analysis?cooling_unit_ids=1,2,3
    - /company/100/revenue_analysis?start_date=2023-08-13&end_date=2023-07-04
    - /company/100/revenue_analysis?end_date=2023-10-29&cooling_unit_ids=15