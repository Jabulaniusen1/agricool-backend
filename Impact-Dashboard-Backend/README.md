# Coldtivate Impact Dashboard ![Coldtivate](logos/coldtivate.svg)

## Description

This repository contains the data pipeline for the Coldtivate Impact Dashboard. It is a data collection program for the Coldtivate App and allows for the automatic generation of a report containing key indicators about the coldrooms that Coldtivate monitors. This data is pulled and used to update the front-end of the Dashboard

## Prerequisites

- Python 3.8^

## Configuration
Use `.env` to specify environment configuration. You can use `.env.example` as a template.

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
There are 2 dockerfiles in the base directory, 'Dockerfile' is for building up the FASTAPI to slice the metrics table while the 'Dockerfile.scheduler' is for building up the image with the cronjobs used to update the metric tables 'company_metrics', 'cooling_units_metrics', and 'impact_metrics'.
The docker-compose file combines these two services into a docker-compose image. 
Navigate (cd) into the root folder. Run the following command to build the docker image and spawn the containers

```commandline
docker-compose --env-file .env.prod up 
```
The company and cooling_unit metric tables are updated by the cronjob every day, the impact metric table is updated at the end of every month.

### View Creation
We currently implemented a view 'analytics_crate_movements' that helps combine all the checkin and checkout information into one view in order to make future queries simpler. If you need to edit this to add new fields, then the view can be recreated by editing the corresponding file and running the following command

```
python3 create_view.py -v analytics_crate_movements
```
*Note: In case you face errors, you might have to drop the view first and then recreate it.

If you want to add new views, just add their definition to the 'views' folder as a separate sql file. Calling the same command above but with the new sql filename will create the new view.

## Author
- [Divinefavour Odion](https://github.com/divineod)

## Contributors
These individuals designed the architecture and wrote the code for the first version of this repo. We built upon their work, fixing bugs and refactoring according to changing project requirements, finally we made the code-base production ready and documented.  
- [Ambarish Prakash](https://gitlab.com/ambarish-prakash)
- Fredrik Nestaas
- [Lucien Walewski](https://gitlab.com/lucienwalewski)
- [Shangen Li](joe@shang-en.li)

## Individual query description
Each query has a description of what it extracts as a comment on the top of the file. For more information on how its used, refer to the Indicator mapping table to see which indicators are based on it

## Indicator mappings
This table mentions for each indicator on the company_metrics, cooling_unit_metrics, and Impact_metrics tables the corresponding sql query in the `sql_queries` and `Impact_queries` folders.

### Company metrics Table

| Indicator Description          |    Sql Query Used     |
|--------------------------------|:---------------------:|
| report_date                    |          --           |
| currency                       |          --           |
| cooling_unit_types             |      company.sql      |
| company_id                     |      company.sql      |
| comp_unspec_user_type          |      company.sql      |
| comp_traders                   |      company.sql      |
| comp_revenue_usd               |  crate_movement.sql   |
| comp_revenue                   |  crate_movement.sql   |
| comp_reg_users_ot              |      company.sql      |
| comp_reg_users_ma              |      company.sql      |
| comp_reg_users_fem             |      company.sql      |
| comp_reg_users                 |      company.sql      |
| comp_ops_out                   |      company.sql      |
| comp_ops_in                    |      company.sql      |
| comp_op_ot                     |      company.sql      |
| comp_op_ma                     |      company.sql      |
| comp_op_fem                    |      company.sql      |
| comp_op                        |      company.sql      |
| comp_name                      |      company.sql      |
| comp_logo                      |      company.sql      |
| comp_kg_out                    |      company.sql      |
| comp_kg_in                     |      company.sql      |
| comp_farmers                   |      company.sql      |
| comp_crates_out                |      company.sql      |
| comp_crates_in                 |      company.sql      |
| comp_country                   |      company.sql      |
| comp_cool_users_ot             |      company.sql      |
| comp_cool_users_ma             |      company.sql      |
| comp_cool_users_fem            |      company.sql      |
| comp_cool_users                |      company.sql      |
| comp_cap_tons                  |      company.sql      |
| comp_cap_num_crates            |      company.sql      |
| comp_beneficiaries_ma          |      company.sql      |
| comp_beneficiaries_fem         |      company.sql      |
| comp_beneficiaries             |      company.sql      |
| comp_average_room_occupancy    | occupancy_company.sql |

### Cooling Unit metrics Table

| Indicator Description  |        Computation Used         |
|------------------------|:-------------------------------:|
| date                   |               --                |
| report_date            |               --                |
| cooling_unit_id        |        cooling_unit.sql         |
| room_revenue           |    cooling_unit_revenue.sql     |
| room_revenue_usd       |    cooling_unit_revenue.sql     |
| check_in_crates_crop   | checkin_crop_distributions.sql  |
| check_in_kg_crop       | checkin_crop_distributions.sql  |
| check_out_kg_crop      | checkout_crop_distributions.sql |
| check_out_crates_crop  | checkout_crop_distributions.sql |
| id                     |        cooling_unit.sql         |
| is_unit_deleted        |        cooling_unit.sql         |
| cap_tons               |        cooling_unit.sql         |
| cap_num_crates         |        cooling_unit.sql         |
| company_id             |        cooling_unit.sql         |
| room_op                |        cooling_unit.sql         |
| room_op_fem            |        cooling_unit.sql         |
| room_op_ma             |        cooling_unit.sql         |
| room_op_ot             |        cooling_unit.sql         |
| room_beneficiaries     |        active_users.sql         |
| room_beneficiaries_fem |        active_users.sql         |
| room_beneficiaries_ma  |        active_users.sql         |
| room_active_users      |        active_users.sql         |
| room_active_user_ids   |        active_users.sql         |
| room_active_fem        |        active_users.sql         |
| room_active_ma         |        active_users.sql         |
| room_active_ot         |        active_users.sql         |
| room_crates_in         |          crates_in.sql          |
| room_ops_in            |          crates_in.sql          |
| room_kg_in             |          crates_in.sql          |
| room_crates_out        |         crates_out.sql          |
| room_ops_out           |         crates_out.sql          |
| room_kg_out            |         crates_out.sql          |
| average_room_occupancy |       occupancy_room.sql        |
| unit_name              |        cooling_unit.sql         |
| currency               |        cooling_unit.sql         |
| state                  |        cooling_unit.sql         |
| cool_unit_type         |        cooling_unit-sql         |
| comp_name              |        cooling_unit.sql         |
| comp_pricing           |        cooling_unit.sql         |
| tot_co2                |         LCA/sql_queries         |
| co2_crops              |        LCA/sql_queries         |

### Impact metrics Table

| Indicator Description                    |     Computation Used     |
|------------------------------------------|:------------------------:|
| survey_date                              | impact_metrics_room.sql  |
| company_id                               | impact_metrics_room.sql  |
| farmer_id                                | impact_metrics_room.sql  |
| monthly_perc_loss                        | impact_metrics_room.sql  |
| monthly_perc_foodloss_reduction          | impact_metrics_room.sql  |
| cooling_unit_id                          | impact_metrics_room.sql  |
| crop_id                                  | impact_metrics_room.sql  |
| baseline_quantity_total                  | impact_metrics_room.sql  |
| baseline_kg_selling_price                | impact_metrics_room.sql  |
| baseline_kg_loss                         | impact_metrics_room.sql  |
| baseline_perc_loss                       | impact_metrics_room.sql  |
| baseline_kg_sold                         | impact_metrics_room.sql  |
| baseline_farmer_income                   | impact_metrics_room.sql  |
| monthly_kg_selling_price                 | impact_metrics_room.sql  |
| monthly_kg_checkin                       | impact_metrics_room.sql  |
| monthly_kg_loss                          | impact_metrics_room.sql  |
| monthly_farmer_revenue                   | impact_metrics_room.sql  |
| monthly_farmer_profit                    | impact_metrics_room.sql  |
| monthly_kg_selling_price_increase        | impact_metrics_room.sql  |
| monthly_perc_unit_selling_price_increase | impact_metrics_room.sql  |
| monthly_farmer_income_increase           | impact_metrics_room.sql  |
| monthly_perc_income_increase             | impact_metrics_room.sql  |
| first_name                               | impact_metrics_room.sql  |
| crop_name                                | impact_metrics_room.sql  |
| currency                                 | impact_metrics_room.sql  |

If there any questions in the indicators you can check the following resources:
- This [google sheet](https://docs.google.com/spreadsheets/d/1fzTH00M7_0DB18lbSxvuZ3bR3Smsv46y/edit#gid=546324656) here contains the logic behind all the different indicators.
- The sql queries for the data for each indicator can be found in the `sql_queries` and `Impact_queries` folders and each query should have information on what it extracts at the top of the file
- All extra data processing is done in the `indicator_reporter.py` using some methods from the `dataProcessor.py` and each method has documentation on what it is called with and what it does and returns
