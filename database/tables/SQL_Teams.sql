-- Table: public.teams

-- DROP TABLE IF EXISTS public.teams;

CREATE TABLE IF NOT EXISTS public.teams
(
    key_teams integer NOT NULL DEFAULT nextval('teams_key_teams_seq'::regclass),
    key_urban integer,
    team_manager integer,
    CONSTRAINT teams_pkey PRIMARY KEY (key_teams),
    CONSTRAINT key_urban_fk FOREIGN KEY (key_urban)
        REFERENCES public.urban_zones (key_urban) MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT team_manager_fk FOREIGN KEY (team_manager)
        REFERENCES public.users (key_user) MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.teams
    OWNER to postgres;