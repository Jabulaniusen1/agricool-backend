-- This query computes the  average occupancy across all rooms of a company since 01.10.2022 till current day

select company_id,
       AVG(average_room_occupancy) as average_company_room_occupancy
from cooling_unit_metrics cum
group by  company_id;
