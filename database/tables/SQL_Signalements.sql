-- Table: public.signalements

-- DROP TABLE IF EXISTS public.signalements;

CREATE TABLE IF NOT EXISTS public.signalements
(
    key_signalement integer NOT NULL DEFAULT nextval('signalements_id_signalement_seq'::regclass),
    key_container integer,
    key_user integer,
    zone_urbaine character varying(80) COLLATE pg_catalog."default",
    description character varying(80) COLLATE pg_catalog."default",
    CONSTRAINT signalements_pkey PRIMARY KEY (key_signalement),
    CONSTRAINT signalements_id_container_fkey FOREIGN KEY (key_container)
        REFERENCES public.container (key) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT signalements_id_user_fkey FOREIGN KEY (key_user)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.signalements
    OWNER to postgres;