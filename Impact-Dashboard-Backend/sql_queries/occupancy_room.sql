-- This query computes the total occupancy of the rooms per day as the total crates still in the room by the specified date
-- minus the total crates checked out then divided by the specified maximum crate capacity in the room

-- This CTE computes the total number of crates checked-out up until the current day
WITH relevant_movements AS (
    SELECT id, date
    FROM operation_movement
    WHERE date <= '%(year)s-%(month)s-%(day)s 23:59:59' -- eod
),
relevant_checkouts AS (
    SELECT sc.cooling_unit_id,
           sc.id AS crate_id
    FROM storage_crate sc
    LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id) 
    left join operation_checkout cko on(cko.id = scp.checkout_id)
    JOIN relevant_movements om ON cko.movement_id = om.id
   	where sc.cmp_fully_checked_out = true
),
-- This CTE computes the total number of crates checked-in up until the current day
relevant_checkins AS (
    SELECT sc.cooling_unit_id,
           sc.id AS crate_id
    FROM storage_crate sc
    JOIN storage_produce sp ON sc.produce_id = sp.id
    JOIN operation_checkin oci ON sp.checkin_id = oci.id
    JOIN relevant_movements om ON oci.movement_id = om.id
),
checkins AS (
    SELECT cooling_unit_id, COUNT(*) AS total_checked_in
    FROM relevant_checkins
    GROUP BY cooling_unit_id
),
checkouts AS (
    SELECT cooling_unit_id, COUNT(*) AS total_checked_out
    FROM relevant_checkouts
    GROUP BY cooling_unit_id
)

SELECT
    scu.id AS cooling_unit_id,
    COALESCE(checkins.total_checked_in, 0) AS all_crates_checked_in,
    COALESCE(checkouts.total_checked_out, 0) AS all_crates_checked_out,
    COALESCE(checkins.total_checked_in, 0) - COALESCE(checkouts.total_checked_out, 0) AS crates_still_in_room,
    ROUND(
        (COALESCE(checkins.total_checked_in, 0) - COALESCE(checkouts.total_checked_out, 0))::decimal /
        NULLIF(scu.capacity_in_number_crates, 0) * 100,
        2
    ) AS occupancy_room
FROM
    storage_coolingunit scu
 JOIN checkins ON scu.id = checkins.cooling_unit_id
 JOIN checkouts ON scu.id = checkouts.cooling_unit_id
