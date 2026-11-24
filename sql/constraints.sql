-- Successful constraint checks catch expected exceptions in subtransactions.
-- No intentional error is left uncaught; ON_ERROR_STOP remains usable.
DO $$
BEGIN
  BEGIN
    INSERT INTO user_role(user_id,role_id,assigned_by)
      SELECT user_id,role_id,assigned_by FROM user_role LIMIT 1;
    RAISE EXCEPTION 'Duplicate assignment unexpectedly accepted';
  EXCEPTION WHEN unique_violation THEN RAISE NOTICE 'PASS: duplicate assignment rejected';
  END;
  BEGIN
    INSERT INTO user_role(user_id,role_id,assigned_by) VALUES(2147483647,1,1);
    RAISE EXCEPTION 'Orphan assignment unexpectedly accepted';
  EXCEPTION WHEN foreign_key_violation THEN RAISE NOTICE 'PASS: orphan foreign key rejected';
  END;
  BEGIN
    INSERT INTO permission(action,resource_type) VALUES('EXEC','report');
    RAISE EXCEPTION 'Unsupported action unexpectedly accepted';
  EXCEPTION WHEN check_violation THEN RAISE NOTICE 'PASS: action constraint enforced';
  END;
END $$;
