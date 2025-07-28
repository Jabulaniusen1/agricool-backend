-- This query extracts the number of check ins performed in a particular day/year as well
-- as total number of crates checked in in that given day/year.

SELECT
    acm.cooling_unit_id,
    COUNT(*) as crates_in,
    COUNT(DISTINCT acm.checkin_id) as operations_in,
    SUM(acm.weight) as kg_in
FROM
    analytics_crate_movements acm
WHERE
    acm.checkin_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
    AND acm.checkin_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
    AND acm.checkin_operator IS NOT NULL
GROUP BY
    acm.cooling_unit_id;
