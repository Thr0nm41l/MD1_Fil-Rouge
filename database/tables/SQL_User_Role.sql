-- Table: public.user_role

-- DROP TABLE IF EXISTS public.user_role;

CREATE TABLE IF NOT EXISTS public.user_role
(
    key_user_role integer NOT NULL DEFAULT nextval('user_role_id_seq'::regclass),
    user_key integer,
    role_key integer,
    CONSTRAINT user_role_pkey PRIMARY KEY (key_user_role),
    CONSTRAINT user_role_role_number_fkey FOREIGN KEY (role_key)
        REFERENCES public.role (key_role) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT user_role_user_number_fkey FOREIGN KEY (user_key)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.user_role
    OWNER to postgres;

ALTER TABLE IF EXISTS public.user_role
    ENABLE ROW LEVEL SECURITY;

