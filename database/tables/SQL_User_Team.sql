-- Table: public.user_team

-- DROP TABLE IF EXISTS public.user_team;

CREATE TABLE IF NOT EXISTS public.user_team
(
    key_user_team integer NOT NULL DEFAULT nextval('user_team_key_user_team_seq'::regclass),
    key_user integer,
    key_team integer,
    affectation_date date,
    CONSTRAINT user_team_pkey PRIMARY KEY (key_user_team)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.user_team
    OWNER to postgres;