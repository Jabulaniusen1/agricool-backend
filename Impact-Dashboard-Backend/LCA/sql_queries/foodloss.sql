select cooling_unit_id,
       (AVG(monthly_perc_loss) / 100) as average_foodloss
from impact_metrics im
where im.cooling_unit_id = %(unit_id)s
group by cooling_unit_id;
