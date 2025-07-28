-- This query returns the active cooling users and active female cooling users per cooling unit in the month
-- An active user is defined as someone who has at least one check-in or check-out in the month for the cooling unit
-- This query takes all crates checked-in or checked-out for the given month/year, and takes distinct of user ids and user genders
-- to return the value
WITH
    country_details AS (
        SELECT
            acm.cooling_unit_id,
            MAX(uc.country) AS country,
            MAX(
                CASE
                    WHEN uc.country = 'NG' then 4.7
                    WHEN uc.country = 'IN' then 4.4
                    WHEN uc.country = 'PH' then 4.2
                    WHEN uc.country is null then 3
                END
            ) AS pop_rate
        FROM
            analytics_crate_movements acm
            LEFT JOIN user_user u ON u.id = acm.checkin_user
            LEFT JOIN user_farmer uf ON u.id = uf.user_id
            LEFT JOIN operation_checkout oc ON oc.id = acm.checkout_id
            LEFT JOIN operation_movement om ON oc.movement_id = om.id
            LEFT JOIN user_operator uo ON uf.created_by_id = uo.id
            LEFT JOIN user_user checkout_u ON checkout_u.id = uo.user_id
            LEFT JOIN user_company uc ON uo.company_id = uc.id
        WHERE
            (
                (
                    acm.checkin_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
                    AND acm.checkin_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
                )
                OR (
                    acm.checkout_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
                    AND acm.checkout_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
                )
            )
        GROUP BY
            acm.cooling_unit_id
    )
SELECT
    acm.cooling_unit_id,
    COUNT(DISTINCT (u.id)) AS active_users,
    ARRAY_AGG (DISTINCT u.id) AS active_user_ids,
    ARRAY_AGG (
        DISTINCT CASE
            WHEN u.gender = 'fe' THEN u.id
        END
    ) AS active_users_female,
    ARRAY_AGG (
        DISTINCT CASE
            WHEN u.gender = 'ma' THEN u.id
        END
    ) AS active_users_male,
    ARRAY_AGG (
        DISTINCT CASE
            WHEN u.gender = 'ot' THEN u.id
        END
    ) AS active_users_other,
    COUNT(DISTINCT (uf.id)) * MAX(pop_rate) AS room_beneficiary,
    COUNT(DISTINCT uf.id) * MAX(cd.pop_rate) * CASE
        WHEN cd.country = 'NG' THEN 0.495
        WHEN cd.country = 'IN' THEN 0.484
        WHEN cd.country = 'PH' THEN 0.492
        ELSE 0.4975
    END AS room_beneficiary_female,
    -- Beneficiary Male
    COUNT(DISTINCT uf.id) * MAX(cd.pop_rate) * CASE
        WHEN cd.country = 'NG' THEN 0.505
        WHEN cd.country = 'IN' THEN 0.516
        WHEN cd.country = 'PH' THEN 0.508
        ELSE 0.5025
    END AS room_beneficiary_male
FROM
    analytics_crate_movements acm
    LEFT JOIN user_user u ON u.id = acm.checkin_user
    LEFT JOIN user_farmer uf ON u.id = uf.user_id
    LEFT JOIN operation_checkout oc ON oc.id = acm.checkout_id
    LEFT JOIN operation_movement om ON oc.movement_id = om.id
    LEFT JOIN user_operator uo ON uo.id = om.operator_id
    LEFT JOIN user_user checkout_u ON checkout_u.id = uo.user_id
    LEFT JOIN country_details cd ON cd.cooling_unit_id = acm.cooling_unit_id
WHERE
    (
        acm.checkin_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
        AND acm.checkin_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
    )
    OR (
        acm.checkout_date >= '%(year)s-%(month)s-%(day)s 00:00:00'
        AND acm.checkout_date <= '%(year)s-%(month)s-%(day)s 23:59:59'
    )
GROUP BY
    acm.cooling_unit_id,
    cd.country;
