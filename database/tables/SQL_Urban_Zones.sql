-- Table: public.urban_zones

-- DROP TABLE IF EXISTS public.urban_zones;

CREATE TABLE IF NOT EXISTS public.urban_zones
(
    key_urban integer NOT NULL DEFAULT nextval('urban_zones_key_urban_seq'::regclass),
    postal_code integer,
    name character varying(40) COLLATE pg_catalog."default",
    CONSTRAINT urban_zones_pkey PRIMARY KEY (key_urban),
    CONSTRAINT postal_code_unique UNIQUE (postal_code)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.urban_zones
    OWNER to postgres;