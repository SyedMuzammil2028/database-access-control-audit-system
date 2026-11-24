-- Execute as owner in a development database. Temp-table COMMIT/ROLLBACK demo.
BEGIN;
CREATE TEMP TABLE transaction_demo (id integer PRIMARY KEY, value text);
INSERT INTO transaction_demo VALUES(1,'committed');
COMMIT;
SELECT * FROM transaction_demo; -- committed
BEGIN;
UPDATE transaction_demo SET value='uncommitted' WHERE id=1;
ROLLBACK;
SELECT * FROM transaction_demo; -- still committed
DROP TABLE transaction_demo;

-- Representative atomic policy change. Entire example is rolled back.
BEGIN;
SELECT pg_advisory_xact_lock(73481021);
WITH changed AS (
 UPDATE user_role SET active=false
 WHERE user_id=(SELECT id FROM app_user WHERE email='analyst@example.com')
 AND role_id=(SELECT id FROM role WHERE name='Report Analyst') AND active
 RETURNING user_id,role_id
)
INSERT INTO policy_change(id,actor_user_id,actor_email,target_type,target_id,operation,details,request_id)
SELECT gen_random_uuid(),a.id,a.email,'user_role',c.user_id||':'||c.role_id,'revoke_role',
 jsonb_build_object('user_id',c.user_id,'role_id',c.role_id,'source','rolled-back SQL demonstration'),gen_random_uuid()
FROM changed c CROSS JOIN app_user a WHERE a.email='admin@example.com';
ROLLBACK; -- neither the revocation nor its policy audit persists
