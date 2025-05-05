# Farmers-Dashboard-Backend ![Coldtivate](logos/coldtivate.svg)

## Description

This repository contains the data pipeline for the Coldtivate Farmers Dashboard. It is a data collection program for the Coldtivate App and allows for the automatic generation of a report containing key indicators about the coldrooms that Coldtivate monitors. This data is pulled and used to update the front-end of the Dashboard

## Prerequisites

- Python 3.8^

## Configuration
Use `.env` to specify environment configuration. You can use `.env.temp` as a template.

## Docker
[![Docker](https://img.shields.io/badge/Docker-Container-blue?logo=docker&logoColor=white)](https://www.docker.com/)

### Docker installation (skip if you already have Docker installed)

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
### Setting up the Docker containers
There are 2 dockerfiles in the Farmers-Dashboard-Backend directory, 'Dockerfile' is for building up the FASTAPI to slice the farmer metrics table while the 'Dockerfile.scheduler' is for building up the image with the cronjobs used to update the 'farmer_metrics' table.
The docker-compose file combines these two services into a docker-compose image. 
Navigate (cd) into the root folder. Run the following command to build the docker image and spawn the containers

```commandline
docker-compose --env-file .env.temp up 
```
The farmer_metric table is updated by the cronjob every day.

## Author
- [Divinefavour Odion](https://github.com/divineod)


## Individual query description
Each query has a description of what it extracts as a comment on the top of the file. For more information on how its used, refer to the Indicator mapping table to see which indicators are based on it

## Indicator mappings
This table mentions for each indicator on the farmer_metrics, the corresponding sql query in the `sql_queries` folder.


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


## Integration Guide
The integration guide located here: [here](INTEGRATION-GUIDE.md)  contains detailed instructions about building the Docker images and spawning the necessary containers for the Farmers dashboard. It contains information on the Architecture of the backend service and API documentation on the endpoints. Refer to the Integration guide when integrating the Backend with Coldtivate's Front-end.