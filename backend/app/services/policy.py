"""All policy writers acquire the same transaction-scoped PostgreSQL lock."""
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, func, text
from app.models import User, Role, UserRole, Permission, RolePermission, Resource, PolicyChange
from app.security.passwords import hash_password

POLICY_LOCK = 73481021


def roles_for(db, user_id):
    return list(db.scalars(select(Role).join(UserRole, UserRole.role_id == Role.id).where(
        UserRole.user_id == user_id, UserRole.active.is_(True), Role.active.is_(True)).order_by(Role.id)))


def category(db, user_id):
    kinds = {r.kind for r in roles_for(db, user_id)}
    return 'admin' if 'admin' in kinds else 'auditor' if 'auditor' in kinds else 'user'


def effective_permissions(db, user_id):
    return list(db.execute(select(Permission.action, Permission.resource_type).join(
        RolePermission, RolePermission.permission_id == Permission.id).join(Role, Role.id == RolePermission.role_id).join(
        UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id,
        UserRole.active.is_(True), Role.active.is_(True)).distinct().order_by(Permission.resource_type, Permission.action)))


def write_policy(db, actor, target_type, target_id, operation, details, request_id=None):
    db.add(PolicyChange(actor_user_id=actor.id, actor_email=actor.email,
        target_type=target_type, target_id=str(target_id), operation=operation,
        details=details, request_id=request_id or uuid4()))
    db.flush()  # An insert failure must roll back the associated mutation.


def require_target(db, model, ident):
    item = db.get(model, ident)
    if item is None:
        raise HTTPException(404, 'The selected record no longer exists.')
    return item


def guard_admin(db, actor_id):
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': POLICY_LOCK})
    actor = db.get(User, actor_id, populate_existing=True)
    if not actor or not actor.active or category(db, actor_id) != 'admin':
        raise HTTPException(403, 'Administrator access is required.')
    return actor


def protect_last_admin(db):
    db.flush()
    count = db.scalar(select(func.count(func.distinct(User.id))).select_from(User).join(
        UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).where(
        User.active.is_(True), UserRole.active.is_(True), Role.active.is_(True), Role.kind == 'admin'))
    if not count:
        raise HTTPException(409, 'At least one active administrator must remain. Assign another administrator first.')


def mutate(db, actor_id, operation, data, request_id=None):
    """Caller commits; exceptions leave both mutation and audit uncommitted."""
    actor = guard_admin(db, actor_id)
    details = {}
    if operation == 'create_user':
        item = User(name=data['name'], email=str(data['email']).lower(), password_hash=hash_password(data['password']))
        db.add(item); db.flush()
        target_type = 'user'; details = {'name': item.name, 'email': item.email}
    elif operation == 'user_status':
        item = require_target(db, User, data['id'])
        details = {'email': item.email, 'before': item.active, 'after': data['active']}
        item.active = data['active']; target_type = 'user'
    elif operation == 'create_role':
        item = Role(**data, kind='user'); db.add(item); db.flush()
        target_type = 'role'; details = {'name': item.name, 'description': item.description}
    elif operation == 'update_role':
        item = require_target(db, Role, data['id'])
        if item.kind != 'user' and data['name'] != item.name:
            raise HTTPException(409, 'System role names are protected.')
        details = {'before': {'name': item.name, 'description': item.description}, 'after': {'name': data['name'], 'description': data['description']}}
        item.name = data['name']; item.description = data['description']; target_type = 'role'
    elif operation == 'role_status':
        item = require_target(db, Role, data['id'])
        details = {'name': item.name, 'before': item.active, 'after': data['active']}
        item.active = data['active']; target_type = 'role'
    elif operation in ('assign_role', 'revoke_role'):
        user = require_target(db, User, data['user_id']); role = require_target(db, Role, data['role_id'])
        item = db.get(UserRole, (user.id, role.id))
        if operation == 'assign_role':
            if not user.active or not role.active:
                raise HTTPException(409, 'Activate the account and role before assigning.')
            if item and item.active:
                raise HTTPException(409, 'This user already has this role.')
            if not item:
                item = UserRole(user_id=user.id, role_id=role.id, assigned_by=actor.id); db.add(item)
            else:
                item.active = True; item.assigned_by = actor.id; item.assigned_at = func.now()
        else:
            if not item or not item.active:
                raise HTTPException(409, 'This role assignment is already inactive.')
            item.active = False
        target_type = 'user_role'
        details = {'user_id': user.id, 'email': user.email, 'role_id': role.id, 'role_name': role.name}
    elif operation == 'create_permission':
        item = Permission(**data); db.add(item); db.flush()
        target_type = 'permission'; details = data
    elif operation in ('map_permission', 'unmap_permission'):
        role = require_target(db, Role, data['role_id']); perm = require_target(db, Permission, data['permission_id'])
        item = db.get(RolePermission, (role.id, perm.id))
        if operation == 'map_permission':
            if item:
                raise HTTPException(409, 'This permission is already mapped to the role.')
            item = RolePermission(**data); db.add(item)
        else:
            if not item:
                raise HTTPException(409, 'This mapping no longer exists.')
            db.delete(item)
        target_type = 'role_permission'
        details = {**data, 'role_name': role.name, 'action': perm.action, 'resource_type': perm.resource_type}
    elif operation == 'create_resource':
        require_target(db, User, data['owner_user_id'])
        item = Resource(**data); db.add(item); db.flush()
        target_type = 'resource'; details = data
    elif operation == 'resource_status':
        item = require_target(db, Resource, data['id'])
        details = {'key': item.resource_key, 'before': item.active, 'after': data['active']}
        item.active = data['active']; target_type = 'resource'
    else:
        raise HTTPException(400, 'Unknown administrative operation.')
    protect_last_admin(db)
    target = (f"{data['user_id']}:{data['role_id']}" if target_type == 'user_role' else
              f"{data['role_id']}:{data['permission_id']}" if target_type == 'role_permission' else item.id)
    write_policy(db, actor, target_type, target, operation, details, request_id)
    return item
