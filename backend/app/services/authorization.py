from fastapi import HTTPException
from sqlalchemy import select, text
from app.models import AuditEvent, User, Resource, Role, Permission, UserRole, RolePermission
from app.services.policy import POLICY_LOCK


def evaluate(db, actor_id, action, resource_id, request_id):
    # Shared policy lock provides a coherent policy snapshot while writes are serialized.
    db.execute(text('SELECT pg_advisory_xact_lock_shared(:key)'), {'key': POLICY_LOCK})
    # Lock the actor to serialize same-actor retries, including simultaneous requests.
    actor = db.scalar(select(User).where(User.id == actor_id).with_for_update().execution_options(populate_existing=True))
    if not actor:
        raise HTTPException(401, 'Please sign in again.')
    previous = db.scalar(select(AuditEvent).where(AuditEvent.actor_user_id == actor_id, AuditEvent.request_id == request_id))
    if previous:
        if previous.action != action or (previous.resource_id or int(previous.resource_key)) != resource_id:
            raise HTTPException(409, 'This request ID was already used for a different operation.')
        return previous
    resource = db.get(Resource, resource_id, populate_existing=True)
    role = None
    if not actor.active:
        reason = 'INACTIVE_ACCOUNT'
    elif not resource:
        reason = 'RESOURCE_NOT_FOUND'
    elif not resource.active:
        reason = 'INACTIVE_RESOURCE'
    else:
        role = db.scalar(select(Role).join(UserRole, UserRole.role_id == Role.id).join(
            RolePermission, RolePermission.role_id == Role.id).join(Permission, Permission.id == RolePermission.permission_id).where(
            UserRole.user_id == actor.id, UserRole.active.is_(True), Role.active.is_(True),
            Permission.action == action, Permission.resource_type == resource.resource_type).order_by(Role.id).limit(1).execution_options(populate_existing=True))
        reason = 'ALLOWED_BY_ROLE' if role else 'NO_MATCHING_PERMISSION'
    event = AuditEvent(actor_user_id=actor.id, actor_email=actor.email, action=action,
        resource_id=resource.id if resource else None,
        resource_type=resource.resource_type if resource else 'unknown',
        resource_key=resource.resource_key if resource else str(resource_id),
        decision='ALLOWED' if role else 'DENIED', reason_code=reason,
        matching_role_id=role.id if role else None, matching_role_name=role.name if role else None, request_id=request_id)
    db.add(event)
    db.flush()
    # Caller commits BEFORE rendering or returning a decision.
    return event
