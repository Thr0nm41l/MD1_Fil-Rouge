-- ============================================================
-- ECOTRACK — Full Database Setup
-- Run this script as the postgres superuser.
-- Creates the database, extensions, all tables (in dependency
-- order), sequences, indexes, functions, triggers, and policies.
-- ============================================================

-- ============================================================
-- 1. DATABASE
-- ============================================================

CREATE DATABASE "Ecotrack"
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE   = 'en_US.UTF-8'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

COMMENT ON DATABASE "Ecotrack" IS 'ECOTRACK — Plateforme intelligente de gestion des déchets urbains';

-- ============================================================
-- 2. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;        -- spatial geometry types and functions
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- trigram matching for GIN index on users_history

-- ============================================================
-- 3. ROLES / APPLICATION USER
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN;
    END IF;
END$$;

-- ============================================================
-- 4. SEQUENCES  (OWNED BY set in section 5.11 after all tables)
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS public.container_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.container_key_seq OWNER TO postgres;

-- measurements_key_seq is not in Sequences.sql (numeric PK, managed inline)
CREATE SEQUENCE IF NOT EXISTS public.measurements_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.measurements_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.role_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.role_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.signalements_id_signalement_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.signalements_id_signalement_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.teams_key_teams_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.teams_key_teams_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.tournees_key_tournee_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.tournees_key_tournee_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.urban_zones_key_urban_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.urban_zones_key_urban_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.user_role_id_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.user_role_id_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.user_team_key_user_team_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.user_team_key_user_team_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.users_history_key_history_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.users_history_key_history_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.users_key_user_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.users_key_user_seq OWNER TO postgres;

-- ============================================================
-- 5. TABLES (ordered by foreign-key dependencies)
-- ============================================================

-- ------------------------------------------------------------
-- 5.1  role  (no dependencies)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.role
(
    key_role integer      NOT NULL DEFAULT nextval('role_key_seq'::regclass),
    nom      varchar(50),
    CONSTRAINT role_pkey PRIMARY KEY (key_role)
);

ALTER TABLE IF EXISTS public.role OWNER TO postgres;

-- Seed the four application roles
INSERT INTO public.role (nom) VALUES
    ('User'),
    ('Worker'),
    ('Manager'),
    ('Admin')
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------
-- 5.2  urban_zones  (no dependencies)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.urban_zones
(
    key_urban   integer     NOT NULL DEFAULT nextval('urban_zones_key_urban_seq'::regclass),
    postal_code integer,
    name        varchar(40),
    CONSTRAINT urban_zones_pkey    PRIMARY KEY (key_urban),
    CONSTRAINT postal_code_unique  UNIQUE      (postal_code)
);

ALTER TABLE IF EXISTS public.urban_zones OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.3  users  (no dependencies — FK from teams references this)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.users
(
    key_user integer      NOT NULL DEFAULT nextval('users_key_user_seq'::regclass),
    email    varchar(50),
    nom      varchar(50),
    prenom   varchar(50),
    password varchar(50),
    CONSTRAINT users_pkey PRIMARY KEY (key_user)
);

ALTER TABLE IF EXISTS public.users OWNER TO postgres;
ALTER TABLE IF EXISTS public.users ENABLE  ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.users FORCE   ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 5.4  container  (no dependencies)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.container
(
    key          integer           NOT NULL DEFAULT nextval('container_key_seq'::regclass),
    latitude     double precision,
    longitude    double precision,
    coordonees   double precision,
    type         integer,
    last_updated timestamp         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT container_pkey PRIMARY KEY (key)
);

ALTER TABLE IF EXISTS public.container OWNER TO postgres;

CREATE UNIQUE INDEX IF NOT EXISTS container_idx
    ON public.container USING btree (key ASC NULLS LAST)
    INCLUDE (latitude, longitude, coordonees)
    WITH (fillfactor = 100, deduplicate_items = true);

-- ------------------------------------------------------------
-- 5.5  teams  (depends on: urban_zones, users)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.teams
(
    key_teams    integer NOT NULL DEFAULT nextval('teams_key_teams_seq'::regclass),
    key_urban    integer,
    team_manager integer,
    CONSTRAINT teams_pkey       PRIMARY KEY (key_teams),
    CONSTRAINT key_urban_fk     FOREIGN KEY (key_urban)
        REFERENCES public.urban_zones (key_urban) MATCH FULL
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT team_manager_fk  FOREIGN KEY (team_manager)
        REFERENCES public.users (key_user) MATCH FULL
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.teams OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.6  measurements  (depends on: container)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.measurements
(
    key_measurements numeric   NOT NULL DEFAULT nextval('measurements_key_seq'::regclass),
    container_key    integer   NOT NULL,
    remplissage      numeric(10,2) NOT NULL DEFAULT 0,
    temperature      numeric,
    CONSTRAINT measurements_pkey            PRIMARY KEY (key_measurements),
    CONSTRAINT measurements_container_key_fkey FOREIGN KEY (container_key)
        REFERENCES public.container (key) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.measurements OWNER TO postgres;

CREATE INDEX IF NOT EXISTS measurements_brin_idx
    ON public.measurements USING brin (remplissage, temperature)
    WITH (pages_per_range = 128, autosummarize = false);

-- ------------------------------------------------------------
-- 5.7  user_role  (depends on: users, role)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_role
(
    key_user_role integer NOT NULL DEFAULT nextval('user_role_id_seq'::regclass),
    user_key      integer,
    role_key      integer,
    CONSTRAINT user_role_pkey                PRIMARY KEY (key_user_role),
    CONSTRAINT user_role_user_number_fkey    FOREIGN KEY (user_key)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT user_role_role_number_fkey    FOREIGN KEY (role_key)
        REFERENCES public.role (key_role) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.user_role OWNER TO postgres;
ALTER TABLE IF EXISTS public.user_role ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 5.8  user_team  (depends on: users, teams)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_team
(
    key_user_team    integer NOT NULL DEFAULT nextval('user_team_key_user_team_seq'::regclass),
    key_user         integer,
    key_team         integer,
    affectation_date date,
    CONSTRAINT user_team_pkey     PRIMARY KEY (key_user_team),
    CONSTRAINT user_team_user_fk  FOREIGN KEY (key_user)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT user_team_team_fk  FOREIGN KEY (key_team)
        REFERENCES public.teams (key_teams) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.user_team OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.9  signalements  (depends on: container, users)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.signalements
(
    key_signalement integer     NOT NULL DEFAULT nextval('signalements_id_signalement_seq'::regclass),
    key_container   integer,
    key_user        integer,
    zone_urbaine    varchar(80),
    description     varchar(80),
    CONSTRAINT signalements_pkey              PRIMARY KEY (key_signalement),
    CONSTRAINT signalements_id_container_fkey FOREIGN KEY (key_container)
        REFERENCES public.container (key) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT signalements_id_user_fkey      FOREIGN KEY (key_user)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.signalements OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.10  tournees  (depends on: teams, urban_zones)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.tournees
(
    key_tournee  integer     NOT NULL DEFAULT nextval('tournees_key_tournee_seq'::regclass),
    key_urban_zone integer,
    key_equipe   integer,
    nom_equipe   varchar(50),
    last_updated date,
    CONSTRAINT tournees_pkey        PRIMARY KEY (key_tournee),
    CONSTRAINT tournee_teams_fk     FOREIGN KEY (key_equipe)
        REFERENCES public.teams (key_teams) MATCH FULL
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT tournee_urban_zone_fk FOREIGN KEY (key_urban_zone)
        REFERENCES public.urban_zones (key_urban) MATCH FULL
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.tournees OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.11  users_history  (depends on: users)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.users_history
(
    key_history integer     NOT NULL DEFAULT nextval('users_history_key_history_seq'::regclass),
    user_key    integer,
    email       varchar(50),
    nom         varchar(50),
    prenom      varchar(50),
    password    varchar(50),
    valid_from  timestamp   DEFAULT CURRENT_TIMESTAMP,
    valid_to    timestamp,
    is_current  boolean     DEFAULT true,
    CONSTRAINT users_history_pkey    PRIMARY KEY (key_history),
    CONSTRAINT users_history_user_fk FOREIGN KEY (user_key)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

ALTER TABLE IF EXISTS public.users_history OWNER TO postgres;

CREATE INDEX IF NOT EXISTS logs_gin_idx
    ON public.users_history USING gin
    (
        email    gin_trgm_ops,
        nom      gin_trgm_ops,
        prenom   gin_trgm_ops,
        password gin_trgm_ops
    )
    WITH (fastupdate = true, gin_pending_list_limit = 4194304);

-- ============================================================
-- 5.12  SEQUENCE OWNERSHIP  (requires all tables to exist)
-- ============================================================

ALTER SEQUENCE public.container_key_seq               OWNED BY public.container.key;
ALTER SEQUENCE public.measurements_key_seq            OWNED BY public.measurements.key_measurements;
ALTER SEQUENCE public.role_key_seq                    OWNED BY public.role.key_role;
ALTER SEQUENCE public.signalements_id_signalement_seq OWNED BY public.signalements.key_signalement;
ALTER SEQUENCE public.teams_key_teams_seq             OWNED BY public.teams.key_teams;
ALTER SEQUENCE public.tournees_key_tournee_seq        OWNED BY public.tournees.key_tournee;
ALTER SEQUENCE public.urban_zones_key_urban_seq       OWNED BY public.urban_zones.key_urban;
ALTER SEQUENCE public.user_role_id_seq                OWNED BY public.user_role.key_user_role;
ALTER SEQUENCE public.user_team_key_user_team_seq     OWNED BY public.user_team.key_user_team;
ALTER SEQUENCE public.users_history_key_history_seq   OWNED BY public.users_history.key_history;
ALTER SEQUENCE public.users_key_user_seq              OWNED BY public.users.key_user;

-- ============================================================
-- 6. FUNCTIONS  (must precede triggers and policies)
-- ============================================================

-- Returns the minimum (lowest-privilege) role key of the current user.
CREATE OR REPLACE FUNCTION public.get_user_role()
    RETURNS integer
    LANGUAGE sql
    STABLE PARALLEL UNSAFE
AS $$
    SELECT MIN(role_key)
    FROM public.user_role
    WHERE user_key = current_setting('app.current_user_id')::int
$$;

ALTER FUNCTION public.get_user_role() OWNER TO postgres;

-- Returns true if the current user holds the given role.
CREATE OR REPLACE FUNCTION public.has_role(role_id integer)
    RETURNS boolean
    LANGUAGE sql
    STABLE PARALLEL UNSAFE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_role
        WHERE user_key = current_setting('app.user_id', true)::int
          AND role_key = role_id
    )
$$;

ALTER FUNCTION public.has_role(integer) OWNER TO postgres;

-- Sets valid_from = NOW() on a new users_history row.
CREATE OR REPLACE FUNCTION public.update_validity()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
BEGIN
    NEW.valid_from := NOW();
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.update_validity() OWNER TO postgres;

-- Inserts a snapshot row into users_history.
CREATE OR REPLACE PROCEDURE public.insert_history(
    IN a integer,
    IN b varchar,
    IN c varchar,
    IN d varchar,
    IN e varchar
)
LANGUAGE sql
AS $$
    INSERT INTO public.users_history (user_key, email, nom, prenom, password)
    VALUES (a, b, c, d, e);
$$;

ALTER PROCEDURE public.insert_history(integer, varchar, varchar, varchar, varchar) OWNER TO postgres;

-- Trigger function called AFTER INSERT OR UPDATE on users.
CREATE OR REPLACE FUNCTION public.update_history_function()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
BEGIN
    PERFORM public.insert_history(NEW.key_user, NEW.email, NEW.nom, NEW.prenom, NEW.password);
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.update_history_function() OWNER TO postgres;

-- ============================================================
-- 7. users_history  (depends on: users + functions above)
-- ============================================================

-- Sets valid_from to the current timestamp on every new history row.
CREATE OR REPLACE TRIGGER history_set_valid
    BEFORE INSERT
    ON public.users_history
    FOR EACH ROW
    EXECUTE FUNCTION public.update_validity();

-- Automatically archives a snapshot whenever a user row is created or updated.
CREATE OR REPLACE TRIGGER users_archive_trigger
    AFTER INSERT OR UPDATE
    ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.update_history_function();

-- ============================================================
-- 8. POLICIES (Row Level Security)
-- ============================================================

-- user_role: app_user may only SELECT their own role mappings.
CREATE POLICY user_role_select_policy
    ON public.user_role
    AS PERMISSIVE FOR SELECT TO public
    USING (user_key = current_setting('app.user_id', true)::int);

-- users: fine-grained access by role.
CREATE POLICY admin_full_access
    ON public.users AS PERMISSIVE FOR ALL TO public
    USING      (get_user_role() = 4)
    WITH CHECK (get_user_role() = 4);

CREATE POLICY users_select_policy
    ON public.users AS PERMISSIVE FOR SELECT TO public
    USING (
        has_role(4)
        OR has_role(3)
        OR (key_user = current_setting('app.user_id', true)::int AND (has_role(1) OR has_role(2)))
    );

CREATE POLICY users_insert_policy
    ON public.users AS PERMISSIVE FOR INSERT TO public
    WITH CHECK (has_role(4) OR has_role(3));

CREATE POLICY users_update_policy
    ON public.users AS PERMISSIVE FOR UPDATE TO public
    USING      (has_role(4) OR key_user = current_setting('app.user_id', true)::int)
    WITH CHECK (has_role(4) OR key_user = current_setting('app.user_id', true)::int);

CREATE POLICY users_delete_policy
    ON public.users AS PERMISSIVE FOR DELETE TO public
    USING (has_role(4));

-- ============================================================
-- 9. GRANTS
-- ============================================================

REVOKE ALL ON TABLE public.user_role FROM app_user;
GRANT  SELECT                               ON TABLE public.user_role TO app_user;
GRANT  ALL                                  ON TABLE public.user_role TO postgres;

REVOKE ALL ON TABLE public.users FROM app_user;
GRANT  INSERT, DELETE, SELECT, UPDATE       ON TABLE public.users     TO app_user;
GRANT  ALL                                  ON TABLE public.users     TO postgres;
