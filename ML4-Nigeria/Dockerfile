###
## BASE STAGE – Aims to have the base for both the model build and the scrapping + prediction services final image
###
FROM python:3.9.7-slim AS base_stage

# OS dependencies
RUN apt-get update && apt-get -y install zlib1g-dev libjpeg-dev gcc g++ chromium-driver rsync

# Python dependencies
WORKDIR /app
RUN pip3 install --upgrade pip
RUN pip3 install pipenv
RUN pip install --upgrade pip setuptools wheel

COPY ./Pipfile* .
RUN pipenv install --dev

###
## RETRAINING STAGE – Aims to have the necessary code to generate the initial services state, including the price prediction model.
###
FROM base_stage AS retraining_stage

# Retraining pieces
COPY ./Retraining-module/config.ini ./config.ini
COPY ./Retraining-module/retraining.py ./
COPY ./data/ ./data/

# # Train the new model
# RUN python3 ./retraining.py

###
## FINAL STAGE – Aims to have the initial data state from the retraining process
###
FROM base_stage AS final_stage

ENV APP_DATA=/app/data/
ENV APP_DEFAULT_DATA=/app/default_data/

COPY --from=retraining_stage /app/data /app/default_data
COPY ./Retraining-module/*.py .
COPY ./Scraping-module/*.py .
COPY ./Scraping-module/FlaskProject/*.py .
COPY ./Scraping-module/config.ini .

# Supervisor and its runtime command
COPY ./entrypoint.sh /entrypoint.sh
ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["pipenv","run","python", "/app/prediction.py"]
