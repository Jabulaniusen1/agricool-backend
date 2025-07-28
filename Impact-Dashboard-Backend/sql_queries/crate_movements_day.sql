-- Extract storage crate movement information from the analytics crate movements view
-- for any crate that was either + CHECKED IN in the given day or
--                               + CHECKED OUT in the given day

-- Extracting both allows flexibility in the python computation as well as reduces number of sql queries performed

SELECT  storage_crate_id,
        cooling_unit_id,
        currency,
        weight,
        crop_id,
        checkin_id,
        checkin_date,
        checkin_operator,
        checkin_farmer,
        checkout_id,
        checkout_date,
        checkout_price,
        checkout_operator,
        checkout_loss_in_kg,
        checkout_survey_price
FROM analytics_crate_movements
WHERE
    (
        checkin_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
        AND checkin_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
    )
    OR (
        checkout_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
        AND checkout_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
    )
