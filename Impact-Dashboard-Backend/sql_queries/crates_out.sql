-- This query extracts the number of check outs performed in a particular day as well
-- as total number of crates checked out in that given day.

SELECT
    acm.cooling_unit_id,
    MIN(acm.checkin_date) as checkin_date_for_checkout_crate,
    COUNT(*) as crates_out,
    COUNT(DISTINCT acm.checkout_id) as operations_out,
    SUM(acm.weight) as kg_out
FROM
    analytics_crate_movements acm
WHERE
    acm.checkout_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
    AND acm.checkout_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
GROUP BY
    acm.cooling_unit_id;
