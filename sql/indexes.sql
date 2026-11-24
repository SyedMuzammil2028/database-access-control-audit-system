-- Canonical indexes are created by Alembic. These idempotent examples match them.
CREATE INDEX IF NOT EXISTS ix_audit_occurred ON audit_event(occurred_at);
CREATE INDEX IF NOT EXISTS ix_audit_actor_time ON audit_event(actor_user_id,occurred_at);
CREATE INDEX IF NOT EXISTS ix_audit_decision_time ON audit_event(decision,occurred_at);
CREATE INDEX IF NOT EXISTS ix_audit_resource_time ON audit_event(resource_id,occurred_at);
CREATE INDEX IF NOT EXISTS ix_policy_time ON policy_change(occurred_at);
CREATE INDEX IF NOT EXISTS ix_policy_actor_time ON policy_change(actor_user_id,occurred_at);
-- PostgreSQL automatically indexes primary keys and UNIQUE constraints.
