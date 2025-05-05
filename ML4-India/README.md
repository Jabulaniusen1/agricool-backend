# ML4market India - Instructions
This repository contains a production-ready Machine Learning model developed by MasterCard's AI Garage and EMPA for forecasting market prices in India.
## 1. Repository contents

```
.
├── README.md                                       > Contains instructions on what the repository contains, how to set up the modules and how to use them.
├── data                                            >> Contains all csv files and model.pkl
|    ├── Apple_price.csv                            > Scraped daily Apple prices
|    ├── Banana_price.csv                           > Scraped daily Banana prices
|    ├── Green Chilli_price.csv                     > Scraped daily Green Chilli prices
|    ├── Tomato_price.csv                           > Scraped daily Tomato prices
|    ├── Brent_csv.csv                              > Scraped daily Brent Oil prices
|    ├── USDINR.csv                                 > Scraped daily USD to INR conversion rates
|    ├── Function.py                                > Contains functions for handling data that are shared between both modules
|    ├── trained_model.pkl                          > Picke file of trained Catboost model
|    ├── Master_encoded.csv                         > Pre-processed (encoded) data to be used by the ML model
|    ├── Old.csv                                    > Scraped data prior to Sept 2021 (Jan'18-Aug'21)
|    ├── Valid_entries.csv                          > Valid State-District-Market-Commodity combinations
|    └── validMarkets.csv                           > Valid State-District-Market combinations
├── Scraping-module                                 >> Docker container for Prediction and Scraping modules
|    ├── FlaskProject                               >> Prediction module
|    |      └── prediction.py                       > Prediction module and command line API
|    ├── chromedriver                               > Webdriver to run the scraping script
|    ├── config.ini                                 > Configuration files with all the initialized values and paths
|    ├── crontab                                    > Sets the frequency for the periodic data scraping
|    ├── scraping.py                                > Scraping and pre-processing python script
|    ├── Dockerfile                                 > Instructions to create the Docker image
|    ├── google-chrome-stable_current_amd64.deb     
|    ├── re_start.sh                                > Shell script to restart prediction module after retraining so that the trained model in Flask API is up-to-date.
|    ├── requirements.txt                           > List of Python libraries required
|    ├── service_script.conf                        > Service script to run two services in parallel
|    └── test_prediction_api.py                     > Script for testing prediction API
└── Retraining-module                               >> Docker container for Retraining and Error modules       
     ├── config.ini                                 > Configuration files with all the initialized values and paths
     ├── crontab                                    > Set the frequency for the periodic retraining
     ├── Dockerfile                                 > Instructions to create the Docker image
     ├── requirements.txt                           > List of Python libraries required
     ├── retraining.py                              > Script to train model with latest data and compare with current model
     └── service_script.conf                        > Service script to run two services in parallel

```  

## 2. Docker installation (skip if you already have Docker installed)

Docker installation depends on the host OS. Please refer [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/) for OS specific instructions. The following example is for Linux 7 installation:

- Run the following commands on terminal
    1. sudo yum install -y yum-utils zip unzip
    2. sudo yum-config-manager --enable ol7\_optional\_latest
    3. sudo yum-config-manager --enable ol7\_addons
    4. sudo yum install -y oraclelinux-developer-release-el7
    5. sudo yum-config-manager --enable ol7\_developer
    6. sudo yum install -y docker-engine btrfs-progs btrfs-progs-devel
    7. sudo systemctl enable --now docker
    8. sudo chmod 666 /var/run/docker.sock

- Check if docker is properly installed by running the command:

        docker run hello-world

## 3. Setting up Prediction and Scraping Modules

1. Move into Scraping-module folder (the scraping and prediction module):

    	cd Scraping-module/

2.  Run docker build command

        docker build --tag ml4market-scraping . #rename as required

    - This command should download all the required dependencies and libraries automatically.

3. Run the docker image (replace {PATH} with the path to this repository)
    - To run docker container in Interactive mode:

            docker run -it -p {HOST_PORT_CHOICE}:5000 -v {PATH}/ML4market-India/data:/Scraping-module/data ml4market-scraping

    - To run docker container in Detached mode: **(Recommended)**

            docker run -d -p {HOST_PORT_CHOICE}:5000 -v {PATH}/ML4market-India/data:/Scraping-module/data ml4market-scraping

4. Predictions can also be accessed via the terminal with the following command:
    ```
    curl -X POST -H "Content-Type: application/json" -d "{\"state\":\"Himachal Pradesh\",\"district\":\"Bilaspur\",\"market\":\"Bilaspur\",\"commodity\":\"Tomato\", \"Available_values\": \"1\"}" http://localhost:{HOST_PORT_CHOICE}/prediction
    ```

5. **Inputs:** The prediction module requires 5 parameters: `state, district, market, commodity and Available_values`. 
    - **Note that the state-district-market must be a valid combination, which can be found in `data/validMarkets.csv`.** 
    - Valid commodities are: `Apple, Banana, Green Chilli, Tomato`.
    - Valid state-district-market-commodity combinations can be found on `data/Valid_entries.csv`
    - `Available_values` is a binary variable that controls whether only real data or also interpolated data should for reporting model Error. **A value of 1 means include interpolated data and 0 means only real data.** The recommended value to use is 1.
6. **Output:**  prediction module returns results in JSON format. The keys are: `'Request', 'Dates', 'Predictions', 'Last Available Error Observed', 'Last Available Value', 'Last Available Date', 'Last 2-month Error', 'Data Availability', 'Prediction Time', 'Result'`. **From these output only the `Predictions` key is relevant for now and it contains a list of floats with the market price forecasts in Rps/Quintal for 14 days corresponding to the dates in `Dates`.** Model errors are calculated on terms of the Mean Average Percentage Error (MAPE). There are three types of output:
    - The normal result would have a `'Result'` message `'Done'`.
    - If there are no data values for the market on the last 6 months the `'Result'` message will be `'No real data in the last 6 months, use predictions with caution'` and although predictions will still be given the `'Last Available Error Observed', 'Last Available Value', 'Last Available Date', 'Last 2-month Error', 'Data Availability'` keys with not be present in the output.
    - If the input parameters don't match any of those in `data/Valid_entries.csv` the `'Result'` message will be `'Not a valid state-district-market-commodity combination'`.
7. A cronjob is set to execute the scraping script daily at 0800. The script will scrape the data reported the day before and update the data folder. The prediction module restart will restart 30 mins after the retraining module has been executed so that it can reflect the new model (if any).

## 4. Setting up Retraining Module

1. Move into Retraining-module folder: (Retraining Module)

        cd Retraining-module/

2. Run docker build command

        docker build --tag ml4market-retraining . # (rename as required)

    -  This command should download all the required dependencies and libraries automatically.

3. Run the docker image (replace {PATH} with the path to this repository)
  - To run docker container in Interactive mode:

        docker run -it -v {PATH}/ML4market-India/data:/Retraining-module/data ml4market-retraining

  - To run docker container in Detached mode: **(Recommended)**

        docker run -d -v {PATH}/ML4market-India/data:/Retraining-module/data ml4maket-retraining

4. Cronjob period is set to execute the retraining script weekly at midnight. The script will use the last 3 years data (from `data/Old.csv` and `data/Master_encoded.csv`) to train a new model and compare its performance with the old existing model. The model which gives the lowest overal MAPE will be used in the prediction module.
