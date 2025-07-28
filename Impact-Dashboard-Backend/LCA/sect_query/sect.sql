WITH FirstOccurrences AS (
    SELECT
        cooling_unit_id,
        value::FLOAT,
        datetime_stamp,
        FIRST_VALUE(datetime_stamp) OVER (PARTITION BY cooling_unit_id ORDER BY datetime_stamp ASC) AS first_datetime_stamp,
        MIN(CASE WHEN value::FLOAT = %(Y)s THEN datetime_stamp ELSE NULL END) OVER (PARTITION BY cooling_unit_id) AS datetime_stamp_sect
    FROM
        storage_coolingunitspecifications
    WHERE
        cooling_unit_id = %(unit_id)s
)
SELECT
    cooling_unit_id,
    value::FLOAT,
    datetime_stamp,
    datetime_stamp_sect,
    first_datetime_stamp,
    CASE
        WHEN datetime_stamp_sect IS NOT NULL
        THEN EXTRACT(DAY FROM datetime_stamp_sect - first_datetime_stamp)
        ELSE NULL
    END AS days_to_sect
FROM
    FirstOccurrences
WHERE
    value::FLOAT = %(Y)s
ORDER BY
    datetime_stamp ASC
LIMIT 1;
