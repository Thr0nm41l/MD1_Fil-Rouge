
-- FUNCTION: public.get_user_role()

-- DROP FUNCTION IF EXISTS public.get_user_role();

CREATE OR REPLACE FUNCTION public.get_user_role(
	)
    RETURNS integer
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
AS $BODY$
SELECT MIN(role_key)
FROM user_role
WHERE user_key = current_setting('app.current_user_id')::int
$BODY$;

ALTER FUNCTION public.get_user_role()
    OWNER TO postgres;

-- FUNCTION: public.has_role(integer)

-- DROP FUNCTION IF EXISTS public.has_role(integer);

CREATE OR REPLACE FUNCTION public.has_role(
	role_id integer)
    RETURNS boolean
    LANGUAGE 'sql'
    COST 100
    STABLE PARALLEL UNSAFE
AS $BODY$
SELECT EXISTS (
    SELECT 1
    FROM public.user_role
    WHERE user_key = current_setting('app.user_id', true)::int
    AND role_key = role_id
)
$BODY$;

ALTER FUNCTION public.has_role(integer)
    OWNER TO postgres;


-- FUNCTION: public.update_history_function()

-- DROP FUNCTION IF EXISTS public.update_history_function();

CREATE OR REPLACE FUNCTION public.update_history_function()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    PERFORM insert_history(NEW.key_user, NEW.email, NEW.nom, NEW.prenom, NEW.password);
    RETURN NEW;
END;
$BODY$;

ALTER FUNCTION public.update_history_function()
    OWNER TO postgres;



-- PROCEDURE: public.insert_history(integer, character varying, character varying, character varying, character varying)

-- DROP PROCEDURE IF EXISTS public.insert_history(integer, character varying, character varying, character varying, character varying);

CREATE OR REPLACE PROCEDURE public.insert_history(
	IN a integer,
	IN b character varying,
	IN c character varying,
	IN d character varying,
	IN e character varying)
LANGUAGE 'sql'
AS $BODY$
	INSERT INTO users_history (user_key, email, nom, prenom, password) VALUES (a, b, c, d, e)
	
$BODY$;
ALTER PROCEDURE public.insert_history(integer, character varying, character varying, character varying, character varying)
    OWNER TO postgres;



