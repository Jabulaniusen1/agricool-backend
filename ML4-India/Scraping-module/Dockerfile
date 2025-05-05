#FROM is the base image for which we will run our application
FROM python:3.12-slim

# OS dependencies
RUN apt-get update && apt-get -y install cron dos2unix zlib1g-dev libjpeg-dev gcc chromium-driver

# Python dependencies
WORKDIR /Scraping-module
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Main app
COPY config.ini .
COPY requirements.txt .
COPY scraping.py .
COPY prediction.py .

# crontab
COPY crontab /etc/cron.d/crontab
RUN dos2unix /etc/cron.d/crontab && crontab /etc/cron.d/crontab && touch /var/log/cron.log

# Supervisor and its runtime command
COPY service_script.conf .
CMD ["supervisord","-c","./service_script.conf"]
