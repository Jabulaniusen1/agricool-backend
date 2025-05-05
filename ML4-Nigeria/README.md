# ML4market Nigeria - Instructions
This repository contains a production-ready Machine Learning model developed by EMPA for forecasting commodity prices in Nigeria.
## 1. Repository contents

```
.
├── README.md                                       > Contains instructions on what the repository contains, how to set up the modules and how to use them.
├── data                                            >> Contains all csv and excel files and model.pkl
|    ├── models                                     >> Folder with trained models
|    |      └── model.pbz2                          > Trained model
|    ├── tomato.xlsx                                > Scraped monthly tomato prices
|    ├── onion.xlsx                                 > Scraped monthly onion prices
|    ├── irish_potato.xlsx                          > Scraped monthly irish potato prices
|    ├── sweet_potato.xlsx                          > Scraped monthly sweet potato prices
|    ├── ripe_plantain.xlsx                         > Scraped monthly ripe plantain prices
|    ├── unripe_plantain.xlsx                       > Scraped monthly unripe plantain prices
|    ├── plantain.xlsx                              > Average between ripe and unripe plantain prices
|    ├── CPI.csv                                    > Scraped monthly Comsumer Prices Index feature
|    ├── CPI_NBS.xlsx                               > Downloaded Consumer Prices Index file from NBS portal
|    ├── crude.xlsx                                 > Scraped monthly Crude prices feature
|    ├── USDtoNaira.csv                             > Scraped monthly USD to Naira exchange rates feature
|    ├── USDtoNAIRA_YAHOO.csv                       > Downloaded USD to Naira Exchange rates from Yahoo site
|    ├── FOOD_PRICES_NBS.xlsx                       > Downloaded Commodity prices file from NBS portal
|    ├── states.csv                                 > File containing the state names
|    ├── Master_dataframe.csv                       > Raw unprocesses training data 
|    └── Master_encoded.csv                         > Pre-processed (encoded) data to be used by the ML model
|     
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

        docker build --tag ml4market-scraping-nigeria . #rename as required

    - This command should download all the required dependencies and libraries automatically.

3. Run the docker image (replace {PATH} with the path to this repository)
    - To run docker container in Interactive mode:

            docker run -it -p {HOST_PORT_CHOICE}:5000 -v {PATH}/ML4market-Nigeria/data:/Scraping-module/data ml4market-scraping-nigeria

    - To run docker container in Detached mode: **(Recommended)**

            docker run -d -p {HOST_PORT_CHOICE}:5000 -v {PATH}/ML4market-Nigeria/data:/Scraping-module/data ml4market-scraping-nigeria

4. Predictions can also be accessed via the terminal with the following command:
    ```
    curl -X POST -H "Content-Type: application/json" -d "{\"state\": \"Zamfara\", \"commodity\": \"Tomato\"}" http://localhost:{HOST_PORT_CHOICE}/prediction
    ```
    Or by running the `test_prediction_apy.py` script in the `Scraping-module` folder.

5. **Inputs:** The prediction module requires 2 parameters: `state and commodity`.
    - Valid commodities are: `Tomato, Onion, Sweet Potato, Irish Potato, Ripe Plantain, and Unripe Plantain`.
    - Valid state names can be found in `data/states.csv`
6. **Output:**  prediction module returns results in JSON format. The keys are: `'Request', 'Dates', 'Predictions'`. **`Predictions` contains a list of floats with the commodity price forecasts in Naira/Kg for 8 months corresponding to the months in `Dates`.** Model errors are calculated on terms of the Mean Absolute Percentage Error (MAPE).

7. A cronjob is set to execute the scraping script weekly on Mondays, Wednesdays, and Fridays at 20:00. The script will scrape the data reported the month before and update the data folder. The prediction module restart will restart 1 hour after the retraining module has been executed so that it can reflect the new model (if any).

## 4. Setting up Retraining Module

1. Move into Retraining-module folder: (Retraining Module)

        cd Retraining-module/

2. Run docker build command

        docker build --tag ml4market-retraining-nigeria . # (rename as required)

    -  This command should download all the required dependencies and libraries automatically.

3. Run the docker image (replace {PATH} with the path to this repository)
  - To run docker container in Interactive mode:

        docker run -it -v {PATH}/ML4market-Nigeria/data:/Retraining-module/data ml4market-retraining-nigeria

  - To run docker container in Detached mode: **(Recommended)**

        docker run -d -v {PATH}/ML4market-Nigeria/data:/Retraining-module/data ml4market-retraining-nigeria

4. Cronjob period is set to execute the retraining script on the 1st of each month at midnight. The script will use all the data from 2017 (from `data/Master_encoded.csv`) to train a new model and compare its performance with the old existing model. The model which gives the lowest overall MAPE will be used in the prediction module.