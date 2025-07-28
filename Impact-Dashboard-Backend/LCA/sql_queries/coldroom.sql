WITH company_details as (
    SELECT c.id as company_id,
        c.country
    FROM user_company c
)
select scu.id,
       scu.name,
       scu.capacity_in_metric_tons,
       scu.capacity_in_number_crates,
       scu.metric,
       scu.sensor,
       scu.cooling_unit_type,
       scu.time_pickup_to_customer,
       scu.crate_length,
       scu.crate_width,
       scu.crate_height,
       scu.crate_weight,
       scu.location_id,
       scu.deleted,
       scu.food_capacity_in_metric_tons,
       scu.date_creation,
       scu.date_last_modified,
       scu.occupancy,
       scu.occupancy_modified_date,
       scu.public,
       sl.id as location_id,
       sl.company_id,
       cds.country
from storage_coolingunit scu
join storage_location sl on scu.location_id = sl.id
join company_details cds on sl.company_id = cds.company_id
where scu.id =  %(unit_id)s;
