"""Public JSON contracts. ORM password/session storage fields are never serialized."""
from datetime import datetime
from typing import Generic, TypeVar, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar('T')
Kind = Literal['admin', 'auditor', 'user']


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class RoleOut(Output):
    id: int
    name: str
    description: str
    kind: Kind
    active: bool


class RoleRow(RoleOut):
    member_count: int
    permission_count: int


class UserOut(Output):
    id: int
    name: str
    email: str
    active: bool
    created_at: datetime
    updated_at: datetime


class UserRow(UserOut):
    roles: list[RoleOut]


class PermissionOut(Output):
    id: int
    action: str
    resource_type: str


class EffectivePermission(BaseModel):
    action: str
    resource_type: str


class ResourceOut(Output):
    id: int
    name: str
    resource_type: str
    resource_key: str
    owner_user_id: int
    active: bool


class ResourceRow(ResourceOut):
    owner_name: str


class AuditOut(Output):
    id: UUID
    actor_user_id: int | None
    actor_email: str
    action: str
    resource_id: int | None
    resource_type: str
    resource_key: str
    decision: Literal['ALLOWED','DENIED']
    reason_code: str
    matching_role_id: int | None
    matching_role_name: str | None
    request_id: UUID
    occurred_at: datetime


class PolicyOut(Output):
    id: UUID
    actor_user_id: int
    actor_email: str
    target_type: str
    target_id: str
    operation: str
    details: dict
    request_id: UUID
    occurred_at: datetime


class SecurityOut(Output):
    id: int
    actor_user_id: int | None
    email: str
    operation: str
    request_id: UUID
    occurred_at: datetime


class SessionOut(BaseModel):
    user: UserOut
    category: Kind
    csrf_token: str
    expires_at: datetime
    roles: list[RoleOut]
    permissions: list[EffectivePermission]


class CsrfOut(BaseModel):
    csrf_token: str


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    csrf_token: str = Field(min_length=1, max_length=256)


class StatusInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    active: bool = Field(strict=True)


class AssignmentRow(BaseModel):
    user_id: int
    role_id: int
    user_name: str
    user_email: str
    role_name: str
    role_active: bool
    active: bool
    assigned_by: int
    assigned_at: datetime


class MappingRow(BaseModel):
    role_id: int
    permission_id: int
    role_name: str
    action: str
    resource_type: str


class Option(BaseModel):
    id: int
    label: str
    active: bool = True


class OptionsOut(BaseModel):
    items: list[Option]
    has_more: bool


class DashboardStats(BaseModel):
    events: int
    allowed: int
    denied: int
    users: int
    roles: int
    resources: int
    policies: int
    recent: int
    recent_denied: int


class DashboardOut(BaseModel):
    stats: DashboardStats
    recent: list[AuditOut]
    changes: list[PolicyOut]


class Message(BaseModel):
    message: str
