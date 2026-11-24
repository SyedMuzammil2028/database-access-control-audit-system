-- GENERATED from Alembic; do not edit. Empty database only.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE app_user (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    password_hash TEXT NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_user_email_lower CHECK (email = lower(email)), 
    CONSTRAINT ck_user_name CHECK (length(trim(name)) > 0), 
    UNIQUE (email)
);

CREATE TABLE permission (
    id SERIAL NOT NULL, 
    action VARCHAR(6) NOT NULL, 
    resource_type VARCHAR(40) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_permission_action CHECK (action IN ('READ','CREATE','UPDATE','DELETE')), 
    CONSTRAINT ck_permission_type CHECK (resource_type ~ '^[a-z][a-z0-9_]{0,39}$'), 
    CONSTRAINT uq_permission_action_type UNIQUE (action, resource_type)
);

CREATE TABLE role (
    id SERIAL NOT NULL, 
    name VARCHAR(60) NOT NULL, 
    description VARCHAR(300) DEFAULT '' NOT NULL, 
    kind VARCHAR(10) DEFAULT 'user' NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_role_kind CHECK (kind IN ('admin','auditor','user')), 
    CONSTRAINT ck_role_name CHECK (length(trim(name)) > 0), 
    UNIQUE (name)
);

CREATE TABLE login_session (
    token_hash VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    csrf_token VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (token_hash), 
    FOREIGN KEY(user_id) REFERENCES app_user (id)
);

CREATE INDEX ix_login_session_expires_at ON login_session (expires_at);

CREATE INDEX ix_login_session_user_id ON login_session (user_id);

CREATE TABLE policy_change (
    id UUID NOT NULL, 
    actor_user_id INTEGER NOT NULL, 
    actor_email VARCHAR(254) NOT NULL, 
    target_type VARCHAR(30) NOT NULL, 
    target_id VARCHAR(80) NOT NULL, 
    operation VARCHAR(40) NOT NULL, 
    details JSONB NOT NULL, 
    request_id UUID NOT NULL, 
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor_user_id) REFERENCES app_user (id)
);

CREATE INDEX ix_policy_actor_time ON policy_change (actor_user_id, occurred_at);

CREATE INDEX ix_policy_time ON policy_change (occurred_at);

CREATE TABLE resource (
    id SERIAL NOT NULL, 
    resource_type VARCHAR(40) NOT NULL, 
    resource_key VARCHAR(80) NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    owner_user_id INTEGER NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_resource_type CHECK (resource_type ~ '^[a-z][a-z0-9_]{0,39}$'), 
    CONSTRAINT ck_resource_key CHECK (length(trim(resource_key)) > 0), 
    FOREIGN KEY(owner_user_id) REFERENCES app_user (id), 
    CONSTRAINT uq_resource_type_key UNIQUE (resource_type, resource_key)
);

CREATE INDEX ix_resource_owner ON resource (owner_user_id);

CREATE TABLE role_permission (
    role_id INTEGER NOT NULL, 
    permission_id INTEGER NOT NULL, 
    PRIMARY KEY (role_id, permission_id), 
    FOREIGN KEY(permission_id) REFERENCES permission (id), 
    FOREIGN KEY(role_id) REFERENCES role (id)
);

CREATE INDEX ix_role_permission_permission ON role_permission (permission_id);

CREATE TABLE security_event (
    id SERIAL NOT NULL, 
    actor_user_id INTEGER, 
    email VARCHAR(254) NOT NULL, 
    ip_hash VARCHAR(64) NOT NULL, 
    operation VARCHAR(30) NOT NULL, 
    request_id UUID NOT NULL, 
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor_user_id) REFERENCES app_user (id)
);

CREATE INDEX ix_security_email_time ON security_event (email, occurred_at);

CREATE INDEX ix_security_ip_time ON security_event (ip_hash, occurred_at);

CREATE TABLE user_role (
    user_id INTEGER NOT NULL, 
    role_id INTEGER NOT NULL, 
    assigned_by INTEGER NOT NULL, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    PRIMARY KEY (user_id, role_id), 
    FOREIGN KEY(assigned_by) REFERENCES app_user (id), 
    FOREIGN KEY(role_id) REFERENCES role (id), 
    FOREIGN KEY(user_id) REFERENCES app_user (id)
);

CREATE INDEX ix_user_role_role ON user_role (role_id);

CREATE TABLE audit_event (
    id UUID NOT NULL, 
    actor_user_id INTEGER, 
    actor_email VARCHAR(254) NOT NULL, 
    action VARCHAR(6) NOT NULL, 
    resource_id INTEGER, 
    resource_type VARCHAR(40) NOT NULL, 
    resource_key VARCHAR(80) NOT NULL, 
    decision VARCHAR(7) NOT NULL, 
    reason_code VARCHAR(40) NOT NULL, 
    matching_role_id INTEGER, 
    matching_role_name VARCHAR(60), 
    request_id UUID NOT NULL, 
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_audit_match CHECK ((decision = 'ALLOWED' AND reason_code = 'ALLOWED_BY_ROLE' AND matching_role_id IS NOT NULL AND matching_role_name IS NOT NULL) OR (decision = 'DENIED' AND reason_code <> 'ALLOWED_BY_ROLE' AND matching_role_id IS NULL AND matching_role_name IS NULL)), 
    CONSTRAINT ck_audit_action CHECK (action IN ('READ','CREATE','UPDATE','DELETE')), 
    CONSTRAINT ck_audit_decision CHECK (decision IN ('ALLOWED','DENIED')), 
    CONSTRAINT ck_audit_reason CHECK (reason_code IN ('ALLOWED_BY_ROLE','NO_MATCHING_PERMISSION','INACTIVE_ACCOUNT','INACTIVE_RESOURCE','RESOURCE_NOT_FOUND')), 
    FOREIGN KEY(actor_user_id) REFERENCES app_user (id), 
    FOREIGN KEY(matching_role_id) REFERENCES role (id), 
    FOREIGN KEY(resource_id) REFERENCES resource (id), 
    CONSTRAINT uq_audit_actor_request UNIQUE (actor_user_id, request_id)
);

CREATE INDEX ix_audit_actor_time ON audit_event (actor_user_id, occurred_at);

CREATE INDEX ix_audit_decision_time ON audit_event (decision, occurred_at);

CREATE INDEX ix_audit_occurred ON audit_event (occurred_at);

CREATE INDEX ix_audit_resource_time ON audit_event (resource_id, occurred_at);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

COMMIT;

