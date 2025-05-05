#FROM is the base image for which we will run our application
FROM ubuntu
WORKDIR /Retraining-module
RUN apt-get update && apt-get -y install python3 python3-pip
RUN apt-get -y install libjpeg-dev
RUN apt-get -y install cron
RUN apt-get -y upgrade
COPY config.ini .
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY retraining.py /Retraining-module/retraining.py
COPY crontab /etc/cron.d/crontab
RUN apt-get update --fix-missing && apt-get -y install dos2unix
RUN dos2unix /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN crontab /etc/cron.d/crontab
RUN touch /var/log/cron.log
RUN chmod 0744 /Retraining-module/retraining.py
COPY service_script.conf .
CMD ["supervisord","-c","/Retraining-module/service_script.conf"]
