-- Table: public.role

-- DROP TABLE IF EXISTS public.role;

CREATE TABLE IF NOT EXISTS public.role
(
    key_role integer NOT NULL DEFAULT nextval('role_key_seq'::regclass),
    nom character varying(50) COLLATE pg_catalog."default",
    CONSTRAINT role_pkey PRIMARY KEY (key_role)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.role
    OWNER to postgres;