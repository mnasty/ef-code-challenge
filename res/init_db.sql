--data definition language file (using default database)

--create schema to store feature tables
CREATE SCHEMA IF NOT EXISTS features
    AUTHORIZATION postgres;

--create ds_clicks table
CREATE TABLE IF NOT EXISTS features.ds_clicks
(
    index bigint,
    offer_id bigint,
    clicked_at timestamp without time zone
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS features.ds_clicks
    OWNER to postgres;

-- Index: ix_features_ds_clicks_index
CREATE INDEX IF NOT EXISTS ix_features_ds_clicks_index
    ON features.ds_clicks USING btree
    (index ASC NULLS LAST)
    TABLESPACE pg_default;

--create ds_leads table
CREATE TABLE IF NOT EXISTS features.ds_leads
(
    index bigint,
    lead_uuid text COLLATE pg_catalog."default",
    requested double precision,
    loan_purpose text COLLATE pg_catalog."default",
    credit text COLLATE pg_catalog."default",
    annual_income double precision
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS features.ds_leads
    OWNER to postgres;

-- Index: ix_features_ds_leads_index
CREATE INDEX IF NOT EXISTS ix_features_ds_leads_index
    ON features.ds_leads USING btree
    (index ASC NULLS LAST)
    TABLESPACE pg_default;

--create ds_offers table
CREATE TABLE IF NOT EXISTS features.ds_offers
(
    index bigint,
    lead_uuid text COLLATE pg_catalog."default",
    offer_id bigint,
    apr double precision,
    lender_id bigint
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS features.ds_offers
    OWNER to postgres;

-- Index: ix_features_ds_offers_index
CREATE INDEX IF NOT EXISTS ix_features_ds_offers_index
    ON features.ds_offers USING btree
    (index ASC NULLS LAST)
    TABLESPACE pg_default;

