

REVOKE ALL ON TABLE public.user_role FROM app_user;

GRANT SELECT ON TABLE public.user_role TO app_user;

GRANT ALL ON TABLE public.user_role TO postgres;


REVOKE ALL ON TABLE public.users FROM app_user;

GRANT INSERT, DELETE, SELECT, UPDATE ON TABLE public.users TO app_user;

GRANT ALL ON TABLE public.users TO postgres;
-- POLICY: admin_full_access

-- DROP POLICY IF EXISTS admin_full_access ON public.users;

CREATE POLICY admin_full_access
    ON public.users
    AS PERMISSIVE
    FOR ALL
    TO public
    USING ((get_user_role() = 4))
    WITH CHECK ((get_user_role() = 4));
-- POLICY: users_delete_policy

-- DROP POLICY IF EXISTS users_delete_policy ON public.users;

CREATE POLICY users_delete_policy
    ON public.users
    AS PERMISSIVE
    FOR DELETE
    TO public
    USING (has_role(4));
-- POLICY: users_insert_policy

-- DROP POLICY IF EXISTS users_insert_policy ON public.users;

CREATE POLICY users_insert_policy
    ON public.users
    AS PERMISSIVE
    FOR INSERT
    TO public
    WITH CHECK ((has_role(4) OR has_role(3)));
-- POLICY: users_select_policy

-- DROP POLICY IF EXISTS users_select_policy ON public.users;

CREATE POLICY users_select_policy
    ON public.users
    AS PERMISSIVE
    FOR SELECT
    TO public
    USING ((has_role(4) OR has_role(3) OR ((key_user = (current_setting('app.user_id'::text, true))::integer) AND (has_role(1) OR has_role(2)))));
-- POLICY: users_update_policy

-- DROP POLICY IF EXISTS users_update_policy ON public.users;

CREATE POLICY users_update_policy
    ON public.users
    AS PERMISSIVE
    FOR UPDATE
    TO public
    USING ((has_role(4) OR (key_user = (current_setting('app.user_id'::text, true))::integer)))
    WITH CHECK ((has_role(4) OR (key_user = (current_setting('app.user_id'::text, true))::integer)));