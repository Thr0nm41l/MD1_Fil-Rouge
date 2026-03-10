-- Table: public.measurements

-- DROP TABLE IF EXISTS public.measurements;

CREATE TABLE IF NOT EXISTS public.measurements
(
    key_measurements numeric NOT NULL,
    container_key integer NOT NULL,
    remplissage numeric(10,2) NOT NULL DEFAULT 0,
    temperature numeric,
    CONSTRAINT measurements_pkey PRIMARY KEY (key_measurements),
    CONSTRAINT measurements_container_key_fkey FOREIGN KEY (container_key)
        REFERENCES public.container (key) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.measurements
    OWNER to postgres;
-- Index: measurements_brin_idx

-- DROP INDEX IF EXISTS public.measurements_brin_idx;

CREATE INDEX IF NOT EXISTS measurements_brin_idx
    ON public.measurements USING brin
    (remplissage, temperature)
    WITH (pages_per_range=128, autosummarize=False)
    TABLESPACE pg_default;