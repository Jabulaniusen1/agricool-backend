-- A view that provides a summarized result of all storage crates
-- For each crate it returns information about it self (crop, weight, price, etc)
-- it's checkin movements (such as checkin date, operator, farmer that checked it in, etc)
-- as well as checkout movement information (checkout date, operator, checkout survey loss and price, etc)

DROP view analytics_crate_movements;

CREATE OR REPLACE VIEW analytics_crate_movements_test AS


 WITH avg_market_survey as (
        SELECT
            scp.checkout_id as checkout_id,
            sp.crop_id as crop_id,
            (SUM(ms.loss) / NULLIF(count(sc.id), 0)) as average_checkout_loss_in_kg,
            (SUM(ms.price) / NULLIF(count(sc.id), 0)) as average_checkout_survey_price
        FROM
            storage_crate as sc
        LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id) 
        INNER JOIN
            storage_produce as sp
        ON (sc.produce_id = sp.id)
        LEFT JOIN
            operation_marketsurvey as ms 
        ON (scp.checkout_id = ms.checkout_id)
        GROUP BY
            scp.checkout_id,
            sp.crop_id
    ),

    -- New CTE for computing the average price per crate
    avg_price_per_crate as (
    SELECT
        cko.id AS checkout_id,
        (cko.cmp_total_amount / NULLIF(COUNT(sc.id), 0)) as avg_price_per_crate 
        
    FROM
        operation_checkout as cko 
    left join 
    	storage_cratepartialcheckout as scp 
    on scp.checkout_id = cko.id
    
    LEFT JOIN
        storage_crate as sc
    ON (sc.id = scp.crate_id)
    
    GROUP BY
        cko.id
    ),

    -- CTE for computing the names of the produce in the crates
    CTE_SCP_Name AS (
    SELECT
        scp.id AS crop_id,
        MAX(sc.id) AS crate_id,
        MAX(sp.id) AS produce_id,
        MAX(scp.name) AS crop_name
    FROM storage_crate as sc
    LEFT join storage_produce as sp on sp.id = sc.produce_id
    LEFT join storage_crop as scp on scp.id = sp.crop_id
    GROUP BY
        scp.id
    ),
    
    maximum_checkout as(
     	select  sc.id as crate_id,
                max(om.date) as max_checkout_date
    
        from storage_crate sc
        LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id) -- if A CRATE is 100% CHECKED out IT WILL STILL APPEAR HERE?
   		left join operation_checkout cko on(cko.id = scp.checkout_id)
   		left outer join operation_movement om on (cko.movement_id = om.id)
   		where sc.cmp_fully_checked_out = true
   		group by sc.id
    ),
    
    -- Create a temp table for the checkout information as it needs to join storage crates with checkout movements
    checkout_info as (
        select  sc.id,
                scp.checkout_id as checkout_id,
                sp.crop_id,
                om.date as checkout_date,
                cko.cmp_total_amount as checkout_price,
                cko.movement_id as movement_id,
                om.operator_id as checkout_operator,
                ms.average_checkout_loss_in_kg as checkout_loss_in_kg,
                ms.average_checkout_survey_price as checkout_survey_price
        from storage_crate sc
        LEFT JOIN storage_cratepartialcheckout scp  on (sc.id = scp.crate_id)
   		left join operation_checkout cko on(cko.id = scp.checkout_id)
        left outer join operation_movement om on (cko.movement_id = om.id)
        left outer join storage_produce sp on (sc.produce_id = sp.id)
        left outer join avg_market_survey ms on (scp.checkout_id = ms.checkout_id AND sp.crop_id = ms.crop_id)
        inner join maximum_checkout mc on (mc.crate_id = sc.id and mc.max_checkout_date = om.date)
    )
    

    -- Join storage crate with the checkin movements to get the checkin movement information. Additionally
    -- join that with the checkout information on the storage crate id to get a combined view of both checkin and
    -- checkout information for each storage crate
    select  sc.id as storage_crate_id,
            sc.cooling_unit_id,
            sc.currency,
            sc.initial_weight as weight,
            sp.crop_id,
            cin.id as checkin_id,
            om.date as checkin_date,
            om.operator_id as checkin_operator,
            uu.id as checkin_user,
            uf.id as checkin_farmer, --creates changes in dataslicer 
            fs.farmer_id as survey_farmer,-- everything here is organized by survey farmer
            cko.checkout_id,
            cko.checkout_date,
            cko.checkout_price,
            cko.checkout_operator,
            cko.checkout_loss_in_kg,
            cko.checkout_survey_price,
            apc.avg_price_per_crate, -- Added average price per crate from the new CTE
            csn.crop_name as crop_name
    from storage_crate sc
        left join checkout_info cko on (sc.id = cko.id)
        left join storage_produce sp on (sc.produce_id = sp.id)
        left join operation_checkin cin on (sp.checkin_id = cin.id)
        left join operation_movement om on (cin.movement_id = om.id)
        left join user_user uu on (cin.owned_by_user_id = uu.id)
        left join user_farmer uf on (uf.user_id = uu.id) 
        left join user_farmersurvey fs on (fs.farmer_id = uf.id)
        left join avg_price_per_crate apc on (apc.checkout_id = cko.checkout_id) -- Joining with the new CTE here
        left join CTE_SCP_Name csn on (csn.crop_id = sp.crop_id); -- Joining with the new CTE here)
