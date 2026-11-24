from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class UserInput(Input):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('password', mode='before')
    @classmethod
    def password_not_trimmed(cls, v):
        # Password whitespace is significant; surrounding whitespace is rejected explicitly.
        if isinstance(v, str) and v != v.strip():
            raise ValueError('Password must not start or end with whitespace')
        return v


class RoleInput(Input):
    name: str = Field(min_length=2, max_length=60)
    description: str = Field(default='', max_length=300)


class PermissionInput(Input):
    action: Literal['READ', 'CREATE', 'UPDATE', 'DELETE']
    resource_type: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')


class ResourceInput(Input):
    name: str = Field(min_length=2, max_length=120)
    resource_type: str = Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    resource_key: str = Field(min_length=1, max_length=80)
    owner_user_id: int = Field(gt=0)


class AssignmentInput(Input):
    user_id: int = Field(gt=0)
    role_id: int = Field(gt=0)


class MappingInput(Input):
    role_id: int = Field(gt=0)
    permission_id: int = Field(gt=0)


class AccessInput(Input):
    action: Literal['READ', 'CREATE', 'UPDATE', 'DELETE']
    resource_id: int = Field(gt=0)
    request_id: UUID
