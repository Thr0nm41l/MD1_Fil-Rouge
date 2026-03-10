-- Table: public.users

-- DROP TABLE IF EXISTS public.users;

CREATE TABLE IF NOT EXISTS public.users
(
    key_user integer NOT NULL DEFAULT nextval('users_key_user_seq'::regclass),
    email character varying(50) COLLATE pg_catalog."default",
    nom character varying(50) COLLATE pg_catalog."default",
    prenom character varying(50) COLLATE pg_catalog."default",
    password character varying(50) COLLATE pg_catalog."default",
    CONSTRAINT users_pkey PRIMARY KEY (key_user)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.users
    OWNER to postgres;

ALTER TABLE IF EXISTS public.users
    ENABLE ROW LEVEL SECURITY;

ALTER TABLE IF EXISTS public.users
    FORCE ROW LEVEL SECURITY;
