from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import (String, Text, Boolean, ForeignKey, CheckConstraint,
                        UniqueConstraint, Index, DateTime, Integer, func)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = 'app_user'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, server_default='true')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (CheckConstraint("email = lower(email)", name='ck_user_email_lower'),
                      CheckConstraint("length(trim(name)) > 0", name='ck_user_name'))


class Role(Base):
    __tablename__ = 'role'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    description: Mapped[str] = mapped_column(String(300), server_default='')
    kind: Mapped[str] = mapped_column(String(10), server_default='user')
    active: Mapped[bool] = mapped_column(Boolean, server_default='true')
    __table_args__ = (CheckConstraint("kind IN ('admin','auditor','user')", name='ck_role_kind'),
                      CheckConstraint("length(trim(name)) > 0", name='ck_role_name'))


class Permission(Base):
    __tablename__ = 'permission'
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(6))
    resource_type: Mapped[str] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint('action', 'resource_type', name='uq_permission_action_type'),
                      CheckConstraint("action IN ('READ','CREATE','UPDATE','DELETE')", name='ck_permission_action'),
                      CheckConstraint("resource_type ~ '^[a-z][a-z0-9_]{0,39}$'", name='ck_permission_type'))


class UserRole(Base):
    __tablename__ = 'user_role'
    user_id: Mapped[int] = mapped_column(ForeignKey('app_user.id'), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('role.id'), primary_key=True)
    assigned_by: Mapped[int] = mapped_column(ForeignKey('app_user.id'))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, server_default='true')
    __table_args__ = (Index('ix_user_role_role', 'role_id'),)


class RolePermission(Base):
    __tablename__ = 'role_permission'
    role_id: Mapped[int] = mapped_column(ForeignKey('role.id'), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey('permission.id'), primary_key=True)
    __table_args__ = (Index('ix_role_permission_permission', 'permission_id'),)


class Resource(Base):
    __tablename__ = 'resource'
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_key: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey('app_user.id'))
    active: Mapped[bool] = mapped_column(Boolean, server_default='true')
    __table_args__ = (UniqueConstraint('resource_type', 'resource_key', name='uq_resource_type_key'),
                      CheckConstraint("resource_type ~ '^[a-z][a-z0-9_]{0,39}$'", name='ck_resource_type'),
                      CheckConstraint("length(trim(resource_key)) > 0", name='ck_resource_key'),
                      Index('ix_resource_owner', 'owner_user_id'))


class AuditEvent(Base):
    __tablename__ = 'audit_event'
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('app_user.id'))
    actor_email: Mapped[str] = mapped_column(String(254))
    action: Mapped[str] = mapped_column(String(6))
    resource_id: Mapped[int | None] = mapped_column(ForeignKey('resource.id'))
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_key: Mapped[str] = mapped_column(String(80))
    decision: Mapped[str] = mapped_column(String(7))
    reason_code: Mapped[str] = mapped_column(String(40))
    matching_role_id: Mapped[int | None] = mapped_column(ForeignKey('role.id'))
    matching_role_name: Mapped[str | None] = mapped_column(String(60))
    request_id: Mapped[UUID] = mapped_column(PGUUID)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('actor_user_id', 'request_id', name='uq_audit_actor_request'),
        CheckConstraint("decision IN ('ALLOWED','DENIED')", name='ck_audit_decision'),
        CheckConstraint("action IN ('READ','CREATE','UPDATE','DELETE')", name='ck_audit_action'),
        CheckConstraint("reason_code IN ('ALLOWED_BY_ROLE','NO_MATCHING_PERMISSION','INACTIVE_ACCOUNT','INACTIVE_RESOURCE','RESOURCE_NOT_FOUND')", name='ck_audit_reason'),
        CheckConstraint("(decision = 'ALLOWED' AND reason_code = 'ALLOWED_BY_ROLE' AND matching_role_id IS NOT NULL AND matching_role_name IS NOT NULL) OR (decision = 'DENIED' AND reason_code <> 'ALLOWED_BY_ROLE' AND matching_role_id IS NULL AND matching_role_name IS NULL)", name='ck_audit_match'),
        Index('ix_audit_occurred', 'occurred_at'),
        Index('ix_audit_actor_time', 'actor_user_id', 'occurred_at'),
        Index('ix_audit_decision_time', 'decision', 'occurred_at'),
        Index('ix_audit_resource_time', 'resource_id', 'occurred_at'))


class PolicyChange(Base):
    __tablename__ = 'policy_change'
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('app_user.id'))
    actor_email: Mapped[str] = mapped_column(String(254))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[str] = mapped_column(String(80))
    operation: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict] = mapped_column(JSONB)
    request_id: Mapped[UUID] = mapped_column(PGUUID, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_policy_time', 'occurred_at'),
                      Index('ix_policy_actor_time', 'actor_user_id', 'occurred_at'))


class LoginSession(Base):
    __tablename__ = 'login_session'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('app_user.id'), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SecurityEvent(Base):
    __tablename__ = 'security_event'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('app_user.id'))
    email: Mapped[str] = mapped_column(String(254))
    ip_hash: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(30))
    request_id: Mapped[UUID] = mapped_column(PGUUID, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_security_ip_time', 'ip_hash', 'occurred_at'),
                      Index('ix_security_email_time', 'email', 'occurred_at'))
