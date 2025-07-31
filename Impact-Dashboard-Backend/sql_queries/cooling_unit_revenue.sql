-- This query computes the revenue per day for each cooling unit

SELECT acm.cooling_unit_id,
       ROUND(SUM(acm.total_crate_cooling_fee)::NUMERIC, 2) AS revenue_room
FROM
    analytics_crate_movements acm
WHERE
    acm.checkout_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
    and acm.checkout_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
GROUP BY
    acm.cooling_unit_id;
