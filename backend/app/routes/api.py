import csv
import io
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException, Query, Response
from sqlalchemy import select, func, or_, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.config import settings
from app.models import User, Role, Permission, UserRole, RolePermission, Resource, AuditEvent, PolicyChange, LoginSession, SecurityEvent
from app.schemas.api import *
from app.schemas.inputs import UserInput, RoleInput, ResourceInput, PermissionInput, AssignmentInput, MappingInput, AccessInput
from app.security.sessions import COOKIE, login_csrf, valid_login_csrf, identity, csrf_check, csrf_signature
from app.services.authentication import authenticate
from app.services.policy import category, roles_for, effective_permissions, mutate
from app.services.authorization import evaluate
from app.services.reports import audit_query, policy_query

router=APIRouter(prefix='/api')
DB=Annotated[Session,Depends(get_db)]


@dataclass
class Context:
    user: User
    session: LoginSession
    kind: str


def current(request: Request, db: DB):
    user, session=identity(request,db)
    return Context(user,session,category(db,user.id))


Auth=Annotated[Context,Depends(current)]


def admin(request: Request, auth: Auth):
    if auth.kind!='admin': raise HTTPException(403,'Administrator access is required.')
    csrf_check({'csrf_token':request.headers.get('X-CSRF-Token','')},auth.session)
    return auth


def investigator(auth: Auth):
    if auth.kind not in ('admin','auditor'): raise HTTPException(403,'Audit workspace access is required.')
    return auth


Admin=Annotated[Context,Depends(admin)]
Investigator=Annotated[Context,Depends(investigator)]


def session_out(db, user, session):
    return SessionOut(user=UserOut.model_validate(user),category=category(db,user.id),
        csrf_token=session.csrf_token,expires_at=session.expires_at,
        roles=[RoleOut.model_validate(r) for r in roles_for(db,user.id)],
        permissions=[EffectivePermission(action=a,resource_type=t) for a,t in effective_permissions(db,user.id)])


def paged(db, query, page, page_size=20, rows=False):
    total=db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    pages=max(1,(total+page_size-1)//page_size); page=min(page,pages)
    query=query.offset((page-1)*page_size).limit(page_size)
    items=db.execute(query).all() if rows else list(db.scalars(query))
    return {'items':items,'total':total,'page':page,'page_size':page_size,'pages':pages}


PageNumber=Annotated[int,Query(ge=1,le=100000)]
Search=Annotated[str,Query(max_length=200)]
Status=Annotated[str,Query(pattern='^(active|inactive)?$')]


@router.get('/auth/csrf',response_model=CsrfOut)
def csrf(response: Response):
    token=login_csrf()
    response.set_cookie('dac_login_csrf',token,httponly=True,secure=settings().cookie_secure,samesite='strict',max_age=3600)
    return {'csrf_token':token}


@router.post('/auth/login',response_model=SessionOut)
def login(payload: LoginInput,request: Request,response: Response,db: DB):
    token=payload.csrf_token
    if not valid_login_csrf(token) or not secrets.compare_digest(token,request.cookies.get('dac_login_csrf','')):
        raise HTTPException(403,'This sign-in form has expired. Refresh and try again.')
    user,session,bearer=authenticate(db,request,payload.email,payload.password)
    response.set_cookie(COOKIE,bearer,httponly=True,secure=settings().cookie_secure,samesite='lax',max_age=settings().session_hours*3600)
    response.delete_cookie('dac_login_csrf')
    return session_out(db,user,session)


@router.get('/auth/session',response_model=SessionOut)
def get_session(db: DB,auth: Auth):
    return session_out(db,auth.user,auth.session)


@router.post('/auth/logout',response_model=Message)
def logout(request: Request,response: Response,db: DB):
    user,session=identity(request,db,allow_inactive=True)
    csrf_check({'csrf_token':request.headers.get('X-CSRF-Token','')},session)
    db.delete(session)
    db.add(SecurityEvent(actor_user_id=user.id,email=user.email,ip_hash=csrf_signature(request.client.host if request.client else 'unknown'),operation='LOGOUT',request_id=request.state.request_id))
    db.commit();response.delete_cookie(COOKIE)
    return {'message':'Signed out.'}


@router.get('/dashboard',response_model=DashboardOut)
def dashboard(db: DB,auth: Auth):
    scope=select(AuditEvent)
    if auth.kind=='user': scope=scope.where(AuditEvent.actor_user_id==auth.user.id)
    def count(q): return db.scalar(select(func.count()).select_from(q.subquery()))
    total=count(scope);allowed=count(scope.where(AuditEvent.decision=='ALLOWED'))
    recent=scope.where(AuditEvent.occurred_at>=datetime.now(timezone.utc)-timedelta(days=7))
    stats={'events':total,'allowed':allowed,'denied':total-allowed,
        'users':count(select(User).where(User.active.is_(True))),
        'roles':count(select(Role).where(Role.active.is_(True))),
        'resources':count(select(Resource).where(Resource.active.is_(True))),
        'policies':count(select(PolicyChange)) if auth.kind!='user' else 0,
        'recent':count(recent),'recent_denied':count(recent.where(AuditEvent.decision=='DENIED'))}
    changes=list(db.scalars(select(PolicyChange).order_by(PolicyChange.occurred_at.desc(),PolicyChange.id).limit(4))) if auth.kind!='user' else []
    return {'stats':stats,'recent':list(db.scalars(scope.order_by(AuditEvent.occurred_at.desc(),AuditEvent.id).limit(6))),'changes':changes}


@router.get('/users',response_model=Page[UserRow])
def users(db: DB,auth: Investigator,page: PageNumber=1,q: Search='',status: Status='',sort: str='name'):
    if auth.kind!='admin': raise HTTPException(403,'Administrator access is required.')
    query=select(User)
    if q: query=query.where(or_(User.name.icontains(q,autoescape=True),User.email.icontains(q,autoescape=True)))
    if status: query=query.where(User.active==(status=='active'))
    sorts={'name':User.name.asc(),'email':User.email.asc(),'newest':User.created_at.desc()}
    if sort not in sorts: raise HTTPException(422,'Choose a supported sort order.')
    result=paged(db,query.order_by(sorts[sort],User.id),page)
    result['items']=[UserRow(**UserOut.model_validate(u).model_dump(),roles=roles_for(db,u.id)) for u in result['items']]
    return result


@router.get('/roles',response_model=Page[RoleRow])
def roles(db: DB,auth: Auth,page: PageNumber=1,q: Search='',status: Status='',sort: str='name'):
    if auth.kind!='admin': raise HTTPException(403,'Administrator access is required.')
    query=select(Role)
    if q: query=query.where(Role.name.icontains(q,autoescape=True))
    if status: query=query.where(Role.active==(status=='active'))
    sorts={'name':Role.name.asc(),'category':Role.kind.asc()}
    if sort not in sorts: raise HTTPException(422,'Choose a supported sort order.')
    result=paged(db,query.order_by(sorts[sort],Role.id),page)
    result['items']=[RoleRow(**RoleOut.model_validate(r).model_dump(),
        member_count=db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_id==r.id,UserRole.active.is_(True))),
        permission_count=db.scalar(select(func.count()).select_from(RolePermission).where(RolePermission.role_id==r.id))) for r in result['items']]
    return result


@router.get('/permissions',response_model=Page[PermissionOut])
def permissions(db: DB,auth: Auth,page: PageNumber=1,q: Search=''):
    if auth.kind!='admin': raise HTTPException(403,'Administrator access is required.')
    query=select(Permission)
    if q: query=query.where(or_(Permission.resource_type.icontains(q,autoescape=True),Permission.action.icontains(q,autoescape=True)))
    return paged(db,query.order_by(Permission.resource_type,Permission.action),page)


@router.get('/mappings',response_model=Page[MappingRow])
def mappings(db: DB,auth: Auth,page: PageNumber=1,q: Search=''):
    if auth.kind!='admin': raise HTTPException(403,'Administrator access is required.')
    query=select(RolePermission,Role,Permission).join(Role,Role.id==RolePermission.role_id).join(Permission,Permission.id==RolePermission.permission_id)
    if q: query=query.where(or_(Role.name.icontains(q,autoescape=True),Permission.resource_type.icontains(q,autoescape=True)))
    result=paged(db,query.order_by(Role.name,Permission.resource_type,Permission.action),page,rows=True)
    result['items']=[MappingRow(role_id=r.id,permission_id=p.id,role_name=r.name,action=p.action,resource_type=p.resource_type) for _,r,p in result['items']]
    return result


@router.get('/assignments',response_model=Page[AssignmentRow])
def assignments(db: DB,auth: Auth,page: PageNumber=1,q: Search='',status: Status=''):
    if auth.kind!='admin': raise HTTPException(403,'Administrator access is required.')
    query=select(UserRole,User,Role).join(User,User.id==UserRole.user_id).join(Role,Role.id==UserRole.role_id)
    if q: query=query.where(or_(User.email.icontains(q,autoescape=True),User.name.icontains(q,autoescape=True),Role.name.icontains(q,autoescape=True)))
    if status: query=query.where(UserRole.active==(status=='active'))
    result=paged(db,query.order_by(User.name,Role.name),page,rows=True)
    result['items']=[AssignmentRow(user_id=u.id,role_id=r.id,user_name=u.name,user_email=u.email,role_name=r.name,role_active=r.active,active=a.active,assigned_by=a.assigned_by,assigned_at=a.assigned_at) for a,u,r in result['items']]
    return result


@router.get('/resources',response_model=Page[ResourceRow])
def resources(db: DB,auth: Auth,page: PageNumber=1,q: Search='',status: Status='',type: Annotated[str,Query(max_length=40)]='',sort: str='name'):
    query=select(Resource,User.name).join(User,User.id==Resource.owner_user_id)
    if q: query=query.where(or_(Resource.name.icontains(q,autoescape=True),Resource.resource_key.icontains(q,autoescape=True)))
    if status: query=query.where(Resource.active==(status=='active'))
    if type: query=query.where(Resource.resource_type==type)
    sorts={'name':Resource.name.asc(),'key':Resource.resource_key.asc(),'type':Resource.resource_type.asc()}
    if sort not in sorts: raise HTTPException(422,'Choose a supported sort order.')
    result=paged(db,query.order_by(sorts[sort],Resource.id),page,rows=True)
    result['items']=[ResourceRow(**ResourceOut.model_validate(r).model_dump(),owner_name=n) for r,n in result['items']]
    return result


@router.get('/options/{collection}',response_model=OptionsOut)
def options(collection: str,db: DB,auth: Auth,q: Search='',selected_id: Annotated[int|None,Query(gt=0)]=None):
    models={'users':User,'roles':Role,'resources':Resource,'permissions':Permission}
    if collection not in models: raise HTTPException(404,'Unknown selection list.')
    if collection in ('users','roles','permissions') and auth.kind!='admin':
        # Investigators can select actors; other policy options remain administrator-only.
        if collection!='users' or auth.kind!='auditor': raise HTTPException(403,'This selection list is restricted.')
    model=models[collection]
    query=select(model)
    if q:
        columns=[User.name,User.email] if model is User else [Role.name] if model is Role else [Resource.name,Resource.resource_key] if model is Resource else [Permission.action,Permission.resource_type]
        query=query.where(or_(*(c.icontains(q,autoescape=True) for c in columns)))
    records=list(db.scalars(query.order_by(model.id).limit(51)));has_more=len(records)>50;records=records[:50]
    if selected_id and not any(r.id==selected_id for r in records):
        selected=db.get(model,selected_id)
        if selected: records=[selected,*records]
    def label(r):
        if isinstance(r,User): return f'{r.name} · {r.email}'
        if isinstance(r,Resource): return f'{r.resource_type.capitalize()} · {r.resource_key} · {r.name}'
        if isinstance(r,Permission): return f'{r.action} · {r.resource_type}'
        return r.name
    return {'items':[Option(id=r.id,label=label(r),active=getattr(r,'active',True)) for r in records],'has_more':has_more}


@router.post('/access',response_model=AuditOut)
def access(payload: AccessInput,request: Request,db: DB):
    user,session=identity(request,db,allow_inactive=True)
    if category(db,user.id)=='auditor': raise HTTPException(403,'Auditors have read-only access.')
    csrf_check({'csrf_token':request.headers.get('X-CSRF-Token','')},session)
    request.state.request_id=payload.request_id
    event=evaluate(db,user.id,**payload.model_dump());db.commit()
    return event


@router.get('/audit',response_model=Page[AuditOut])
def audit(request: Request,db: DB,auth: Investigator,page: PageNumber=1):
    return paged(db,audit_query(request.query_params),page)


@router.get('/history',response_model=Page[AuditOut])
def history(request: Request,db: DB,auth: Auth,page: PageNumber=1):
    return paged(db,audit_query(request.query_params,auth.user.id),page)


@router.get('/events/{event_id}',response_model=AuditOut)
def event_detail(event_id: UUID,db: DB,request: Request):
    user,_=identity(request,db,allow_inactive=True)
    event=db.get(AuditEvent,event_id)
    if not event: raise HTTPException(404,'This event does not exist.')
    if event.actor_user_id!=user.id and (not user.active or category(db,user.id) not in ('admin','auditor')):
        raise HTTPException(403,'You can only view your own access decisions.')
    return event


@router.get('/policy',response_model=Page[PolicyOut])
def policy(request: Request,db: DB,auth: Investigator,page: PageNumber=1):
    return paged(db,policy_query(request.query_params),page)


@router.get('/security',response_model=Page[SecurityOut])
def security(db: DB,auth: Investigator,page: PageNumber=1,q: Search=''):
    query=select(SecurityEvent)
    if q: query=query.where(SecurityEvent.email.icontains(q,autoescape=True))
    return paged(db,query.order_by(SecurityEvent.occurred_at.desc(),SecurityEvent.id.desc()),page)


def csv_cell(value):
    value=str(value) if value is not None else ''
    return "'"+value if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')) else value


@router.get('/audit/export')
def export(request: Request,db: DB,auth: Investigator):
    events=list(db.scalars(audit_query(request.query_params,export=True).limit(5001)))
    if len(events)>5000: raise HTTPException(422,'More than 5,000 events match. Narrow your filters before exporting.')
    stream=io.StringIO(newline='');writer=csv.writer(stream)
    fields=['id','occurred_at','actor_email','action','resource_type','resource_key','decision','reason_code','matching_role_name','request_id']
    writer.writerow(fields)
    for event in events: writer.writerow([csv_cell(getattr(event,f)) for f in fields])
    return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="access-audit.csv"'})


def apply(db,auth,request,operation,data):
    try:
        result=mutate(db,auth.user.id,operation,data,request.state.request_id);db.commit();return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'This entry conflicts with an existing record. Names, email addresses and mappings must be unique.')


@router.post('/users',response_model=UserOut,status_code=201)
def create_user(payload: UserInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'create_user',payload.model_dump())


@router.patch('/users/{ident}/status',response_model=UserOut)
def user_status(ident: int,payload: StatusInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'user_status',{'id':ident,**payload.model_dump()})


@router.post('/roles',response_model=RoleOut,status_code=201)
def create_role(payload: RoleInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'create_role',payload.model_dump())


@router.put('/roles/{ident}',response_model=RoleOut)
def update_role(ident: int,payload: RoleInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'update_role',{'id':ident,**payload.model_dump()})


@router.patch('/roles/{ident}/status',response_model=RoleOut)
def role_status(ident: int,payload: StatusInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'role_status',{'id':ident,**payload.model_dump()})


@router.post('/permissions',response_model=PermissionOut,status_code=201)
def create_permission(payload: PermissionInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'create_permission',payload.model_dump())


@router.post('/resources',response_model=ResourceOut,status_code=201)
def create_resource(payload: ResourceInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'create_resource',payload.model_dump())


@router.patch('/resources/{ident}/status',response_model=ResourceOut)
def resource_status(ident: int,payload: StatusInput,request: Request,db: DB,auth: Admin):
    return apply(db,auth,request,'resource_status',{'id':ident,**payload.model_dump()})


@router.post('/assignments',response_model=Message,status_code=201)
def assign(payload: AssignmentInput,request: Request,db: DB,auth: Admin):
    apply(db,auth,request,'assign_role',payload.model_dump());return {'message':'Role assigned. Policy history updated.'}


@router.delete('/assignments/{user_id}/{role_id}',response_model=Message)
def revoke(user_id: int,role_id: int,request: Request,db: DB,auth: Admin):
    apply(db,auth,request,'revoke_role',{'user_id':user_id,'role_id':role_id});return {'message':'Role revoked. Policy history updated.'}


@router.post('/mappings',response_model=Message,status_code=201)
def map_permission(payload: MappingInput,request: Request,db: DB,auth: Admin):
    apply(db,auth,request,'map_permission',payload.model_dump());return {'message':'Permission mapped. Policy history updated.'}


@router.delete('/mappings/{role_id}/{permission_id}',response_model=Message)
def unmap(role_id: int,permission_id: int,request: Request,db: DB,auth: Admin):
    apply(db,auth,request,'unmap_permission',{'role_id':role_id,'permission_id':permission_id});return {'message':'Mapping removed. Policy history updated.'}
