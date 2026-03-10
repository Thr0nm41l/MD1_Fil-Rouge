-- Table: public.tournees

-- DROP TABLE IF EXISTS public.tournees;

CREATE TABLE IF NOT EXISTS public.tournees
(
    key_tournee integer NOT NULL DEFAULT nextval('tournees_key_tournee_seq'::regclass),
    key_urban_zone integer,
    key_equipe integer,
	nom_equipe varchar(50),
    last_updated date,
    CONSTRAINT tournees_pkey PRIMARY KEY (key_tournee),
    CONSTRAINT tournee_teams_fk FOREIGN KEY (key_equipe)
        REFERENCES public.teams (key_teams) MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT tournee_urban_zone_fk FOREIGN KEY (key_urban_zone)
        REFERENCES public.urban_zones (key_urban) MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.tournees
    OWNER to postgres;