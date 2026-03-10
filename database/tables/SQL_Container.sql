-- Table: public.container

-- DROP TABLE IF EXISTS public.container;

CREATE TABLE IF NOT EXISTS public.container
(
    key integer NOT NULL DEFAULT nextval('container_key_seq'::regclass),
    latitude double precision,
    longitude double precision,
    coordonees double precision,
    type integer,
    "Last_Updated" date GENERATED ALWAYS AS ('2026-02-20 22:59:01.797663'::timestamp without time zone) STORED,
    CONSTRAINT container_pkey PRIMARY KEY (key)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.container
    OWNER to postgres;
-- Index: container_idx

-- DROP INDEX IF EXISTS public.container_idx;

CREATE UNIQUE INDEX IF NOT EXISTS container_idx
    ON public.container USING btree
    (key ASC NULLS LAST)
    INCLUDE(latitude, longitude, coordonees)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;