"""Synthetic development fixture. Never run against a production dataset."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select, func, text
from app.database import SessionLocal
from app.models import User, Role, Permission, UserRole, RolePermission, Resource, AuditEvent, PolicyChange
from app.security.passwords import hash_password
from app.services.authorization import evaluate

DEMO_PASSWORD = 'AccessDemo!2026#'


def seed(db):
    db.execute(text('SELECT pg_advisory_xact_lock(73481021)'))
    if db.scalar(select(func.count()).select_from(User)):
        return False
    now = datetime.now(timezone.utc)
    people = [
        ('Alex Morgan','admin@example.com',True),
        ('Maya Chen','maya.admin@example.com',True),
        ('Omar Siddiqui','omar.admin@example.com',True),
        ('Jordan Ellis','auditor@example.com',True),
        ('Leila Hassan','leila.auditor@example.com',True),
        ('Noah Bennett','noah.auditor@example.com',True),
        ('Samira Khan','analyst@example.com',True),
        ('Daniel Park','editor@example.com',True),
        ('Priya Shah','viewer@example.com',True),
        ('Evan Brooks','inactive@example.com',False),
    ]
    users = [User(name=n,email=e,active=a,password_hash=hash_password(DEMO_PASSWORD), created_at=now-timedelta(days=30-i)) for i,(n,e,a) in enumerate(people)]
    db.add_all(users); db.flush()
    roles = [Role(name='Administrator', description='Manage accounts, roles, permissions and registered resources.', kind='admin'),
             Role(name='Auditor',description='Investigate access decisions and administrative history.',kind='auditor'),
             Role(name='Report Analyst',description='Read registered reports.',kind='user'),
             Role(name='Document Editor',description='Read, create and update registered documents.',kind='user'),
             Role(name='Document Viewer',description='Read registered documents.',kind='user'),
             Role(name='Legacy Reviewer',description='Retired review role retained for historical reference.',kind='user',active=False)]
    db.add_all(roles); db.flush()
    permissions = [Permission(action=a,resource_type=t) for t in ['document','report'] for a in ['READ','CREATE','UPDATE','DELETE']]
    db.add_all(permissions); db.flush()
    for role in roles:
        for perm in permissions:
            if role.kind == 'admin' or (role.name == 'Report Analyst' and perm.action == 'READ' and perm.resource_type == 'report') or (role.name == 'Document Editor' and perm.resource_type == 'document' and perm.action in ('READ','CREATE','UPDATE')) or (role.name == 'Document Viewer' and perm.action == 'READ' and perm.resource_type == 'document'):
                db.add(RolePermission(role_id=role.id,permission_id=perm.id))
    assignment_pairs = [(0,0),(1,0),(2,0),(3,1),(4,1),(5,1),(6,2),(6,4),(7,3),(8,4),(9,2)]
    for i,(ui,ri) in enumerate(assignment_pairs):
        db.add(UserRole(user_id=users[ui].id,role_id=roles[ri].id,assigned_by=users[0].id,assigned_at=now-timedelta(days=24,hours=i)))
        db.add(PolicyChange(actor_user_id=users[0].id,actor_email=users[0].email,target_type='user_role',target_id=f'{users[ui].id}:{roles[ri].id}',operation='assign_role',details={'user_id':users[ui].id,'email':users[ui].email,'role_id':roles[ri].id,'role_name':roles[ri].name,'source':'synthetic seed'},occurred_at=now-timedelta(days=24,hours=i)))
    db.add(UserRole(user_id=users[8].id,role_id=roles[5].id,assigned_by=users[1].id,active=False,assigned_at=now-timedelta(days=23)))
    for operation, days in [('assign_role',23),('revoke_role',22)]:
        db.add(PolicyChange(actor_user_id=users[1].id,actor_email=users[1].email,target_type='user_role',target_id=f'{users[8].id}:{roles[5].id}',operation=operation,details={'user_id':users[8].id,'email':users[8].email,'role_id':roles[5].id,'role_name':roles[5].name,'source':'synthetic seed'},occurred_at=now-timedelta(days=days)))
    names = [('report','R42','Quarterly operations report'),('report','R43','Monthly risk review'),('report','R44','Access compliance summary'),('report','R45','Annual finance overview'),('report','R46','Archived vendor assessment'),('report','R47','Service availability report'),('document','D100','Employee handbook'),('document','D101','Information security policy'),('document','D102','Vendor onboarding guide'),('document','D103','Incident response procedure'),('document','D104','Data retention standard'),('document','D105','Archived project brief'),('document','D106','Operations runbook'),('document','D107','Change management procedure'),('report','R48','Resource utilization report'),('document','D108','Internal review checklist')]
    resources = [Resource(resource_type=t,resource_key=k,name=n,owner_user_id=users[6 if t=='report' else 7].id,active=k not in ('R46','D105')) for t,k,n in names]
    db.add_all(resources); db.flush()
    # Run the real authorization engine so every seeded decision matches actual rules.
    for i in range(180):
        actor = users[[0,6,7,8,9][i%5]]
        resource = resources[i%len(resources)]
        action = ['READ','UPDATE','CREATE','DELETE'][i%4] if i%3 else 'READ'
        event = evaluate(db, actor.id, action, resource.id, uuid4())
        event.occurred_at = now-timedelta(days=i%21,hours=i%24,minutes=i%60)
    db.flush()
    return True


if __name__ == '__main__':
    with SessionLocal() as db:
        changed = seed(db); db.commit()
        print('Loaded synthetic demo dataset.' if changed else 'Existing dataset retained; seed skipped.')
