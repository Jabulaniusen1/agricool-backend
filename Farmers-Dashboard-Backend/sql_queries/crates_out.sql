-- This query extracts the number of check outs performed in a particular day as well
-- as total number of crates checked out in that given day.
SELECT
  acm.checkin_farmer as farmer_id,
  acm.cooling_unit_id as cooling_unit_id,
  COUNT(*) as crates_out,
  COUNT(DISTINCT acm.checkout_id) as operations_out,
  SUM(acm.weight) as kg_out
FROM
  analytics_crate_movements acm
WHERE
  acm.checkout_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
  AND acm.checkout_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
GROUP by
  acm.checkin_farmer,
  acm.cooling_unit_id;
