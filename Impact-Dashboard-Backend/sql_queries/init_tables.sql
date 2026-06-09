-- Create metrics tables for Impact Dashboard Backend
-- These tables store pre-computed metrics for the dashboard

-- Company metrics table
CREATE TABLE IF NOT EXISTS company_metrics (
    report_date DATE,
    company_id INT4 PRIMARY KEY,
    comp_name VARCHAR(255),
    comp_country BPCHAR(2),
    comp_cap_tons NUMERIC,
    comp_cap_num_crates INT4,
    cooling_unit_types JSONB,
    comp_op INT4,
    comp_op_fem INT4,
    comp_op_ma INT4,
    comp_op_ot INT4,
    currency BPCHAR(3),
    comp_reg_users INT4,
    comp_reg_users_ma INT4,
    comp_reg_users_fem INT4,
    comp_reg_users_ot INT4,
    comp_beneficiaries NUMERIC(8,2),
    comp_beneficiaries_fem NUMERIC(8,2),
    comp_beneficiaries_ma NUMERIC(8,2),
    comp_cool_users INT4,
    comp_cool_users_fem INT4,
    comp_cool_users_ma INT4,
    comp_cool_users_ot INT4,
    comp_farmers INT4,
    comp_traders INT4,
    comp_unspec_user_type INT4,
    comp_crates_in INT4,
    comp_ops_in INT4,
    comp_kg_in INT4,
    comp_crates_out INT4,
    comp_ops_out INT4,
    comp_kg_out INT4,
    comp_average_room_occupancy NUMERIC(8,2),
    comp_revenue NUMERIC(16,2),
    comp_revenue_usd NUMERIC(16,2)
);

-- Cooling unit metrics table
CREATE TABLE IF NOT EXISTS cooling_unit_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    report_date DATE NOT NULL,
    cooling_unit_id INT4 NOT NULL,
    unit_name TEXT NOT NULL,
    is_unit_deleted BOOLEAN NOT NULL,
    state TEXT,
    cool_unit_type TEXT NOT NULL,
    cap_tons INT4 NOT NULL,
    cap_num_crates INT4 NOT NULL,
    company_id INT4 NOT NULL,
    comp_name TEXT NOT NULL,
    comp_pricing TEXT NOT NULL,
    currency TEXT NOT NULL,
    room_op INT4 NOT NULL,
    room_op_fem INT4 NOT NULL,
    room_op_ma INT4 NOT NULL,
    room_op_ot INT4 NOT NULL,
    room_beneficiaries NUMERIC NOT NULL,
    room_beneficiaries_fem NUMERIC NOT NULL,
    room_beneficiaries_ma NUMERIC NOT NULL,
    room_active_users INT4 NOT NULL,
    room_active_user_ids INT4[] NOT NULL,
    room_active_fem INT4[] NOT NULL,
    room_active_ma INT4[] NOT NULL,
    room_active_ot INT4[] NOT NULL,
    room_crates_in INT4 NOT NULL,
    room_ops_in INT4 NOT NULL,
    room_kg_in INT4 NOT NULL,
    room_crates_out INT4 NOT NULL,
    room_ops_out INT4 NOT NULL,
    room_kg_out INT4 NOT NULL,
    average_room_occupancy NUMERIC NOT NULL,
    room_revenue NUMERIC NOT NULL,
    room_revenue_usd NUMERIC NOT NULL,
    check_in_crates_crop JSONB,
    check_in_kg_crop JSONB,
    check_out_crates_crop JSONB,
    check_out_kg_crop JSONB,
    tot_co2 FLOAT8,
    co2_crops JSONB
);

-- Create index on cooling_unit_metrics for faster queries
CREATE INDEX IF NOT EXISTS idx_cooling_unit_metrics_date ON cooling_unit_metrics(date);
CREATE INDEX IF NOT EXISTS idx_cooling_unit_metrics_cooling_unit_id ON cooling_unit_metrics(cooling_unit_id);
CREATE INDEX IF NOT EXISTS idx_cooling_unit_metrics_company_id ON cooling_unit_metrics(company_id);

-- Impact metrics table
CREATE TABLE IF NOT EXISTS impact_metrics (
    report_date DATE,
    cooling_unit_id INT8,
    unit_name TEXT,
    company_id INT8,
    farmer_id INT8,
    crop_id INT8,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    crop_name VARCHAR(255),
    currency TEXT,
    baseline_quantity_total_month FLOAT8,
    baseline_kg_selling_price_month NUMERIC,
    baseline_kg_loss_month FLOAT8,
    baseline_perc_loss_month FLOAT8,
    baseline_kg_sold_month FLOAT8,
    baseline_farmer_revenue_month FLOAT8,
    monthly_kg_selling_price FLOAT8,
    monthly_kg_checkin FLOAT8,
    monthly_kg_loss INT8,
    monthly_farmer_revenue FLOAT8,
    monthly_kg_selling_price_evolution FLOAT8,
    monthly_perc_unit_selling_price_evolution FLOAT8,
    monthly_farmer_revenue_evolution FLOAT8,
    monthly_perc_farmer_revenue_evolution FLOAT8,
    monthly_perc_loss FLOAT8,
    monthly_perc_foodloss_diff FLOAT8,
    monthly_perc_foodloss_evolution FLOAT8,
    latest_survey_date TIMESTAMPTZ,
    baseline_completed_surveys_room INT8,
    possible_post_checkout_survey_room INT8,
    total_post_checkout_survey_unit INT8
);

-- Create indexes on impact_metrics for faster queries
CREATE INDEX IF NOT EXISTS idx_impact_metrics_cooling_unit_id ON impact_metrics(cooling_unit_id);
CREATE INDEX IF NOT EXISTS idx_impact_metrics_company_id ON impact_metrics(company_id);
CREATE INDEX IF NOT EXISTS idx_impact_metrics_latest_survey_date ON impact_metrics(latest_survey_date);
