-- SEQUENCE: public.container_key_seq

-- DROP SEQUENCE IF EXISTS public.container_key_seq;

CREATE SEQUENCE IF NOT EXISTS public.container_key_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.container_key_seq
    OWNED BY public.container.key;

ALTER SEQUENCE public.container_key_seq
    OWNER TO postgres;

-- SEQUENCE: public.role_key_seq

-- DROP SEQUENCE IF EXISTS public.role_key_seq;

CREATE SEQUENCE IF NOT EXISTS public.role_key_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.role_key_seq
    OWNED BY public.role.key_role;

ALTER SEQUENCE public.role_key_seq
    OWNER TO postgres;


    
-- SEQUENCE: public.signalements_id_signalement_seq

-- DROP SEQUENCE IF EXISTS public.signalements_id_signalement_seq;

CREATE SEQUENCE IF NOT EXISTS public.signalements_id_signalement_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.signalements_id_signalement_seq
    OWNED BY public.signalements.key_signalement;

ALTER SEQUENCE public.signalements_id_signalement_seq
    OWNER TO postgres;

    
    
-- SEQUENCE: public.teams_key_teams_seq

-- DROP SEQUENCE IF EXISTS public.teams_key_teams_seq;

CREATE SEQUENCE IF NOT EXISTS public.teams_key_teams_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.teams_key_teams_seq
    OWNED BY public.teams.key_teams;

ALTER SEQUENCE public.teams_key_teams_seq
    OWNER TO postgres;

-- SEQUENCE: public.tournees_key_tournee_seq

-- DROP SEQUENCE IF EXISTS public.tournees_key_tournee_seq;

CREATE SEQUENCE IF NOT EXISTS public.tournees_key_tournee_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.tournees_key_tournee_seq
    OWNED BY public.tournees.key_tournee;

ALTER SEQUENCE public.tournees_key_tournee_seq
    OWNER TO postgres;

-- SEQUENCE: public.urban_zones_key_urban_seq

-- DROP SEQUENCE IF EXISTS public.urban_zones_key_urban_seq;

CREATE SEQUENCE IF NOT EXISTS public.urban_zones_key_urban_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.urban_zones_key_urban_seq
    OWNED BY public.urban_zones.key_urban;

ALTER SEQUENCE public.urban_zones_key_urban_seq
    OWNER TO postgres;

-- SEQUENCE: public.user_role_id_seq

-- DROP SEQUENCE IF EXISTS public.user_role_id_seq;

CREATE SEQUENCE IF NOT EXISTS public.user_role_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.user_role_id_seq
    OWNED BY public.user_role.key_user_role;

ALTER SEQUENCE public.user_role_id_seq
    OWNER TO postgres;

-- SEQUENCE: public.user_team_key_user_team_seq

-- DROP SEQUENCE IF EXISTS public.user_team_key_user_team_seq;

CREATE SEQUENCE IF NOT EXISTS public.user_team_key_user_team_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.user_team_key_user_team_seq
    OWNED BY public.user_team.key_user_team;

ALTER SEQUENCE public.user_team_key_user_team_seq
    OWNER TO postgres;

-- SEQUENCE: public.users_history_key_history_seq

-- DROP SEQUENCE IF EXISTS public.users_history_key_history_seq;

CREATE SEQUENCE IF NOT EXISTS public.users_history_key_history_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.users_history_key_history_seq
    OWNED BY public.users_history.key_history;

ALTER SEQUENCE public.users_history_key_history_seq
    OWNER TO postgres;

-- SEQUENCE: public.users_key_user_seq

-- DROP SEQUENCE IF EXISTS public.users_key_user_seq;

CREATE SEQUENCE IF NOT EXISTS public.users_key_user_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

ALTER SEQUENCE public.users_key_user_seq
    OWNED BY public.users.key_user;

ALTER SEQUENCE public.users_key_user_seq
    OWNER TO postgres;