-- ============================================================
-- ECOTRACK — Complete Database Setup
-- Covers all requirements: E1–E10
--   PostGIS geospatial, OLTP, OLAP/DW, IoT ingestion,
--   Analytics, Route optimisation, Gamification, ML support.
-- Run this script as the postgres superuser.
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

-- Switch into the new database before creating any objects.
-- All subsequent statements run inside "Ecotrack".
\c "Ecotrack"


-- ============================================================
-- 2. EXTENSIONS  (G1 / BDD1)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;            -- spatial geometry types & functions
CREATE EXTENSION IF NOT EXISTS pg_trgm;            -- trigram GIN indexes
CREATE EXTENSION IF NOT EXISTS btree_gin;          -- GIN support for B-tree operators
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- query-performance tracking


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
-- 4. SEQUENCES
-- ============================================================

-- OLTP
CREATE SEQUENCE IF NOT EXISTS public.role_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.role_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.zones_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.zones_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.users_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.users_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.container_type_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.container_type_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.containers_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.containers_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.device_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.device_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.teams_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.teams_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.user_role_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.user_role_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.user_team_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.user_team_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.signalements_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.signalements_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.routes_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.routes_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.route_steps_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.route_steps_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.collections_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.collections_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.notifications_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.notifications_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.users_history_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.users_history_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.dashboard_config_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.dashboard_config_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.reports_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.reports_key_seq OWNER TO postgres;

-- OLAP
CREATE SEQUENCE IF NOT EXISTS public.fill_history_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 100;
ALTER  SEQUENCE public.fill_history_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.agg_hourly_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.agg_hourly_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.agg_daily_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.agg_daily_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.ml_predictions_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.ml_predictions_key_seq OWNER TO postgres;

-- Gamification
CREATE SEQUENCE IF NOT EXISTS public.user_points_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.user_points_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.badges_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.badges_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.user_badges_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.user_badges_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.defis_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.defis_key_seq OWNER TO postgres;

CREATE SEQUENCE IF NOT EXISTS public.defi_participations_key_seq
    INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;
ALTER  SEQUENCE public.defi_participations_key_seq OWNER TO postgres;


-- ============================================================
-- 5. OLTP TABLES  (ordered by FK dependencies)
-- ============================================================

-- ------------------------------------------------------------
-- 5.1  role  (no dependencies)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.role
(
    key_role integer     NOT NULL DEFAULT nextval('role_key_seq'::regclass),
    name     varchar(50) NOT NULL,
    CONSTRAINT role_pkey        PRIMARY KEY (key_role),
    CONSTRAINT role_name_unique UNIQUE      (name)
);

ALTER TABLE IF EXISTS public.role OWNER TO postgres;

INSERT INTO public.role (name) VALUES
    ('User'),
    ('Worker'),
    ('Manager'),
    ('Admin')
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------
-- 5.2  zones  (no dependencies — PostGIS polygon)  [BDD2, G3]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.zones
(
    key_zone    integer                NOT NULL DEFAULT nextval('zones_key_seq'::regclass),
    postal_code integer,
    name        varchar(100),
    polygon     geometry(Polygon, 4326),
    CONSTRAINT zones_pkey          PRIMARY KEY (key_zone),
    CONSTRAINT zones_postal_unique UNIQUE      (postal_code)
);

ALTER TABLE IF EXISTS public.zones OWNER TO postgres;
COMMENT ON COLUMN public.zones.polygon IS 'Zone boundary — WGS84 polygon (SRID 4326)';

-- ------------------------------------------------------------
-- 5.3  users  (no dependencies)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.users
(
    key_user   integer      NOT NULL DEFAULT nextval('users_key_seq'::regclass),
    email      varchar(100) NOT NULL,
    name       varchar(50),
    first_name varchar(50),
    password   varchar(255) NOT NULL,
    created_at timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_pkey         PRIMARY KEY (key_user),
    CONSTRAINT users_email_unique UNIQUE      (email)
);

ALTER TABLE IF EXISTS public.users OWNER TO postgres;
ALTER TABLE IF EXISTS public.users ENABLE  ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.users FORCE   ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 5.4  container_type  (no dependencies)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.container_type
(
    key_type           integer      NOT NULL DEFAULT nextval('container_type_key_seq'::regclass),
    name               varchar(50)  NOT NULL,
    description        varchar(255),
    fill_threshold_pct numeric(5,2) NOT NULL DEFAULT 70.00,
    CONSTRAINT container_type_pkey        PRIMARY KEY (key_type),
    CONSTRAINT container_type_name_unique UNIQUE      (name)
);

ALTER TABLE IF EXISTS public.container_type OWNER TO postgres;

INSERT INTO public.container_type (name, description, fill_threshold_pct) VALUES
    ('Verre',     'Bouteilles et bocaux en verre',            80.00),
    ('Plastique', 'Emballages plastiques et PET',             70.00),
    ('Papier',    'Papier, carton et journaux',               75.00),
    ('Organique', 'Déchets alimentaires et de jardin',        65.00),
    ('Général',   'Ordures ménagères non triées',             70.00),
    ('Métal',     'Canettes, boîtes de conserve, ferraille',  80.00)
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------
-- 5.5  containers  (depends on: zones, container_type)  [BDD2, G2, C5]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.containers
(
    key_container      integer               NOT NULL DEFAULT nextval('containers_key_seq'::regclass),
    location           geometry(Point, 4326) NOT NULL,
    type_id            integer,
    zone_id            integer,
    capacity_liters    numeric(10,2)         NOT NULL DEFAULT 1000.00,
    fill_rate          numeric(5,2)          NOT NULL DEFAULT 0.00
                           CHECK (fill_rate >= 0 AND fill_rate <= 100),
    status             varchar(20)           NOT NULL DEFAULT 'empty'
                           CHECK (status IN ('empty', 'normal', 'full', 'critical')),
    fill_threshold_pct numeric(5,2)          NOT NULL DEFAULT 70.00,
    last_updated       timestamp             NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active          boolean               NOT NULL DEFAULT true,
    CONSTRAINT containers_pkey    PRIMARY KEY (key_container),
    CONSTRAINT containers_type_fk FOREIGN KEY (type_id)
        REFERENCES public.container_type (key_type) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT containers_zone_fk FOREIGN KEY (zone_id)
        REFERENCES public.zones (key_zone) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.containers OWNER TO postgres;
COMMENT ON COLUMN public.containers.location  IS 'GPS position — WGS84 point (SRID 4326)';
COMMENT ON COLUMN public.containers.fill_rate IS 'Current fill rate 0–100 %';
COMMENT ON COLUMN public.containers.status    IS 'Derived: empty(<25), normal(25-70), full(70-90), critical(>=90)';
COMMENT ON COLUMN public.containers.is_active IS 'Soft-delete flag — false = logically deleted (C5)';

-- ------------------------------------------------------------
-- 5.6  device  (depends on: containers)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.device
(
    key_device       integer      NOT NULL DEFAULT nextval('device_key_seq'::regclass),
    container_id     integer      NOT NULL,
    model            varchar(100),
    firmware_version varchar(50),
    battery_pct      numeric(5,2) CHECK (battery_pct >= 0 AND battery_pct <= 100),
    last_seen        timestamp,
    is_active        boolean      NOT NULL DEFAULT true,
    CONSTRAINT device_pkey         PRIMARY KEY (key_device),
    CONSTRAINT device_container_fk FOREIGN KEY (container_id)
        REFERENCES public.containers (key_container) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.device OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.7  teams  (depends on: zones, users)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.teams
(
    key_teams    integer      NOT NULL DEFAULT nextval('teams_key_seq'::regclass),
    zone_id      integer,
    team_manager integer,
    name         varchar(100),
    CONSTRAINT teams_pkey       PRIMARY KEY (key_teams),
    CONSTRAINT teams_zone_fk    FOREIGN KEY (zone_id)
        REFERENCES public.zones (key_zone) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT teams_manager_fk FOREIGN KEY (team_manager)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.teams OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.8  user_role  (depends on: users, role)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_role
(
    key_user_role integer NOT NULL DEFAULT nextval('user_role_key_seq'::regclass),
    user_key      integer NOT NULL,
    role_key      integer NOT NULL,
    CONSTRAINT user_role_pkey    PRIMARY KEY (key_user_role),
    CONSTRAINT user_role_unique  UNIQUE (user_key, role_key),
    CONSTRAINT user_role_user_fk FOREIGN KEY (user_key)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT user_role_role_fk FOREIGN KEY (role_key)
        REFERENCES public.role (key_role) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.user_role OWNER TO postgres;
ALTER TABLE IF EXISTS public.user_role ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 5.9  user_team  (depends on: users, teams)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_team
(
    key_user_team    integer NOT NULL DEFAULT nextval('user_team_key_seq'::regclass),
    key_user         integer NOT NULL,
    key_team         integer NOT NULL,
    affectation_date date    NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT user_team_pkey    PRIMARY KEY (key_user_team),
    CONSTRAINT user_team_unique  UNIQUE (key_user, key_team),
    CONSTRAINT user_team_user_fk FOREIGN KEY (key_user)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT user_team_team_fk FOREIGN KEY (key_team)
        REFERENCES public.teams (key_teams) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.user_team OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.10  signalements  (depends on: containers, users, zones)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.signalements
(
    key_signalement integer      NOT NULL DEFAULT nextval('signalements_key_seq'::regclass),
    container_id    integer,
    user_id         integer,
    zone_id         integer,
    description     varchar(500),
    status          varchar(30)  NOT NULL DEFAULT 'ouvert'
                        CHECK (status IN ('ouvert', 'en_traitement', 'resolu', 'ferme')),
    created_at      timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at     timestamp,
    CONSTRAINT signalements_pkey         PRIMARY KEY (key_signalement),
    CONSTRAINT signalements_container_fk FOREIGN KEY (container_id)
        REFERENCES public.containers (key_container) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT signalements_user_fk      FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT signalements_zone_fk      FOREIGN KEY (zone_id)
        REFERENCES public.zones (key_zone) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.signalements OWNER TO postgres;
ALTER TABLE IF EXISTS public.signalements ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 5.11  routes  (depends on: teams, zones)  [BDD2, T1]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.routes
(
    key_route    integer                     NOT NULL DEFAULT nextval('routes_key_seq'::regclass),
    zone_id      integer,
    team_id      integer,
    path         geometry(LineString, 4326),
    name         varchar(100),
    status       varchar(30)                 NOT NULL DEFAULT 'planifiee'
                     CHECK (status IN ('planifiee', 'en_cours', 'terminee', 'annulee')),
    scheduled_at date,
    started_at   timestamp,
    completed_at timestamp,
    distance_m   numeric(12,2),
    last_updated date                        NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT routes_pkey    PRIMARY KEY (key_route),
    CONSTRAINT routes_zone_fk FOREIGN KEY (zone_id)
        REFERENCES public.zones (key_zone) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT routes_team_fk FOREIGN KEY (team_id)
        REFERENCES public.teams (key_teams) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.routes OWNER TO postgres;
COMMENT ON COLUMN public.routes.path IS 'Route geometry — WGS84 LineString (SRID 4326)';

-- ------------------------------------------------------------
-- 5.12  route_steps  (depends on: routes, containers)  [T1]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.route_steps
(
    key_step           integer      NOT NULL DEFAULT nextval('route_steps_key_seq'::regclass),
    route_id           integer      NOT NULL,
    container_id       integer      NOT NULL,
    step_order         integer      NOT NULL,
    collected          boolean      NOT NULL DEFAULT false,
    collected_at       timestamp,
    volume_collected_l numeric(10,2),
    CONSTRAINT route_steps_pkey         PRIMARY KEY (key_step),
    CONSTRAINT route_steps_order_unique UNIQUE (route_id, step_order),
    CONSTRAINT route_steps_route_fk     FOREIGN KEY (route_id)
        REFERENCES public.routes (key_route) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT route_steps_container_fk FOREIGN KEY (container_id)
        REFERENCES public.containers (key_container) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.route_steps OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.13  collections  (depends on: containers, users, routes)  [T7]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.collections
(
    key_collection     integer      NOT NULL DEFAULT nextval('collections_key_seq'::regclass),
    container_id       integer      NOT NULL,
    agent_id           integer,
    route_id           integer,
    collected_at       timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fill_rate_before   numeric(5,2),
    fill_rate_after    numeric(5,2) NOT NULL DEFAULT 0.00,
    volume_collected_l numeric(10,2),
    CONSTRAINT collections_pkey         PRIMARY KEY (key_collection),
    CONSTRAINT collections_container_fk FOREIGN KEY (container_id)
        REFERENCES public.containers (key_container) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT collections_agent_fk     FOREIGN KEY (agent_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT collections_route_fk     FOREIGN KEY (route_id)
        REFERENCES public.routes (key_route) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.collections OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.14  notifications  (depends on: users, containers)  [C17]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.notifications
(
    key_notification integer     NOT NULL DEFAULT nextval('notifications_key_seq'::regclass),
    user_id          integer,
    container_id     integer,
    type             varchar(50) NOT NULL
                         CHECK (type IN ('threshold_breach', 'maintenance', 'route_assigned',
                                         'badge_earned', 'defi_completed', 'info')),
    title            varchar(200),
    content          text,
    is_read          boolean     NOT NULL DEFAULT false,
    created_at       timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notifications_pkey         PRIMARY KEY (key_notification),
    CONSTRAINT notifications_user_fk      FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT notifications_container_fk FOREIGN KEY (container_id)
        REFERENCES public.containers (key_container) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.notifications OWNER TO postgres;
ALTER TABLE IF EXISTS public.notifications ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 5.15  users_history  (depends on: users)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.users_history
(
    key_history integer      NOT NULL DEFAULT nextval('users_history_key_seq'::regclass),
    user_key    integer,
    email       varchar(100),
    name        varchar(50),
    first_name  varchar(50),
    password    varchar(255),
    valid_from  timestamp    DEFAULT CURRENT_TIMESTAMP,
    valid_to    timestamp,
    is_current  boolean      DEFAULT true,
    CONSTRAINT users_history_pkey    PRIMARY KEY (key_history),
    CONSTRAINT users_history_user_fk FOREIGN KEY (user_key)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.users_history OWNER TO postgres;

-- ------------------------------------------------------------
-- 5.16  dashboard_config  (depends on: users)  [DA4, DA5]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.dashboard_config
(
    key_config    integer   NOT NULL DEFAULT nextval('dashboard_config_key_seq'::regclass),
    user_id       integer   NOT NULL,
    layout_config jsonb     NOT NULL DEFAULT '{}',
    created_at    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dashboard_config_pkey        PRIMARY KEY (key_config),
    CONSTRAINT dashboard_config_user_fk     FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT dashboard_config_user_unique UNIQUE (user_id)
);

ALTER TABLE IF EXISTS public.dashboard_config OWNER TO postgres;
COMMENT ON COLUMN public.dashboard_config.layout_config IS 'JSON: selected charts, grid positions, saved filter preferences';

-- ------------------------------------------------------------
-- 5.17  reports  (depends on: users, zones)  [R1–R8]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.reports
(
    key_report   integer     NOT NULL DEFAULT nextval('reports_key_seq'::regclass),
    user_id      integer,
    zone_id      integer,
    report_type  varchar(30) NOT NULL
                     CHECK (report_type IN ('monthly', 'weekly', 'custom', 'zone', 'route')),
    format       varchar(10) NOT NULL DEFAULT 'pdf'
                     CHECK (format IN ('pdf', 'excel')),
    period_start date,
    period_end   date,
    file_path    varchar(500),
    status       varchar(20) NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'processing', 'ready', 'error')),
    created_at   timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reports_pkey    PRIMARY KEY (key_report),
    CONSTRAINT reports_user_fk FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT reports_zone_fk FOREIGN KEY (zone_id)
        REFERENCES public.zones (key_zone) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.reports OWNER TO postgres;


-- ============================================================
-- 6. OLAP TABLES
-- ============================================================

-- ------------------------------------------------------------
-- 6.1  fill_history  (partitioned by month)  [BDD3, BDD5, H1]
--      Core IoT time-series — ~500 000 rows / day, 12 months.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.fill_history
(
    key_history  bigint       NOT NULL DEFAULT nextval('fill_history_key_seq'::regclass),
    container_id integer      NOT NULL,
    device_id    integer,
    fill_rate    numeric(5,2) NOT NULL
                     CHECK (fill_rate >= 0 AND fill_rate <= 100),
    temperature  numeric(6,2),
    battery_pct  numeric(5,2) CHECK (battery_pct >= 0 AND battery_pct <= 100),
    is_outlier   boolean      NOT NULL DEFAULT false,
    measured_at  timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- measured_at must be part of PK for declarative range partitioning
    CONSTRAINT fill_history_pkey PRIMARY KEY (key_history, measured_at)
) PARTITION BY RANGE (measured_at);

ALTER TABLE IF EXISTS public.fill_history OWNER TO postgres;
COMMENT ON TABLE  public.fill_history IS 'Core IoT time-series, partitioned by month (BDD5). ~500 000 rows/day.';
COMMENT ON COLUMN public.fill_history.is_outlier IS 'True when the value is aberrant — kept for audit, excluded from aggregates';

-- Monthly partitions 2024
CREATE TABLE IF NOT EXISTS public.fill_history_2024_01 PARTITION OF public.fill_history FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_02 PARTITION OF public.fill_history FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_03 PARTITION OF public.fill_history FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_04 PARTITION OF public.fill_history FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_05 PARTITION OF public.fill_history FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_06 PARTITION OF public.fill_history FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_07 PARTITION OF public.fill_history FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_08 PARTITION OF public.fill_history FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_09 PARTITION OF public.fill_history FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_10 PARTITION OF public.fill_history FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_11 PARTITION OF public.fill_history FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2024_12 PARTITION OF public.fill_history FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- Monthly partitions 2025
CREATE TABLE IF NOT EXISTS public.fill_history_2025_01 PARTITION OF public.fill_history FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_02 PARTITION OF public.fill_history FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_03 PARTITION OF public.fill_history FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_04 PARTITION OF public.fill_history FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_05 PARTITION OF public.fill_history FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_06 PARTITION OF public.fill_history FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_07 PARTITION OF public.fill_history FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_08 PARTITION OF public.fill_history FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_09 PARTITION OF public.fill_history FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_10 PARTITION OF public.fill_history FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_11 PARTITION OF public.fill_history FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2025_12 PARTITION OF public.fill_history FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Monthly partitions 2026
CREATE TABLE IF NOT EXISTS public.fill_history_2026_01 PARTITION OF public.fill_history FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_02 PARTITION OF public.fill_history FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_03 PARTITION OF public.fill_history FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_04 PARTITION OF public.fill_history FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_05 PARTITION OF public.fill_history FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_06 PARTITION OF public.fill_history FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_07 PARTITION OF public.fill_history FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_08 PARTITION OF public.fill_history FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_09 PARTITION OF public.fill_history FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_10 PARTITION OF public.fill_history FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_11 PARTITION OF public.fill_history FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE IF NOT EXISTS public.fill_history_2026_12 PARTITION OF public.fill_history FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- Catch-all for data outside pre-created ranges
CREATE TABLE IF NOT EXISTS public.fill_history_default PARTITION OF public.fill_history DEFAULT;

-- ------------------------------------------------------------
-- 6.2  aggregated_hourly_stats  (OLAP — hourly rollup)  [H3]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.aggregated_hourly_stats
(
    key_stat          integer      NOT NULL DEFAULT nextval('agg_hourly_key_seq'::regclass),
    container_id      integer      NOT NULL,
    zone_id           integer,
    hour_bucket       timestamp    NOT NULL,
    avg_fill_rate     numeric(5,2),
    min_fill_rate     numeric(5,2),
    max_fill_rate     numeric(5,2),
    measurement_count integer      NOT NULL DEFAULT 0,
    CONSTRAINT agg_hourly_pkey   PRIMARY KEY (key_stat),
    CONSTRAINT agg_hourly_unique UNIQUE (container_id, hour_bucket)
);

ALTER TABLE IF EXISTS public.aggregated_hourly_stats OWNER TO postgres;

-- ------------------------------------------------------------
-- 6.3  aggregated_daily_stats  (OLAP — daily rollup)  [BDD4, H4]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.aggregated_daily_stats
(
    key_stat          integer      NOT NULL DEFAULT nextval('agg_daily_key_seq'::regclass),
    container_id      integer      NOT NULL,
    zone_id           integer,
    day_bucket        date         NOT NULL,
    avg_fill_rate     numeric(5,2),
    min_fill_rate     numeric(5,2),
    max_fill_rate     numeric(5,2),
    overflow_count    integer      NOT NULL DEFAULT 0,
    collection_count  integer      NOT NULL DEFAULT 0,
    measurement_count integer      NOT NULL DEFAULT 0,
    CONSTRAINT agg_daily_pkey   PRIMARY KEY (key_stat),
    CONSTRAINT agg_daily_unique UNIQUE (container_id, day_bucket)
);

ALTER TABLE IF EXISTS public.aggregated_daily_stats OWNER TO postgres;

-- ------------------------------------------------------------
-- 6.4  ml_predictions  (OLAP — model output)  [BDD4, ML5]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.ml_predictions
(
    key_prediction      integer      NOT NULL DEFAULT nextval('ml_predictions_key_seq'::regclass),
    container_id        integer      NOT NULL,
    predicted_at        timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    horizon_hours       integer      NOT NULL DEFAULT 24,
    predicted_fill_rate numeric(5,2) NOT NULL,
    actual_fill_rate    numeric(5,2),
    model_version       varchar(50),
    CONSTRAINT ml_predictions_pkey PRIMARY KEY (key_prediction)
);

ALTER TABLE IF EXISTS public.ml_predictions OWNER TO postgres;
COMMENT ON COLUMN public.ml_predictions.actual_fill_rate IS 'Filled ex-post to evaluate model accuracy (RMSE/MAE/R²)';


-- ============================================================
-- 7. GAMIFICATION TABLES  [GAM1]
-- ============================================================

-- ------------------------------------------------------------
-- 7.1  user_points  (cumulative point ledger per user)  [GAM2]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_points
(
    key_points   integer     NOT NULL DEFAULT nextval('user_points_key_seq'::regclass),
    user_id      integer     NOT NULL,
    action_type  varchar(50) NOT NULL,
    points       integer     NOT NULL,
    reference_id integer,
    earned_at    timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_points_pkey    PRIMARY KEY (key_points),
    CONSTRAINT user_points_user_fk FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.user_points OWNER TO postgres;
COMMENT ON COLUMN public.user_points.action_type  IS 'E.g. signalement(+10), eco_action(+5), defi_completed, badge_earned';
COMMENT ON COLUMN public.user_points.reference_id IS 'Optional FK to the triggering entity (signalement, collection, defi)';

-- ------------------------------------------------------------
-- 7.2  badges  (catalogue — 30+ badges)  [GAM5]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.badges
(
    key_badge     integer      NOT NULL DEFAULT nextval('badges_key_seq'::regclass),
    name          varchar(100) NOT NULL,
    description   varchar(500),
    category      varchar(50)  NOT NULL
                      CHECK (category IN ('signalement', 'collecte', 'streak', 'zone', 'defi', 'special')),
    icon          varchar(100),
    points_value  integer      NOT NULL DEFAULT 0,
    condition_sql text,
    CONSTRAINT badges_pkey        PRIMARY KEY (key_badge),
    CONSTRAINT badges_name_unique UNIQUE (name)
);

ALTER TABLE IF EXISTS public.badges OWNER TO postgres;
COMMENT ON COLUMN public.badges.condition_sql IS 'Optional SQL expression evaluated by the badge-award batch to auto-assign';

INSERT INTO public.badges (name, description, category, points_value) VALUES
    -- Signalement
    ('Premier Signalement',        'Effectuer son premier signalement',                                      'signalement', 10),
    ('Sentinelle',                 '10 signalements effectués',                                              'signalement', 50),
    ('Gardien de la Ville',        '50 signalements effectués',                                              'signalement', 150),
    ('Vigie Urbaine',              '100 signalements effectués',                                             'signalement', 300),
    ('Champion des Signalements',  '500 signalements effectués',                                             'signalement', 1000),
    ('Sauveur de Conteneur',       'Signaler un conteneur débordant avant une collecte planifiée',           'signalement', 60),
    ('Alerte Rapide',              'Signaler un débordement avant qu''une alerte système soit levée',        'signalement', 75),
    -- Collecte
    ('Éco-Citoyen',                'Première collecte enregistrée',                                          'collecte', 10),
    ('Collecteur Actif',           '10 collectes enregistrées',                                              'collecte', 50),
    ('Maître du Tri',              '50 collectes enregistrées',                                              'collecte', 150),
    ('Héros du Recyclage',         '200 collectes enregistrées',                                             'collecte', 400),
    -- Streak
    ('Semaine Verte',              '7 jours consécutifs d''activité',                                        'streak', 30),
    ('Mois Vert',                  '30 jours consécutifs d''activité',                                       'streak', 100),
    ('Trimestre Durable',          '90 jours consécutifs d''activité',                                       'streak', 300),
    -- Zone
    ('Ambassadeur de Zone',        'Signalement dans 5 zones différentes',                                   'zone', 50),
    ('Explorateur Urbain',         'Signalement dans 10 zones différentes',                                  'zone', 100),
    ('Couverture Totale',          'Signalement dans toutes les zones de la ville',                          'zone', 500),
    -- Défi
    ('Défi Relevé',                'Compléter son premier défi',                                             'defi', 50),
    ('Champion des Défis',         'Compléter 10 défis',                                                     'defi', 200),
    ('Invincible',                 'Compléter 5 défis consécutifs sans en abandonner un',                    'defi', 250),
    ('Fondateur de Défi',          'Créer un défi auquel participent 50+ personnes',                         'defi', 300),
    -- Spécial
    ('Pionnier',                   'Membre depuis le premier mois du lancement de la plateforme',            'special', 200),
    ('Influenceur Vert',           'Parrainer 5 amis inscrits sur la plateforme',                           'special', 100),
    ('Top 10 Mensuel',             'Figurer dans le top 10 du leaderboard mensuel',                          'special', 150),
    ('Top 3 Mensuel',              'Figurer dans le top 3 du leaderboard mensuel',                           'special', 300),
    ('Champion Mensuel',           'Atteindre la première place du leaderboard mensuel',                     'special', 500),
    ('Grand Maître',               'Dépasser 10 000 points cumulés',                                         'special', 500),
    ('Zéro Déchet',                '100 % de taux de tri correct sur un mois complet',                       'special', 400),
    ('Nuit Blanche',               'Effectuer une action entre 0 h et 5 h',                                  'special', 25),
    ('Week-end Engagé',            'Signalement un samedi ET un dimanche dans la même semaine',              'special', 20)
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------
-- 7.3  user_badges  (depends on: users, badges)  [GAM6]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_badges
(
    key_user_badge integer   NOT NULL DEFAULT nextval('user_badges_key_seq'::regclass),
    user_id        integer   NOT NULL,
    badge_id       integer   NOT NULL,
    earned_at      timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_badges_pkey     PRIMARY KEY (key_user_badge),
    CONSTRAINT user_badges_unique   UNIQUE (user_id, badge_id),
    CONSTRAINT user_badges_user_fk  FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT user_badges_badge_fk FOREIGN KEY (badge_id)
        REFERENCES public.badges (key_badge) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.user_badges OWNER TO postgres;

-- ------------------------------------------------------------
-- 7.4  defis  (challenges — no dependencies)  [GAM8]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.defis
(
    key_defi        integer      NOT NULL DEFAULT nextval('defis_key_seq'::regclass),
    title           varchar(200) NOT NULL,
    description     text,
    type            varchar(50)  NOT NULL
                        CHECK (type IN ('collecte', 'signalement', 'zone', 'collaboratif')),
    target_value    integer      NOT NULL DEFAULT 1,
    reward_points   integer      NOT NULL DEFAULT 0,
    reward_badge_id integer,
    starts_at       timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ends_at         timestamp,
    is_active       boolean      NOT NULL DEFAULT true,
    CONSTRAINT defis_pkey     PRIMARY KEY (key_defi),
    CONSTRAINT defis_badge_fk FOREIGN KEY (reward_badge_id)
        REFERENCES public.badges (key_badge) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE SET NULL
);

ALTER TABLE IF EXISTS public.defis OWNER TO postgres;

-- ------------------------------------------------------------
-- 7.5  defi_participations  (depends on: defis, users)  [GAM8]
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.defi_participations
(
    key_participation integer   NOT NULL DEFAULT nextval('defi_participations_key_seq'::regclass),
    defi_id           integer   NOT NULL,
    user_id           integer   NOT NULL,
    registered_at     timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    progress          integer   NOT NULL DEFAULT 0,
    completed         boolean   NOT NULL DEFAULT false,
    completed_at      timestamp,
    CONSTRAINT defi_participations_pkey    PRIMARY KEY (key_participation),
    CONSTRAINT defi_participations_unique  UNIQUE (defi_id, user_id),
    CONSTRAINT defi_participations_defi_fk FOREIGN KEY (defi_id)
        REFERENCES public.defis (key_defi) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE,
    CONSTRAINT defi_participations_user_fk FOREIGN KEY (user_id)
        REFERENCES public.users (key_user) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.defi_participations OWNER TO postgres;


-- ============================================================
-- 8. SEQUENCE OWNERSHIP  (requires all tables to exist)
-- ============================================================

ALTER SEQUENCE public.role_key_seq                OWNED BY public.role.key_role;
ALTER SEQUENCE public.zones_key_seq               OWNED BY public.zones.key_zone;
ALTER SEQUENCE public.users_key_seq               OWNED BY public.users.key_user;
ALTER SEQUENCE public.container_type_key_seq      OWNED BY public.container_type.key_type;
ALTER SEQUENCE public.containers_key_seq          OWNED BY public.containers.key_container;
ALTER SEQUENCE public.device_key_seq              OWNED BY public.device.key_device;
ALTER SEQUENCE public.teams_key_seq               OWNED BY public.teams.key_teams;
ALTER SEQUENCE public.user_role_key_seq           OWNED BY public.user_role.key_user_role;
ALTER SEQUENCE public.user_team_key_seq           OWNED BY public.user_team.key_user_team;
ALTER SEQUENCE public.signalements_key_seq        OWNED BY public.signalements.key_signalement;
ALTER SEQUENCE public.routes_key_seq              OWNED BY public.routes.key_route;
ALTER SEQUENCE public.route_steps_key_seq         OWNED BY public.route_steps.key_step;
ALTER SEQUENCE public.collections_key_seq         OWNED BY public.collections.key_collection;
ALTER SEQUENCE public.notifications_key_seq       OWNED BY public.notifications.key_notification;
ALTER SEQUENCE public.users_history_key_seq       OWNED BY public.users_history.key_history;
ALTER SEQUENCE public.dashboard_config_key_seq    OWNED BY public.dashboard_config.key_config;
ALTER SEQUENCE public.reports_key_seq             OWNED BY public.reports.key_report;
ALTER SEQUENCE public.fill_history_key_seq        OWNED BY public.fill_history.key_history;
ALTER SEQUENCE public.agg_hourly_key_seq          OWNED BY public.aggregated_hourly_stats.key_stat;
ALTER SEQUENCE public.agg_daily_key_seq           OWNED BY public.aggregated_daily_stats.key_stat;
ALTER SEQUENCE public.ml_predictions_key_seq      OWNED BY public.ml_predictions.key_prediction;
ALTER SEQUENCE public.user_points_key_seq         OWNED BY public.user_points.key_points;
ALTER SEQUENCE public.badges_key_seq              OWNED BY public.badges.key_badge;
ALTER SEQUENCE public.user_badges_key_seq         OWNED BY public.user_badges.key_user_badge;
ALTER SEQUENCE public.defis_key_seq               OWNED BY public.defis.key_defi;
ALTER SEQUENCE public.defi_participations_key_seq OWNED BY public.defi_participations.key_participation;


-- ============================================================
-- 9. INDEXES  [BDD6]
-- ============================================================

-- Spatial GIST indexes — all GEOMETRY columns  (G4)
CREATE INDEX IF NOT EXISTS containers_location_gist_idx
    ON public.containers USING gist (location);

CREATE INDEX IF NOT EXISTS zones_polygon_gist_idx
    ON public.zones USING gist (polygon);

CREATE INDEX IF NOT EXISTS routes_path_gist_idx
    ON public.routes USING gist (path);

-- B-tree on temporal columns  (BDD6, H1)
CREATE INDEX IF NOT EXISTS fill_history_measured_at_idx
    ON public.fill_history (measured_at DESC);

CREATE INDEX IF NOT EXISTS fill_history_container_time_idx
    ON public.fill_history (container_id, measured_at DESC);

CREATE INDEX IF NOT EXISTS collections_collected_at_idx
    ON public.collections (collected_at DESC);

CREATE INDEX IF NOT EXISTS signalements_created_at_idx
    ON public.signalements (created_at DESC);

CREATE INDEX IF NOT EXISTS user_points_earned_at_idx
    ON public.user_points (user_id, earned_at DESC);

CREATE INDEX IF NOT EXISTS agg_hourly_bucket_idx
    ON public.aggregated_hourly_stats (hour_bucket DESC);

CREATE INDEX IF NOT EXISTS agg_daily_bucket_idx
    ON public.aggregated_daily_stats (day_bucket DESC);

CREATE INDEX IF NOT EXISTS ml_pred_container_time_idx
    ON public.ml_predictions (container_id, predicted_at DESC);

-- B-tree on FK columns used in frequent JOINs
CREATE INDEX IF NOT EXISTS fill_history_container_idx
    ON public.fill_history (container_id);

CREATE INDEX IF NOT EXISTS containers_zone_idx
    ON public.containers (zone_id);

CREATE INDEX IF NOT EXISTS containers_type_idx
    ON public.containers (type_id);

CREATE INDEX IF NOT EXISTS containers_status_active_idx
    ON public.containers (status) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS notifications_user_unread_idx
    ON public.notifications (user_id, created_at DESC) WHERE is_read = false;

CREATE INDEX IF NOT EXISTS route_steps_route_order_idx
    ON public.route_steps (route_id, step_order);

CREATE INDEX IF NOT EXISTS signalements_container_idx
    ON public.signalements (container_id);

-- GIN trigram on users_history for fuzzy-search  (pg_trgm)
CREATE INDEX IF NOT EXISTS users_history_gin_idx
    ON public.users_history USING gin
    (
        email       gin_trgm_ops,
        name        gin_trgm_ops,
        first_name  gin_trgm_ops
    )
    WITH (fastupdate = true, gin_pending_list_limit = 4194304);

-- GIN on dashboard JSONB config
CREATE INDEX IF NOT EXISTS dashboard_config_layout_gin_idx
    ON public.dashboard_config USING gin (layout_config);


-- ============================================================
-- 10. FUNCTIONS
-- ============================================================

-- ------------------------------------------------------------
-- 10.1  RBAC helpers
-- ------------------------------------------------------------

-- Returns the minimum (lowest-privilege) role key of the current user.
CREATE OR REPLACE FUNCTION public.get_user_role()
    RETURNS integer
    LANGUAGE sql
    STABLE PARALLEL UNSAFE
AS $$
    SELECT MIN(role_key)
    FROM public.user_role
    WHERE user_key = current_setting('app.user_id', true)::int
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

-- ------------------------------------------------------------
-- 10.2  users_history helpers
-- ------------------------------------------------------------

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
    INSERT INTO public.users_history (user_key, email, name, first_name, password)
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
    PERFORM public.insert_history(NEW.key_user, NEW.email, NEW.name, NEW.first_name, NEW.password);
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.update_history_function() OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.3  Spatial helpers  (G5–G8)
-- ------------------------------------------------------------

-- Containers within a zone polygon — ST_Within  (G6, Z2).
CREATE OR REPLACE FUNCTION public.get_containers_in_zone(p_zone_id integer)
    RETURNS SETOF public.containers
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT c.*
    FROM public.containers c
    JOIN public.zones z ON z.key_zone = p_zone_id
    WHERE z.polygon IS NOT NULL
      AND ST_Within(c.location, z.polygon)
      AND c.is_active = true;
$$;

ALTER FUNCTION public.get_containers_in_zone(integer) OWNER TO postgres;

-- Containers within p_radius_m metres of a lat/lng point — ST_DWithin  (G7).
CREATE OR REPLACE FUNCTION public.get_containers_near(
    p_lat      double precision,
    p_lng      double precision,
    p_radius_m double precision DEFAULT 1000.0
)
    RETURNS SETOF public.containers
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT c.*
    FROM public.containers c
    WHERE ST_DWithin(
              c.location::geography,
              ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
              p_radius_m
          )
      AND c.is_active = true;
$$;

ALTER FUNCTION public.get_containers_near(double precision, double precision, double precision) OWNER TO postgres;

-- Density of active containers per km² for a zone — ST_Area  (Z5, C19).
CREATE OR REPLACE FUNCTION public.get_zone_density(p_zone_id integer)
    RETURNS numeric
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT ROUND(
        COUNT(c.key_container)::numeric /
        NULLIF(ST_Area(z.polygon::geography)::numeric / 1e6, 0),
        4
    )
    FROM public.zones z
    LEFT JOIN public.containers c
           ON ST_Within(c.location, z.polygon) AND c.is_active = true
    WHERE z.key_zone = p_zone_id
      AND z.polygon IS NOT NULL
    GROUP BY z.polygon;
$$;

ALTER FUNCTION public.get_zone_density(integer) OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.4  Container status computation  (C16)
-- ------------------------------------------------------------

-- Pure function: fill_rate → status label.
CREATE OR REPLACE FUNCTION public.compute_container_status(p_fill_rate numeric)
    RETURNS varchar
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE
AS $$
    SELECT CASE
        WHEN p_fill_rate >= 90 THEN 'critical'
        WHEN p_fill_rate >= 70 THEN 'full'
        WHEN p_fill_rate >= 25 THEN 'normal'
        ELSE 'empty'
    END;
$$;

ALTER FUNCTION public.compute_container_status(numeric) OWNER TO postgres;

-- Trigger function: keep containers.fill_rate and status in sync after an IoT insert.
CREATE OR REPLACE FUNCTION public.update_container_fill_status()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
BEGIN
    UPDATE public.containers
    SET fill_rate    = NEW.fill_rate,
        status       = public.compute_container_status(NEW.fill_rate),
        last_updated = NOW()
    WHERE key_container = NEW.container_id;
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.update_container_fill_status() OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.5  Alert generation  (C17)
-- ------------------------------------------------------------

-- Trigger function: inserts a notification when fill_rate exceeds the threshold.
CREATE OR REPLACE FUNCTION public.generate_fill_alert()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
DECLARE
    v_threshold numeric(5,2);
BEGIN
    SELECT fill_threshold_pct INTO v_threshold
    FROM public.containers
    WHERE key_container = NEW.container_id;

    IF NEW.fill_rate > v_threshold THEN
        INSERT INTO public.notifications (container_id, type, title, content)
        VALUES (
            NEW.container_id,
            'threshold_breach',
            'Conteneur — seuil dépassé',
            format(
                'Conteneur %s : taux de remplissage %s %% (seuil configuré : %s %%)',
                NEW.container_id, NEW.fill_rate, v_threshold
            )
        );
    END IF;
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.generate_fill_alert() OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.6  Auto zone assignment  (Z4, C3)
-- ------------------------------------------------------------

-- Trigger function: resolves zone_id from GPS location via ST_Within on INSERT/UPDATE.
CREATE OR REPLACE FUNCTION public.assign_zone_to_container()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
DECLARE
    v_zone_id integer;
BEGIN
    SELECT key_zone INTO v_zone_id
    FROM public.zones
    WHERE polygon IS NOT NULL
      AND ST_Within(NEW.location, polygon)
    ORDER BY ST_Area(polygon)   -- smallest enclosing zone wins
    LIMIT 1;

    NEW.zone_id := v_zone_id;
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.assign_zone_to_container() OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.7  IoT deduplication check  (C14)
-- ------------------------------------------------------------

-- Returns true when a measurement for the same container already exists
-- within the same clock-minute (same-minute duplicate detection).
CREATE OR REPLACE FUNCTION public.is_duplicate_measurement(
    p_container_id integer,
    p_measured_at  timestamp
)
    RETURNS boolean
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.fill_history
        WHERE container_id = p_container_id
          AND date_trunc('minute', measured_at) = date_trunc('minute', p_measured_at)
    );
$$;

ALTER FUNCTION public.is_duplicate_measurement(integer, timestamp) OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.8  Gamification — point attribution  (GAM2)
-- ------------------------------------------------------------

-- Appends a point-ledger entry for a user.
CREATE OR REPLACE FUNCTION public.award_points(
    p_user_id integer,
    p_action  varchar,
    p_points  integer,
    p_ref_id  integer DEFAULT NULL
)
    RETURNS void
    LANGUAGE sql
    VOLATILE PARALLEL UNSAFE
AS $$
    INSERT INTO public.user_points (user_id, action_type, points, reference_id)
    VALUES (p_user_id, p_action, p_points, p_ref_id);
$$;

ALTER FUNCTION public.award_points(integer, varchar, integer, integer) OWNER TO postgres;

-- Trigger function: awards +10 pts when a signalement is created.
CREATE OR REPLACE FUNCTION public.award_points_on_signalement()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
BEGIN
    IF NEW.user_id IS NOT NULL THEN
        PERFORM public.award_points(NEW.user_id, 'signalement', 10, NEW.key_signalement);
    END IF;
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.award_points_on_signalement() OWNER TO postgres;

-- Trigger function: awards badge points + pushes a notification when a badge is granted.
CREATE OR REPLACE FUNCTION public.award_points_on_badge()
    RETURNS trigger
    LANGUAGE plpgsql
    VOLATILE NOT LEAKPROOF
AS $$
DECLARE
    v_pts integer;
BEGIN
    SELECT points_value INTO v_pts FROM public.badges WHERE key_badge = NEW.badge_id;
    IF v_pts > 0 THEN
        PERFORM public.award_points(NEW.user_id, 'badge_earned', v_pts, NEW.badge_id);
    END IF;
    INSERT INTO public.notifications (user_id, type, title, content)
    SELECT NEW.user_id, 'badge_earned',
           'Nouveau badge débloqué !',
           format('Vous avez obtenu le badge « %s »', b.name)
    FROM public.badges b WHERE b.key_badge = NEW.badge_id;
    RETURN NEW;
END;
$$;

ALTER FUNCTION public.award_points_on_badge() OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.9  Leaderboard helper  (GAM3, GAM4)
-- ------------------------------------------------------------

-- Top-N users by total points, optionally filtered to a time window.
CREATE OR REPLACE FUNCTION public.get_leaderboard(
    p_limit integer   DEFAULT 100,
    p_from  timestamp DEFAULT NULL,
    p_to    timestamp DEFAULT NULL
)
    RETURNS TABLE (
        rank         bigint,
        user_id      integer,
        name         varchar,
        first_name   varchar,
        total_points bigint
    )
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT
        ROW_NUMBER() OVER (ORDER BY SUM(up.points) DESC) AS rank,
        u.key_user,
        u.name,
        u.first_name,
        SUM(up.points) AS total_points
    FROM public.users u
    JOIN public.user_points up ON up.user_id = u.key_user
    WHERE (p_from IS NULL OR up.earned_at >= p_from)
      AND (p_to   IS NULL OR up.earned_at <= p_to)
    GROUP BY u.key_user, u.name, u.first_name
    ORDER BY total_points DESC
    LIMIT p_limit;
$$;

ALTER FUNCTION public.get_leaderboard(integer, timestamp, timestamp) OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.10  ETL aggregation procedures  (H3, H4)
-- ------------------------------------------------------------

-- Upserts aggregated_hourly_stats for one hour bucket.
CREATE OR REPLACE PROCEDURE public.aggregate_hourly(p_hour timestamp)
LANGUAGE sql
AS $$
    INSERT INTO public.aggregated_hourly_stats
        (container_id, zone_id, hour_bucket,
         avg_fill_rate, min_fill_rate, max_fill_rate, measurement_count)
    SELECT
        fh.container_id,
        c.zone_id,
        date_trunc('hour', fh.measured_at)          AS hour_bucket,
        ROUND(AVG(fh.fill_rate)::numeric, 2),
        MIN(fh.fill_rate),
        MAX(fh.fill_rate),
        COUNT(*)
    FROM public.fill_history fh
    JOIN public.containers c ON c.key_container = fh.container_id
    WHERE date_trunc('hour', fh.measured_at) = date_trunc('hour', p_hour)
      AND fh.is_outlier = false
    GROUP BY fh.container_id, c.zone_id, date_trunc('hour', fh.measured_at)
    ON CONFLICT (container_id, hour_bucket) DO UPDATE SET
        avg_fill_rate     = EXCLUDED.avg_fill_rate,
        min_fill_rate     = EXCLUDED.min_fill_rate,
        max_fill_rate     = EXCLUDED.max_fill_rate,
        measurement_count = EXCLUDED.measurement_count;
$$;

ALTER PROCEDURE public.aggregate_hourly(timestamp) OWNER TO postgres;

-- Upserts aggregated_daily_stats for one calendar day.
CREATE OR REPLACE PROCEDURE public.aggregate_daily(p_day date)
LANGUAGE sql
AS $$
    INSERT INTO public.aggregated_daily_stats
        (container_id, zone_id, day_bucket,
         avg_fill_rate, min_fill_rate, max_fill_rate,
         overflow_count, collection_count, measurement_count)
    SELECT
        fh.container_id,
        c.zone_id,
        fh.measured_at::date                                    AS day_bucket,
        ROUND(AVG(fh.fill_rate)::numeric, 2),
        MIN(fh.fill_rate),
        MAX(fh.fill_rate),
        COUNT(*) FILTER (WHERE fh.fill_rate > c.fill_threshold_pct),
        COALESCE(coll.coll_count, 0),
        COUNT(*)
    FROM public.fill_history fh
    JOIN public.containers c ON c.key_container = fh.container_id
    LEFT JOIN (
        SELECT container_id, COUNT(*) AS coll_count
        FROM public.collections
        WHERE collected_at::date = p_day
        GROUP BY container_id
    ) coll ON coll.container_id = fh.container_id
    WHERE fh.measured_at::date = p_day
      AND fh.is_outlier = false
    GROUP BY fh.container_id, c.zone_id, fh.measured_at::date, coll.coll_count
    ON CONFLICT (container_id, day_bucket) DO UPDATE SET
        avg_fill_rate     = EXCLUDED.avg_fill_rate,
        min_fill_rate     = EXCLUDED.min_fill_rate,
        max_fill_rate     = EXCLUDED.max_fill_rate,
        overflow_count    = EXCLUDED.overflow_count,
        collection_count  = EXCLUDED.collection_count,
        measurement_count = EXCLUDED.measurement_count;
$$;

ALTER PROCEDURE public.aggregate_daily(date) OWNER TO postgres;

-- ------------------------------------------------------------
-- 10.11  Analytics helpers  (A8, A9, H7)
-- ------------------------------------------------------------

-- Heatmap data: count of measurements grouped by (day_of_week × hour).
CREATE OR REPLACE FUNCTION public.get_heatmap_data(
    p_from timestamp DEFAULT NOW() - INTERVAL '90 days',
    p_to   timestamp DEFAULT NOW()
)
    RETURNS TABLE (
        day_of_week integer,
        hour_of_day integer,
        cnt         bigint
    )
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT
        EXTRACT(isodow FROM measured_at)::integer  AS day_of_week,
        EXTRACT(hour   FROM measured_at)::integer  AS hour_of_day,
        COUNT(*)                                   AS cnt
    FROM public.fill_history
    WHERE measured_at BETWEEN p_from AND p_to
      AND is_outlier = false
    GROUP BY 1, 2
    ORDER BY 1, 2;
$$;

ALTER FUNCTION public.get_heatmap_data(timestamp, timestamp) OWNER TO postgres;

-- Choropleth data: per-zone density + average fill rate  (A9, Z5).
CREATE OR REPLACE FUNCTION public.get_choropleth_data()
    RETURNS TABLE (
        zone_id       integer,
        zone_name     varchar,
        polygon       geometry,
        density_km2   numeric,
        avg_fill_rate numeric
    )
    LANGUAGE sql
    STABLE PARALLEL SAFE
AS $$
    SELECT
        z.key_zone,
        z.name,
        z.polygon,
        ROUND(COUNT(c.key_container)::numeric /
              NULLIF(ST_Area(z.polygon::geography)::numeric / 1e6, 0), 4) AS density_km2,
        ROUND(AVG(c.fill_rate)::numeric, 2)                       AS avg_fill_rate
    FROM public.zones z
    LEFT JOIN public.containers c
           ON ST_Within(c.location, z.polygon) AND c.is_active = true
    WHERE z.polygon IS NOT NULL
    GROUP BY z.key_zone, z.name, z.polygon;
$$;

ALTER FUNCTION public.get_choropleth_data() OWNER TO postgres;


-- ============================================================
-- 11. TRIGGERS
-- ============================================================

-- users_history: stamp valid_from on every new history row.
CREATE OR REPLACE TRIGGER history_set_valid
    BEFORE INSERT
    ON public.users_history
    FOR EACH ROW
    EXECUTE FUNCTION public.update_validity();

-- users: archive snapshot after insert or update.
CREATE OR REPLACE TRIGGER users_archive_trigger
    AFTER INSERT OR UPDATE
    ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.update_history_function();

-- containers: auto-assign zone from GPS position on insert or location update  (Z4).
CREATE OR REPLACE TRIGGER containers_assign_zone
    BEFORE INSERT OR UPDATE OF location
    ON public.containers
    FOR EACH ROW
    EXECUTE FUNCTION public.assign_zone_to_container();

-- fill_history: sync container fill_rate + status after each IoT measurement  (C16).
CREATE OR REPLACE TRIGGER fill_history_update_container
    AFTER INSERT
    ON public.fill_history
    FOR EACH ROW
    EXECUTE FUNCTION public.update_container_fill_status();

-- fill_history: generate a threshold-breach notification when needed  (C17).
CREATE OR REPLACE TRIGGER fill_history_alert
    AFTER INSERT
    ON public.fill_history
    FOR EACH ROW
    EXECUTE FUNCTION public.generate_fill_alert();

-- signalements: award +10 pts to the reporting user  (GAM2).
CREATE OR REPLACE TRIGGER signalement_award_points
    AFTER INSERT
    ON public.signalements
    FOR EACH ROW
    EXECUTE FUNCTION public.award_points_on_signalement();

-- user_badges: award badge points + push notification when a badge is granted  (GAM6).
CREATE OR REPLACE TRIGGER user_badges_award_points
    AFTER INSERT
    ON public.user_badges
    FOR EACH ROW
    EXECUTE FUNCTION public.award_points_on_badge();


-- ============================================================
-- 12. POLICIES  (Row Level Security)
-- ============================================================

-- user_role: users can SELECT only their own role mappings.
CREATE POLICY user_role_select_policy
    ON public.user_role
    AS PERMISSIVE FOR SELECT TO public
    USING (user_key = current_setting('app.user_id', true)::int);

-- users: role-based access.
CREATE POLICY admin_full_access
    ON public.users AS PERMISSIVE FOR ALL TO public
    USING      (get_user_role() = 4)
    WITH CHECK (get_user_role() = 4);

CREATE POLICY users_select_policy
    ON public.users AS PERMISSIVE FOR SELECT TO public
    USING (
        has_role(4)
        OR has_role(3)
        OR (key_user = current_setting('app.user_id', true)::int
            AND (has_role(1) OR has_role(2)))
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

-- signalements: citizen sees own; worker/manager/admin see all in scope.
CREATE POLICY signalements_select_policy
    ON public.signalements AS PERMISSIVE FOR SELECT TO public
    USING (
        has_role(4) OR has_role(3) OR has_role(2)
        OR user_id = current_setting('app.user_id', true)::int
    );

CREATE POLICY signalements_insert_policy
    ON public.signalements AS PERMISSIVE FOR INSERT TO public
    WITH CHECK (
        user_id = current_setting('app.user_id', true)::int
        OR has_role(4)
    );

CREATE POLICY signalements_update_policy
    ON public.signalements AS PERMISSIVE FOR UPDATE TO public
    USING (has_role(4) OR has_role(3) OR has_role(2));

-- notifications: each user sees only their own (or broadcast notifications).
CREATE POLICY notifications_user_policy
    ON public.notifications AS PERMISSIVE FOR SELECT TO public
    USING (
        user_id IS NULL
        OR user_id = current_setting('app.user_id', true)::int
        OR has_role(4)
    );


-- ============================================================
-- 13. GRANTS
-- ============================================================

-- Core OLTP
REVOKE ALL ON TABLE public.user_role FROM app_user;
GRANT  SELECT                         ON TABLE public.user_role TO app_user;
GRANT  ALL                            ON TABLE public.user_role TO postgres;

REVOKE ALL ON TABLE public.users FROM app_user;
GRANT  INSERT, DELETE, SELECT, UPDATE ON TABLE public.users     TO app_user;
GRANT  ALL                            ON TABLE public.users     TO postgres;

GRANT  SELECT, INSERT, UPDATE         ON TABLE public.containers              TO app_user;
GRANT  SELECT                         ON TABLE public.container_type          TO app_user;
GRANT  SELECT                         ON TABLE public.zones                   TO app_user;
GRANT  SELECT, INSERT                 ON TABLE public.signalements            TO app_user;
GRANT  SELECT                         ON TABLE public.routes                  TO app_user;
GRANT  SELECT                         ON TABLE public.route_steps             TO app_user;
GRANT  SELECT, INSERT                 ON TABLE public.collections             TO app_user;
GRANT  SELECT, UPDATE                 ON TABLE public.notifications           TO app_user;
GRANT  SELECT, INSERT, UPDATE         ON TABLE public.dashboard_config        TO app_user;
GRANT  SELECT, INSERT                 ON TABLE public.reports                 TO app_user;

-- OLAP
GRANT  SELECT, INSERT                 ON TABLE public.fill_history            TO app_user;
GRANT  SELECT                         ON TABLE public.aggregated_hourly_stats TO app_user;
GRANT  SELECT                         ON TABLE public.aggregated_daily_stats  TO app_user;
GRANT  SELECT                         ON TABLE public.ml_predictions          TO app_user;

-- Gamification
GRANT  SELECT, INSERT                 ON TABLE public.user_points             TO app_user;
GRANT  SELECT                         ON TABLE public.badges                  TO app_user;
GRANT  SELECT, INSERT                 ON TABLE public.user_badges             TO app_user;
GRANT  SELECT                         ON TABLE public.defis                   TO app_user;
GRANT  SELECT, INSERT, UPDATE         ON TABLE public.defi_participations     TO app_user;

-- Superuser retains full access to everything
GRANT  ALL ON ALL TABLES    IN SCHEMA public TO postgres;
GRANT  ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT  ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres;
