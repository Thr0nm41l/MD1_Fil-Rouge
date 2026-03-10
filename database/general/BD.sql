-- Database: Ecotrack

-- DROP DATABASE IF EXISTS "Ecotrack";

CREATE DATABASE "Ecotrack"
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

COMMENT ON DATABASE "Ecotrack"
    IS 'Database for ecotrack sql/Merise TP';