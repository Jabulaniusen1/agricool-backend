SELECT
    sc1.cooling_unit_id,
    COALESCE(avg_data.T_storage_maintain, 3.5) as T_storage_maintain,
    COALESCE(CAST(sc1.value AS FLOAT), 8) as T_room, -- Convert to float before applying COALESCE
    COALESCE(CAST(sc1.set_point_value AS FLOAT), 5) as Tf_storage_cooldown,
    sc1.datetime_stamp
FROM
    storage_coolingunitspecifications sc1
JOIN
    (SELECT
         cooling_unit_id,
         AVG(value::FLOAT) as T_storage_maintain
     FROM
         (SELECT *,
                 ROW_NUMBER() OVER (PARTITION BY cooling_unit_id ORDER BY datetime_stamp DESC) as rn
          FROM storage_coolingunitspecifications
          WHERE cooling_unit_id = %(unit_id)s) as recent_records
     WHERE
         recent_records.rn <= 6
     GROUP BY
         cooling_unit_id) as avg_data
ON
    sc1.cooling_unit_id = avg_data.cooling_unit_id
WHERE
    sc1.cooling_unit_id = %(unit_id)s
ORDER BY
    sc1.datetime_stamp DESC
LIMIT 1;
