-- This query retrieves the base cooling unit properties, along with its location information.
-- Furthermore it also retrieves the pricing strategy FROM the storage_coolingunitcrop table

-- Extract pricing strategy for each cooling unit FROM the storage_coolingunitcrop table
WITH unit_pricing as (
    SELECT cc.cooling_unit_id,
        -- use MAX because there are multiple entries per cooling unit, but they should be the
        -- same as there is no way to set a different price per crop currently
        MAX(
            (
                CASE
                    WHEN sp.pricing_type = 'PERIODICITY' THEN ' per day'
                    ELSE ' fixed'
                END
            )
        ) as pricing_period
    FROM    storage_coolingunitcrop cc,
            storage_pricing sp
    WHERE   cc.cooling_unit_id is not NULL
            AND cc.pricing_id = sp.id
    GROUP BY cc.cooling_unit_id
)
-- Select the required fields FROM storage_coolingunit, storage_location AND the above unit pricing table
SELECT u.id as cooling_unit_id,
    u.name as unit_name,
    u.deleted as is_unit_deleted,
    l.state,
    l.company_id,
    u.cooling_unit_type,
    u.capacity_in_metric_tons,
    u.food_capacity_in_metric_tons,
    u.capacity_in_number_crates,
    count(
        CASE
            WHEN uu.is_active = true THEN uu.id
        END
    ) as operators,
    count(
        CASE
            when uu.gender = 'fe' and uu.is_active = true then 1
        END
    ) as operators_female,
    count(
        CASE
            when uu.gender = 'ma' and uu.is_active = true then 1
        END
    ) as operators_male,
        count(
        CASE
            when (uu.gender = 'ot' OR uu.gender IS NULL) and uu.is_active = true then 1
        END
    ) as operators_other,
    CONCAT(
        (
            CASE
                WHEN u.metric = 'CRATES' THEN 'Per Crate'
                ELSE 'Per KG'
            END
        ),
        up.pricing_period
    ) as pricing_strategy
FROM storage_coolingunit u
    LEFT JOIN unit_pricing up on (u.id = up.cooling_unit_id)
    LEFT JOIN storage_coolingunit_operators co on (co.coolingunit_id = u.id)
    LEFT JOIN user_user uu on (co.user_id = uu.id),
    storage_location l
WHERE u.location_id = l.id AND u.deleted = FALSE
GROUP BY u.id,
    l.state,
    l.company_id,
    pricing_strategy
ORDER BY u.id
