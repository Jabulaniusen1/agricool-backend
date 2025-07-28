CREATE OR REPLACE VIEW view_relevant_checkins AS
-- This CTE computes the total number of crates checked-in up until the current day
WITH relevant_checkins AS (
    SELECT sc.cooling_unit_id,
        sc.id as crate_id,
        sc.weight as crate_weight,
        om.date as checkin_date,
        crop_id as crop_id
    FROM storage_crate sc
        JOIN storage_produce sp on(sc.produce_id = sp.id)
        JOIN operation_checkin oci on(sp.checkin_id = oci.id)
        JOIN operation_movement om on (oci.movement_id = om.id)
)

SELECT rci.crate_id as crate_id,
       rci.crate_weight as crate_weight,
       checkin_date as checkin_date,
       crop_id as crop_id,
       sc.name as crop_name,
       sc.harvested_today as harvested_today,
       sc.harvested_yesterday as harvested_yesterday,
       sc.harvested_day_before_yesterday as harvested_day_before_yesterday,
       sc.harvested_before as harvested_before,
       sc.size_selection_1 as size_selection_1,
       sc.size_selection_2 as size_selection_2,
       sc.size_selection_3 as size_selection_3,
       scu.id as cooling_unit_id,
       scu.capacity_in_number_crates as capacity_in_number_crates,
       oc.id as checkout_id
FROM relevant_checkins rci
    JOIN storage_coolingunit scu on (scu.id = rci.cooling_unit_id)
    LEFT JOIN storage_cratepartialcheckout scp  on (rci.crate_id = scp.crate_id)
    left join operation_checkout oc on(oc.id = scp.checkout_id)
    JOIN storage_crop sc on rci.crop_id = sc.id
where oc.id is null;

--drop view view_relevant_checkins;
