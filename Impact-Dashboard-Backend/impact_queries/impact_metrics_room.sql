-- This query computes the monthly impact metrics for the dashboard including farmer income evolution and food loss evolution


-- Baseline completed survey count
WITH baseline_completed_surveys as (
    SELECT
        scu.id, COUNT(*) as total_num_filled_in_surveys
    FROM user_farmersurvey ufs
    JOIN user_farmersurveycommodity ufsc on ufs.id = ufsc.farmer_survey_id
    JOIN user_farmer uf on ufs.farmer_id = uf.id
    LEFT JOIN user_farmer_companies ufcs on uf.id = ufcs.farmer_id
    LEFT JOIN
        user_company uc ON ufcs.company_id = uc.id
    LEFT JOIN
        storage_location sl ON uc.id = sl.company_id
    LEFT JOIN
        storage_coolingunit scu ON sl.id = scu.location_id
    WHERE
        ufs.date_filled_in < %(datetime_end)s
        AND scu.id is not null
    GROUP BY scu.id
),

-- This CTE computes the price per kg per checkout for a crop type for a farmer in a given cooling unit
survey_prices_checkout as (
    SELECT uf.id as farmer_id,
        oc.id as check_out_id,
        sc.id as storage_crop_id,
        scu.id as cooling_unit_id,
        AVG(oms.price) / NULLIF(AVG(oms.kg_in_unit), 0) AS selling_price,
        MAX(uu.first_name) as first_name,
        MAX(sc.name) as crop_name,
        MAX(sc.id) as crop_id,
        MAX(oms.date_filled_in) as latest_survey_date
    FROM operation_marketsurvey oms
    JOIN operation_checkout oc on oms.checkout_id = oc.id
    JOIN storage_crop sc on oms.crop_id = sc.id
    JOIN operation_movement om on oc.movement_id = om.id
    JOIN storage_produce sp on sc.id = sp.crop_id
    JOIN operation_checkin oci on sp.checkin_id = oci.id
    join user_user uu on (oci.owned_by_user_id = uu.id)
    join user_farmer uf on (uf.user_id = uu.id)
    JOIN user_farmer_cooling_units ufcu on uf.id = ufcu.farmer_id
    JOIN storage_coolingunit scu on ufcu.coolingunit_id = scu.id
    WHERE
        oms.date_filled_in >= %(datetime_start)s
        AND oms.date_filled_in < %(datetime_end)s
    GROUP BY uf.id, oc.id, scu.id, sc.id
),


-- This CTE computes the average post-checkout selling price for all crop-user combinations in a given month
cooling_unit_aggregated_survey_prices as (
SELECT spc.farmer_id,
	acm.cooling_unit_id,
    spc.first_name as first_name,
    AVG(selling_price) as selling_price,
    MAX(spc.storage_crop_id) as crop_id,
    MAX(spc.crop_name) as crop_name
FROM operation_checkout oc
JOIN operation_marketsurvey oms on oc.id = oms.checkout_id
JOIN storage_crop sc on oms.crop_id = sc.id
JOIN operation_movement om on oc.movement_id = om.id
JOIN storage_produce sp on sc.id = sp.crop_id
JOIN operation_checkin oci on sp.checkin_id = oci.id
join user_user uu on (oci.owned_by_user_id = uu.id)
join user_farmer uf on (uf.user_id = uu.id)
JOIN user_farmer_cooling_units ufcu on uf.id = ufcu.farmer_id
JOIN storage_coolingunit scu on ufcu.coolingunit_id = scu.id
join survey_prices_checkout spc on oc.id = spc.check_out_id AND spc.farmer_id = uf.id AND spc.cooling_unit_id = scu.id
inner join analytics_crate_movements acm on oc.id = acm.checkout_id AND acm.checkin_farmer = uf.id AND acm.cooling_unit_id = scu.id and acm.crop_id = sc.id
GROUP BY spc.farmer_id, spc.storage_crop_id, acm.cooling_unit_id, spc.first_name),

-- The total number of possible post-checkout surveys for each cooling unit
baseline_possible_surveys as (
    SELECT
        acm.cooling_unit_id,
        COUNT(DISTINCT acm.checkin_id) AS total_checkins,
        COUNT(DISTINCT  acm.crop_name) AS distinct_crops,
        COUNT(DISTINCT CONCAT(acm.checkin_farmer, '-', acm.crop_name)) AS num_of_possible_surveys
    FROM
        analytics_crate_movements acm
    WHERE
        acm.checkin_date < %(datetime_end)s -- include crate movements prior to the end date
        AND (acm.checkout_date IS NULL OR acm.checkout_date < %(datetime_end)s) -- also include checkout_date if it is not null
    GROUP BY acm.cooling_unit_id
),

-- The total number of filled in post-checkout surveys for each cooling unit
total_post_checkout_survey_count as (
    SELECT sco.coolingunit_id as cooling_unit_id,
        count(distinct oms.id) AS total_surveys
    FROM operation_marketsurvey oms
    JOIN operation_checkout oc on oms.checkout_id = oc.id
    JOIN operation_movement om on oc.movement_id = om.id
    JOIN user_operator uo on om.operator_id = uo.id
    JOIN user_user uu on uo.user_id = uu.id
    JOIN storage_coolingunit_operators sco on uu.id = sco.user_id
    WHERE
        oms.date_filled_in >= %(datetime_start)s
        AND oms.date_filled_in < %(datetime_end)s
    GROUP BY sco.coolingunit_id
),

-- Baseline metrics
baseline_survey as (
    SELECT
        scu.id AS cooling_unit_id ,
        scu.name AS cooling_unit_name,
        sc.name AS crop_name,
        MAX(sc.id) AS crop_id,
        uf.id AS farmer_id,
        uu.first_name AS first_name,
        MAX(sl.company_id) AS company_id,
        (AVG(ufsc.average_price) * AVG(ufsc.kg_in_unit)) AS baseline_prices,
        MIN(ufsc.quantity_sold) * 4 AS quantity_sold,
        MIN(ufsc.quantity_self_consumed) * 4 AS quantity_self_consumed,
        MAX(ufsc.quantity_total) * 4 AS quantity_total,
        MIN(ufsc.quantity_below_market_price) * 4 AS quantity_lost,
        COUNT(ufsc.id) AS num_of_surveys,
        COUNT(DISTINCT (ufc.farmer_id)) as num_baseline_survey,
        ufsc.currency as baseline_currency
    FROM
        user_farmersurveycommodity ufsc
    LEFT JOIN
        user_farmersurvey ufs ON ufsc.farmer_survey_id = ufs.id
    LEFT JOIN
        user_farmer uf ON ufs.farmer_id = uf.id
    LEFT JOIN
        user_farmer_cooling_units ufc ON uf.id = ufc.farmer_id
    LEFT JOIN
        storage_crop sc ON ufsc.crop_id = sc.id
    LEFT JOIN
        user_user uu ON uf.user_id = uu.id
    LEFT JOIN user_farmer_companies ufcs on uf.id = ufcs.farmer_id
    LEFT JOIN
        user_company uc ON ufcs.company_id = uc.id
    LEFT JOIN
        storage_location sl ON uc.id = sl.company_id
    LEFT JOIN
        storage_coolingunit scu ON sl.id = scu.location_id
    WHERE scu.id is not null
    GROUP BY
        scu.id, sc.name, uf.id, uu.first_name, ufsc.currency
)

---- Post check-out metrics
SELECT
    %(date_end)s as report_date,
    sc.cooling_unit_id AS cooling_unit_id,
    MAX(bs.cooling_unit_name) as unit_name,
    MAX(bs.company_id) AS company_id,
    uf.id AS farmer_id,
    oms.crop_id AS crop_id,
    uu.first_name AS first_name,
    uu.last_name AS last_name,
    scp.name AS crop_name,
    COALESCE(MAX(oms.currency), MAX(bs.baseline_currency)) AS currency,
    MAX(bs.quantity_total) AS baseline_quantity_total_month,
    MAX(bs.baseline_prices) AS baseline_kg_selling_price_month,
    MAX(bs.quantity_lost) AS baseline_kg_loss_month,
    (MAX(bs.quantity_lost)/MAX(bs.quantity_total)) * 100 AS baseline_perc_loss_month,
    MAX(bs.quantity_sold) AS baseline_kg_sold_month,
    (SUM(weight) - SUM(COALESCE(loss, 0)) * MAX(bs.baseline_prices)) AS baseline_farmer_revenue_month,
    MAX(COALESCE(casp.selling_price, 0)) AS monthly_kg_selling_price,
    SUM(weight) AS monthly_kg_checkin,
    SUM(COALESCE(loss, 0)) AS monthly_kg_loss,
    MAX(COALESCE(casp.selling_price, 0)) * (SUM(weight) - SUM(COALESCE(loss, 0))) AS monthly_farmer_revenue,
    MAX(COALESCE(casp.selling_price, 0)) - MAX(bs.baseline_prices) AS monthly_kg_selling_price_evolution,
    (((MAX(COALESCE(casp.selling_price, 0)))- MAX(bs.baseline_prices)) / MAX(bs.baseline_prices)) * 100 AS monthly_perc_unit_selling_price_evolution,
    ( (MAX(COALESCE(casp.selling_price, 0)) * (SUM(weight) - SUM(COALESCE(loss, 0)))) - ((SUM(weight) - SUM(COALESCE(loss, 0))) * MAX(bs.baseline_prices)) ) AS monthly_farmer_revenue_evolution,
    (( (MAX(COALESCE(casp.selling_price, 0)) * (SUM(weight) - SUM(COALESCE(loss, 0))))  - ((SUM(weight) - SUM(COALESCE(loss, 0))) * MAX(bs.baseline_prices)))  / ((SUM(weight) - SUM(COALESCE(loss, 0))) * MAX(bs.baseline_prices))) * 100 AS monthly_perc_farmer_revenue_evolution,
    (SUM(COALESCE(loss, 0)) / NULLIF(SUM(weight), 0)) * 100 AS monthly_perc_loss,
    ((SUM(COALESCE(loss, 0)) / NULLIF(SUM(weight), 0)) - (MAX(bs.quantity_lost) / MAX(bs.quantity_total)))  * 100 AS monthly_perc_foodloss_diff,
    CASE
        WHEN MAX(bs.quantity_lost) = 0
            THEN (SUM(COALESCE(loss, 0)) / NULLIF(SUM(weight), 0)) * 100
        ELSE (
            ((SUM(COALESCE(loss, 0)) / NULLIF(SUM(weight), 0)) - (MAX(bs.quantity_lost) / MAX(bs.quantity_total))) /
            (MAX(bs.quantity_lost) / MAX(bs.quantity_total))
        ) * 100
    END AS monthly_perc_foodloss_evolution,
    MAX(oms.date_filled_in) AS latest_survey_date,
    MAX(bcs.total_num_filled_in_surveys) as baseline_completed_surveys_room,
    MAX(bps.num_of_possible_surveys) as possible_post_checkout_survey_room,
    MAX(tpcs.total_surveys) as total_post_checkout_survey_unit
FROM storage_crate sc
JOIN storage_cratepartialcheckout scpc  on (sc.id = scpc.crate_id)
join operation_checkout oc on(oc.id = scpc.checkout_id)
JOIN operation_movement om on oc.movement_id = om.id
JOIN operation_marketsurvey oms on oms.checkout_id = oc.id
JOIN storage_produce sp on sp.id = sc.produce_id
JOIN operation_checkin oc2 on sp.checkin_id = oc2.id
join user_user uu on (oc2.owned_by_user_id = uu.id)
join user_farmer uf on (uf.user_id = uu.id)
JOIN storage_crop scp on scp.id = sp.crop_id
JOIN baseline_survey bs on sc.cooling_unit_id = bs.cooling_unit_id
    AND uf.id = bs.farmer_id
    AND scp.name = bs.crop_name
LEFT JOIN baseline_completed_surveys bcs on bcs.id = sc.cooling_unit_id
LEFT JOIN baseline_possible_surveys bps on bps.cooling_unit_id = sc.cooling_unit_id
LEFT JOIN total_post_checkout_survey_count tpcs on tpcs.cooling_unit_id = sc.cooling_unit_id
INNER JOIN cooling_unit_aggregated_survey_prices casp on casp.cooling_unit_id = sc.cooling_unit_id AND casp.farmer_id = uf.id AND casp.crop_name = scp.name
WHERE
    oms.date_filled_in >= %(datetime_start)s
    AND oms.date_filled_in < %(datetime_end)s
    AND
    (
       bs.baseline_currency = oms.currency
       OR (oms.currency IS NULL AND bs.baseline_currency IS NOT NULL)
   ) AND bs.quantity_lost IS NOT NULL
     AND bs.quantity_sold IS NOT NULL
     AND bs.quantity_total IS NOT NULL
     AND bs.baseline_prices IS NOT NULL
     AND bs.crop_id =  oms.crop_id
GROUP BY sc.cooling_unit_id, uf.id, uu.first_name, uu.last_name, scp.name, oms.crop_id;
