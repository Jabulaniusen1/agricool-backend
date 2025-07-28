select
    cooling_unit_id,
    crop_id,
    crop_name,
    SUM(crate_weight) AS kg_checkin,
    COUNT(crate_weight) As num_crates
from view_relevant_checkins vrc
WHERE
    vrc.cooling_unit_id = %(unit_id)s AND
    vrc.checkin_date <= '%(year)s-%(month)s-%(day)s'
group by cooling_unit_id, crop_id, crop_name;
