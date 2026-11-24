-- Read-only derived views. Execute as the migration owner.
CREATE OR REPLACE VIEW effective_user_permission AS
SELECT DISTINCT u.id AS user_id, u.email, p.action, p.resource_type
FROM app_user u
JOIN user_role ur ON ur.user_id = u.id AND ur.active
JOIN role r ON r.id = ur.role_id AND r.active
JOIN role_permission rp ON rp.role_id = r.id
JOIN permission p ON p.id = rp.permission_id
WHERE u.active;

CREATE OR REPLACE VIEW daily_access_summary AS
SELECT (occurred_at AT TIME ZONE 'UTC')::date AS access_date,
       resource_type, decision, count(*) AS request_count
FROM audit_event
GROUP BY (occurred_at AT TIME ZONE 'UTC')::date, resource_type, decision;
