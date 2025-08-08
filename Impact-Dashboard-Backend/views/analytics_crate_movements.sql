-- A view that provides a summarized result of all storage crates
-- For each crate it returns information about it self (crop, weight, price, etc)
-- it's checkin movements (such as checkin date, operator, farmer that checked it in, etc)
-- as well as checkout movement information (checkout date, operator, checkout survey loss and price, etc)

DROP view analytics_crate_movements;

CREATE OR REPLACE VIEW analytics_crate_movements AS
WITH

    -- 1. CTE for the average loss in kg and price per crop, per checkout
    avg_market_survey AS (
        SELECT
            scp.checkout_id as checkout_id,
            sp.crop_id AS crop_id,
            (SUM(ms.loss) / NULLIF(COUNT(sc.id), 0)) AS average_checkout_loss_in_kg,
            (SUM(ms.price) / NULLIF(COUNT(sc.id), 0)) AS average_checkout_survey_price
        FROM storage_cratepartialcheckout scp
        LEFT JOIN storage_crate AS sc ON (sc.id = scp.crate_id)
        LEFT JOIN storage_produce AS sp ON (sc.produce_id = sp.id)
        INNER JOIN operation_marketsurvey AS ms ON (scp.checkout_id = ms.checkout_id) -- inner join to filter results and remove rows without a market survey
        GROUP BY scp.checkout_id, sp.crop_id
        ),

    -- 2. CTE for pulling the checkout date of the checkout where a crate was fully checked out (as opposed to a partial checkout)
    maximum_checkout AS(
     	SELECT
            sc.id AS crate_id,
            MAX(om.date) AS max_checkout_date
        FROM storage_crate AS sc
        LEFT JOIN storage_cratepartialcheckout AS scp ON (sc.id = scp.crate_id)
   		LEFT JOIN operation_checkout AS cko ON (cko.id = scp.checkout_id)
   		LEFT JOIN operation_movement AS om ON (cko.movement_id = om.id)
   		WHERE sc.cmp_fully_checked_out = true
   		GROUP BY sc.id
    ),

    -- 3. CTE for all summarized checkout information as it needs to be joined with checkin date in the next query
    checkout_info as (
        select  sc.id,
                scp.checkout_id as checkout_id,
                om.date as checkout_date,
                scp.cooling_fees as checkout_price, -- Represents the cooling fees paid at the final checkout of this crate, before it is "fully checked out"
                sc.cmp_total_paid_in_cooling_fees as total_crate_cooling_fee, -- Represents the total amount paid in cooling fees for this crate, across all partial checkouts
                om.operator_id as checkout_operator,
                ms.average_checkout_loss_in_kg as checkout_loss_in_kg,
                ms.average_checkout_survey_price as checkout_survey_price
        from storage_crate sc
        LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id)
   		left join operation_checkout cko on(cko.id = scp.checkout_id)
        left outer join operation_movement om on (cko.movement_id = om.id)
        inner join maximum_checkout mc on (mc.crate_id = sc.id and mc.max_checkout_date = om.date) -- Joining on CTE #2 for final checkout dates
        left outer join storage_produce sp on (sc.produce_id = sp.id)
        left outer join avg_market_survey ms on (scp.checkout_id = ms.checkout_id AND sp.crop_id = ms.crop_id) -- Joining on CTE #1 for post-checkout survey info
    )

    -- Final query: Join storage crate with the checkin movements to get the checkin movement information.
    -- Then join with the checkout information on the storage crate id to get a combined view of both checkin and checkout information for each storage crate
    select  sc.id as storage_crate_id,
            sc.cooling_unit_id,
            sc.currency,
            sc.initial_weight as weight,
            sp.crop_id,
            scp.name as crop_name,
            cin.id as checkin_id,
            om.date as checkin_date,
            om.operator_id as checkin_operator,
            uu.id as checkin_user,
            uf.id as checkin_farmer, --creates changes in dataslicer
            fs.farmer_id as survey_farmer,-- everything here is organized by survey farmer
            cko.checkout_id,
            cko.checkout_date,
            cko.checkout_price,
            cko.total_crate_cooling_fee,
            cko.checkout_operator,
            cko.checkout_loss_in_kg,
            cko.checkout_survey_price
    from storage_crate sc
        left join checkout_info cko on (sc.id = cko.id) -- Joining on CTE #3 for checkout data
        left join storage_produce sp on (sc.produce_id = sp.id)
        left join storage_crop scp on (scp.id = sp.crop_id)
        left join operation_checkin cin on (sp.checkin_id = cin.id)
        left join operation_movement om on (cin.movement_id = om.id)
        left join user_user uu on (cin.owned_by_user_id = uu.id)
        left join user_farmer uf on (uf.user_id = uu.id)
        left join user_farmersurvey fs on (fs.farmer_id = uf.id)
