-- This query retrieves company details per company id. The return values are:
-- + id, country AND name - retrieved FROM the user_company table
-- + total_registered_users (all AND only female) - retrieved FROM user_serviceprovider merged with the company table
-- + cooling_user_count (all AND female) - retrieved by linking the company to its operators AND any farmers linked to those operators
--       (the active user count is basically a subset of this only containing users that performed a checkin)
-- + beneficiary count - retrieved by multiplying the cooling user count by a fixed value - ie 3

-- company details getting base details FROM user_company
WITH company_details as (
    SELECT c.id as company_id,
        c.country,
        c.name,
        c.logo,
        c.currency,
        count(
            CASE
                WHEN u.is_active = true THEN u.id
            END
        ) as total_registered_users,
        count(
            CASE
                WHEN u.gender = 'ma' and u.is_active = true THEN 1
            END
        ) as male_registered_users,
        count(
            CASE
                WHEN (u.gender = 'ot' OR u.gender IS NULL) and u.is_active = true THEN 1
            END
        ) as other_registered_users,
        count(
            CASE
                WHEN u.gender = 'fe' and u.is_active = true THEN 1
            END
        ) as female_registered_users
    FROM user_company c
        LEFT JOIN user_serviceprovider ru on c.id = ru.company_id
        LEFT JOIN user_user u on ru.user_id = u.id
    GROUP BY c.id,
        c.country,
        c.name
),

-- separate CTE for computing the cooling unit types
TypeCounts AS (
    SELECT
        sl.company_id,
        scu.cooling_unit_type,
        COUNT(scu.cooling_unit_type) AS type_count
    FROM
        storage_coolingunit scu
    LEFT JOIN
        storage_location sl ON scu.location_id = sl.id
    WHERE
        scu.cooling_unit_type IS NOT NULL AND scu.deleted = FALSE
    GROUP BY
        sl.company_id, scu.cooling_unit_type
),

cooling_unit_types AS (
SELECT
    company_id,
    jsonb_object_agg(cooling_unit_type, type_count) AS cooling_unit_types
FROM
    TypeCounts
GROUP BY
    company_id
),

-- separate CTE for computing company operators
company_operator_details as (SELECT uo.company_id,
       count(
        CASE
            when not uu.phone = ''  then 1
        END
           ) as operators,
       count(
        CASE
            when not uu.phone = '' AND uu.gender = 'fe'  then 1
        END
        ) as operators_female,
        count(
            CASE
                when not uu.phone = '' AND uu.gender = 'ma' then 1
            END
        ) as operators_male,
        count(
        CASE
            when not uu.phone = '' AND (uu.gender = 'ot' OR uu.gender IS NULL) then 1
        END
    ) as operators_other
FROM user_operator uo
LEFT JOIN user_company uc on uc.id = uo.company_id
LEFT JOIN user_user uu on uo.user_id = uu.id
WHERE
    uu.is_active = TRUE
GROUP BY uo.company_id),

-- Separate CTE for computing total check-ins
total_crates_stats as (
SELECT
    sl.company_id,
    COUNT(*) as crates_in,
    COUNT(DISTINCT acm.checkin_id) as operations_in,
    SUM(acm.weight) as kg_in,
    COUNT(CASE WHEN acm.checkout_date IS NOT NULL THEN 1 ELSE NULL END) as crates_out,
    COUNT(DISTINCT CASE WHEN acm.checkout_date IS NOT NULL THEN acm.checkin_id ELSE NULL END) as operations_out,
    SUM(CASE WHEN acm.checkout_date IS NOT NULL THEN acm.weight ELSE 0 END) as kg_out
FROM
    analytics_crate_movements acm
LEFT JOIN storage_coolingunit sc on acm.cooling_unit_id = sc.id
LEFT JOIN storage_location sl on  sc.location_id = sl.id
WHERE sc.deleted = FALSE AND sl.deleted = FALSE
GROUP BY
    sl.company_id
),

-- Separate CTE for room capacity metrics,
company_room_metrics as (
    SELECT l.company_id,
    SUM(u.capacity_in_metric_tons) as total_capacity_in_metric_tons,
    SUM(u.capacity_in_number_crates) as total_capacity_in_number_crates
FROM storage_coolingunit u,
    storage_location l
WHERE u.location_id = l.id AND u.deleted = FALSE
GROUP BY l.company_id
),

-- separate cooling user temp table as this needs to group the farmers by company
company_cooling_users as (
    SELECT c.id as company_id,
        count (*) as cooling_user_count,
        count(
            CASE
                -- to avoid the default cooling user
                WHEN u.gender = 'fe' then 1
            END
        ) as cooling_user_female_count,
        count(
            CASE
                -- to avoid the default cooling user
                WHEN u.gender = 'ma' then 1
            END
        ) as cooling_user_male_count,
        count(
            CASE
                -- to avoid the default cooling user
                when (u.gender = 'ot' OR u.gender IS NULL) then 1
            END
        ) as cooling_user_other_count,
        count(
            CASE
                WHEN ufs.user_type = 'FARMER' then 1
            END
        ) as farmers,
        count(
            CASE
                WHEN ufs.user_type = 'TRADER' then 1
            END
        ) as traders,
        sum(
            CASE
                WHEN c.country = 'NG' THEN 4.7
                WHEN c.country = 'IN' THEN 4.4
                WHEN c.country = 'PH' THEN 4.2
                ELSE 3
            END

    ) as beneficiary_count,
    sum(
            CASE
                WHEN c.country = 'NG' THEN 4.7 * 0.495 -- Female gender split ratios per country and global
                WHEN c.country = 'IN' THEN 4.4 * 0.484
                WHEN c.country = 'PH' THEN 4.2 * 0.492
                ELSE 3 * 0.4975
            END

    ) as beneficiary_count_female,
    sum(
            CASE
                WHEN c.country = 'NG' THEN 4.7 * 0.505 -- Male gender split ratios per country and global
                WHEN c.country = 'IN' THEN 4.4 * 0.516
                WHEN c.country = 'PH' THEN 4.2 * 0.508
                ELSE 3 * 0.5025
            END

    ) as beneficiary_count_male
    FROM
        user_company c
    JOIN user_operator o ON c.id = o.company_id
    JOIN user_farmer f ON o.id = f.created_by_id
    JOIN user_user u ON u.id = f.user_id
    LEFT JOIN user_farmersurvey ufs ON ufs.farmer_id = f.id
    GROUP BY c.id
)
-- select required fields by combining above two tables
SELECT  cds.company_id,
        cds.country,
        cds.name,
        cds.logo as company_logo,
        cds.currency as currency,
        cds.total_registered_users,
        cds.female_registered_users,
        cds.male_registered_users,
        cds.other_registered_users,
        ccus.cooling_user_count,
        ccus.cooling_user_female_count,
        ccus.cooling_user_male_count,
        ccus.cooling_user_other_count,
        ccus.beneficiary_count,
        ccus.beneficiary_count_male,
        ccus.beneficiary_count_female,
        ccus.farmers,
        ccus.traders,
        (ccus.cooling_user_count - (ccus.farmers + ccus.traders)) AS unspecified_usertype,
        cod.operators as company_ops,
        cod.operators_male as company_ops_male,
        cod.operators_female as company_ops_female,
        cod.operators_other as company_ops_other,
        tcs.crates_in as company_crates_in,
        tcs.operations_in as company_operations_in,
        tcs.kg_in as company_kg_in,
        tcs.crates_out as company_crates_out,
        tcs.operations_out as company_operations_out,
        tcs.kg_out as company_kg_out,
        crm.total_capacity_in_metric_tons as total_capacity_in_metric_tons,
        crm.total_capacity_in_number_crates as total_capacity_in_number_crates,
        cut.cooling_unit_types AS cooling_unit_types
FROM company_details cds
    LEFT JOIN company_cooling_users ccus USING(company_id)
    LEFT JOIN company_operator_details cod USING(company_id)
    LEFT JOIN total_crates_stats tcs USING(company_id)
    LEFT JOIN company_room_metrics crm USING(company_id)
    LEFT JOIN cooling_unit_types cut USING(company_id)
ORDER BY cds.company_id
