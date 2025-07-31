SELECT  sl.company_id,
        MAX(uc.currency) as currency_crate,
        SUM (acm.total_crate_cooling_fee) as company_total_revenue
FROM analytics_crate_movements acm
LEFT JOIN storage_coolingunit sc on acm.cooling_unit_id = sc.id
LEFT JOIN storage_location sl on  sc.location_id = sl.id
LEFT JOIN user_company uc on sl.company_id = uc.id
WHERE sc.deleted = FALSE AND sl.deleted = FALSE
GROUP BY sl.company_id;
