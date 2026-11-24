-- Academic demonstrations. Run as owner on a seeded demonstration database.
-- 1. Basic CRUD on a temporary relation; live security policy is unaffected.
CREATE TEMP TABLE sql_crud_demo (id integer PRIMARY KEY, name text NOT NULL);
INSERT INTO sql_crud_demo VALUES (1, 'Sample registration');
SELECT * FROM sql_crud_demo WHERE id=1;
UPDATE sql_crud_demo SET name='Updated registration' WHERE id=1;
DELETE FROM sql_crud_demo WHERE id=1;
DROP TABLE sql_crud_demo;

-- 2. INNER JOIN: assigned users and role names.
SELECT u.email, r.name, ur.active, ur.assigned_at
FROM app_user u INNER JOIN user_role ur ON ur.user_id=u.id
INNER JOIN role r ON r.id=ur.role_id ORDER BY u.email, r.name;

-- 3. LEFT JOIN: include users with no active assignment.
SELECT u.email, r.name AS active_role
FROM app_user u LEFT JOIN user_role ur ON ur.user_id=u.id AND ur.active
LEFT JOIN role r ON r.id=ur.role_id AND r.active ORDER BY u.email;

-- 4. Effective permissions: multi-table join (inactive accounts excluded).
SELECT DISTINCT u.email, p.action, p.resource_type
FROM app_user u JOIN user_role ur ON ur.user_id=u.id AND ur.active
JOIN role r ON r.id=ur.role_id AND r.active
JOIN role_permission rp ON rp.role_id=r.id
JOIN permission p ON p.id=rp.permission_id
WHERE u.active ORDER BY u.email,p.resource_type,p.action;

-- 5. GROUP BY and aggregate: requests by UTC day, type and decision.
SELECT (occurred_at AT TIME ZONE 'UTC')::date AS day,
 resource_type, decision, count(*) AS requests
FROM audit_event GROUP BY day,resource_type,decision ORDER BY day DESC;

-- 6. HAVING: users with at least three denials in the last 30 days.
SELECT actor_email, count(*) AS denials, min(occurred_at) AS first_denial,
 max(occurred_at) AS last_denial
FROM audit_event WHERE decision='DENIED' AND occurred_at>=now()-interval '30 days'
GROUP BY actor_email HAVING count(*)>=3 ORDER BY denials DESC;

-- 7. Policy changes followed by that subject's access within one day.
SELECT pc.id AS change_id, pc.operation, pc.occurred_at AS changed_at,
 ae.id AS event_id, ae.actor_email, ae.resource_key, ae.decision, ae.occurred_at
FROM policy_change pc JOIN audit_event ae
 ON ae.actor_user_id=(pc.details->>'user_id')::integer
 AND ae.occurred_at>=pc.occurred_at
 AND ae.occurred_at<pc.occurred_at+interval '1 day'
WHERE pc.target_type='user_role' ORDER BY pc.occurred_at;

-- 8. Historical role snapshots compared with current assignments.
SELECT ae.id, ae.actor_email, ae.decision, ae.matching_role_name AS role_at_decision,
 ae.reason_code, ae.occurred_at,
 EXISTS (SELECT 1 FROM user_role ur JOIN role r ON r.id=ur.role_id
         WHERE ur.user_id=ae.actor_user_id AND ur.role_id=ae.matching_role_id
         AND ur.active AND r.active) AS matching_role_still_assigned,
 (SELECT string_agg(r.name, ', ' ORDER BY r.name)
  FROM user_role ur JOIN role r ON r.id=ur.role_id
  WHERE ur.user_id=ae.actor_user_id AND ur.active AND r.active) AS current_roles
FROM audit_event ae ORDER BY ae.occurred_at DESC;

-- 9. Role assignment changes made by a chosen administrator.
SELECT pc.operation, pc.details->>'email' AS subject_email,
 pc.details->>'role_name' AS role, pc.occurred_at
FROM policy_change pc JOIN app_user admin ON admin.id=pc.actor_user_id
WHERE admin.email='admin@example.com' AND pc.target_type='user_role'
ORDER BY pc.occurred_at DESC;

-- 10. Access history of the representative sample report R42.
SELECT actor_email, action, decision, reason_code, matching_role_name,
 request_id, occurred_at FROM audit_event
WHERE resource_type='report' AND resource_key='R42' ORDER BY occurred_at DESC;

-- 11. EXISTS/subquery: resources with a recorded denied request.
SELECT r.resource_type, r.resource_key, r.name FROM resource r
WHERE EXISTS (SELECT 1 FROM audit_event ae WHERE ae.resource_id=r.id AND ae.decision='DENIED');
SELECT email FROM app_user WHERE id IN
 (SELECT user_id FROM user_role WHERE active GROUP BY user_id HAVING count(*)>1);

-- 12. Conditional aggregates and view queries.
SELECT count(*) AS total,
 count(*) FILTER (WHERE decision='ALLOWED') AS allowed,
 count(*) FILTER (WHERE decision='DENIED') AS denied,
 round(100.0*count(*) FILTER (WHERE decision='DENIED')/nullif(count(*),0),2) AS denied_percent
FROM audit_event;
SELECT * FROM effective_user_permission ORDER BY email,resource_type,action;
SELECT * FROM daily_access_summary ORDER BY access_date DESC;

-- 13. Query planning: small fixtures may favor a sequential scan legitimately.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM audit_event
WHERE actor_user_id=7 AND occurred_at>=now()-interval '7 days' ORDER BY occurred_at DESC LIMIT 20;
EXPLAIN SELECT * FROM audit_event
WHERE decision='DENIED' AND occurred_at>=now()-interval '30 days';
