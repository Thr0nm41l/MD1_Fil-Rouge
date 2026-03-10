-- Table: public.users_history

-- DROP TABLE IF EXISTS public.users_history;

CREATE TABLE IF NOT EXISTS public.users_history
(
    key_history integer NOT NULL DEFAULT nextval('users_history_key_history_seq'::regclass),
    user_key integer,
    email character varying(50) COLLATE pg_catalog."default",
    nom character varying(50) COLLATE pg_catalog."default",
    prenom character varying(50) COLLATE pg_catalog."default",
    password character varying(50) COLLATE pg_catalog."default",
    valid_from date DEFAULT '2026-03-10 09:20:26.953781+00'::timestamp with time zone,
    valid_to date,
    is_current boolean DEFAULT true
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.users_history
    OWNER to postgres;
-- Index: logs_gin_idx

-- DROP INDEX IF EXISTS public.logs_gin_idx;

CREATE INDEX IF NOT EXISTS logs_gin_idx
    ON public.users_history USING gin
    (email COLLATE pg_catalog."default" gin_trgm_ops, nom COLLATE pg_catalog."default" gin_trgm_ops, prenom COLLATE pg_catalog."default" gin_trgm_ops, password COLLATE pg_catalog."default" gin_trgm_ops)
    WITH (fastupdate=True, gin_pending_list_limit=4194304)
    TABLESPACE pg_default;

-- Trigger: history_set_valid

-- DROP TRIGGER IF EXISTS history_set_valid ON public.users_history;

CREATE OR REPLACE TRIGGER history_set_valid
    BEFORE INSERT
    ON public.users_history
    FOR EACH ROW
    EXECUTE FUNCTION public.update_validity();