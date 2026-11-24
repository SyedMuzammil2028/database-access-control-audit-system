-- Run as migration owner AFTER migrations and views. dac_app is provisioned by
-- scripts/init-db.sh with a password passed through a psql variable (not tracked).
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO dac_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM dac_app;
GRANT SELECT, INSERT, UPDATE ON app_user, role, permission, resource, user_role TO dac_app;
GRANT SELECT, INSERT, DELETE ON role_permission, login_session TO dac_app;
GRANT SELECT, INSERT ON audit_event, policy_change, security_event TO dac_app;
GRANT SELECT ON effective_user_permission, daily_access_summary TO dac_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dac_app;
-- No audit UPDATE/DELETE, no DDL, no migration table rights; no user/role deletion.
-- Optional dedicated SQL auditor (provision password independently):
-- CREATE ROLE dac_sql_auditor NOLOGIN;
-- GRANT CONNECT ON DATABASE dac TO dac_sql_auditor;
-- GRANT USAGE ON SCHEMA public TO dac_sql_auditor;
-- GRANT SELECT ON audit_event, policy_change, security_event,
--   effective_user_permission, daily_access_summary TO dac_sql_auditor;
