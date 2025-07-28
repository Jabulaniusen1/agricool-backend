create table farmer_metrics
(
    id                     serial
        primary key,
    date                   date      not null,
    report_date            date      not null,
    farmer_id              integer   not null,
    cooling_unit_id        integer   not null,
    gender                 text      not null,
    room_crates_in         integer   not null,
    room_ops_in            integer   not null,
    room_kg_in             integer   not null,
    room_crates_out        integer   not null,
    room_ops_out           integer   not null,
    room_kg_out            integer   not null,
    check_in_crates_crop   jsonb,
    check_in_kg_crop       jsonb,
    check_out_crates_crop  jsonb,
    check_out_kg_crop      jsonb
);