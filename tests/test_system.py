import csv
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4
import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session
from app.models import *
from app.services.authorization import evaluate
from app.services.policy import mutate, roles_for, effective_permissions
from app.security.sessions import digest
from app.security.passwords import verify_password
from app.routes.api import csv_cell


def test_authentication_session_and_logout(client,sign_in,db):
    response,csrf=sign_in();assert response.status_code==200
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
    session_key=digest(client.cookies['dac_session']);stored=db.get(LoginSession,session_key)
    assert stored and stored.token_hash!=client.cookies['dac_session']
    assert response.json()['category']=='admin' and 'password_hash' not in response.text
    assert client.get('/api/dashboard').status_code==200
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':csrf}).status_code==200
    db.expire_all();assert db.get(LoginSession,session_key) is None
    assert client.get('/api/dashboard').status_code==401
    assert db.scalar(select(func.count()).select_from(SecurityEvent))==2


@pytest.mark.parametrize('email,password',[('admin@example.com','wrong-password'),('missing@example.com','AccessDemo!2026#'),('inactive@example.com','AccessDemo!2026#'),("' OR 1=1 --",'anything')])
def test_invalid_authentication(client,sign_in,db,email,password):
    result,csrf=sign_in(email,password)
    assert result.status_code==400 and csrf is None
    assert not client.cookies.get('dac_session')
    assert db.scalar(select(func.count()).select_from(SecurityEvent).where(SecurityEvent.operation=='LOGIN_FAILED'))==1


def test_login_csrf_and_throttle(client,sign_in):
    assert client.post('/api/auth/login',json={'email':'admin@example.com','password':'AccessDemo!2026#','csrf_token':'forged'}).status_code==403
    for _ in range(10): assert sign_in(password='invalid-password')[0].status_code==400
    assert sign_in()[0].status_code==429


@pytest.mark.parametrize('path',['dashboard','users','roles','permissions','mappings','assignments','resources','audit','policy','auth/session'])
def test_protected_routes(client,path):
    assert client.get('/api/'+path).status_code==401


@pytest.mark.parametrize('email,path', [('admin@example.com',p) for p in ['dashboard','users','roles','permissions','mappings','assignments','resources','audit','policy','security','auth/session','history','options/users','options/resources']] + [('analyst@example.com',p) for p in ['dashboard','auth/session','resources','history','options/resources']] + [('auditor@example.com',p) for p in ['dashboard','audit','policy','security','resources','auth/session','options/users']])
def test_role_api_views(client,sign_in,email,path):
    sign_in(email);response=client.get('/api/'+path)
    assert response.status_code==200,response.text
    assert 'password_hash' not in response.text and 'token_hash' not in response.text
    assert 'Content-Security-Policy' in response.headers


@pytest.mark.parametrize('email,path',[('analyst@example.com','users'),('analyst@example.com','audit'),('analyst@example.com','policy'),('auditor@example.com','users'),('auditor@example.com','permissions'),('auditor@example.com','mappings')])
def test_role_restrictions(client,sign_in,email,path):
    sign_in(email);assert client.get('/api/'+path).status_code==403


@pytest.mark.parametrize('email',['analyst@example.com','auditor@example.com'])
def test_unauthorized_administrative_actions(client,sign_in,db,email):
    _,csrf=sign_in(email);before=db.scalar(select(func.count()).select_from(User))
    response=client.post('/api/users',headers={'X-CSRF-Token':csrf},json={'name':'Unauthorized User','email':'bad@example.com','password':'VeryLongPassword123!'})
    assert response.status_code==403
    assert db.scalar(select(func.count()).select_from(User))==before
    if email=='auditor@example.com': assert client.post('/api/access',headers={'X-CSRF-Token':csrf},json={'action':'READ','resource_id':1,'request_id':str(uuid4())}).status_code==403


def test_csrf_and_session_expiry(client,sign_in,db):
    sign_in()
    assert client.post('/api/roles',json={'name':'Forbidden'}).status_code==403
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':'forged'}).status_code==403
    session=db.get(LoginSession,digest(client.cookies['dac_session']))
    session.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1);db.commit()
    assert client.get('/api/users').status_code==401


@pytest.mark.parametrize('actor,action,resource,decision,reason', [
    (7,'READ',1,'ALLOWED','ALLOWED_BY_ROLE'),(7,'DELETE',1,'DENIED','NO_MATCHING_PERMISSION'),
    (10,'READ',1,'DENIED','INACTIVE_ACCOUNT'),(7,'READ',5,'DENIED','INACTIVE_RESOURCE'),
    (7,'READ',9999,'DENIED','RESOURCE_NOT_FOUND'),(8,'UPDATE',7,'ALLOWED','ALLOWED_BY_ROLE'),
    (9,'READ',1,'DENIED','NO_MATCHING_PERMISSION'),(7,'READ',7,'ALLOWED','ALLOWED_BY_ROLE')])
def test_authorization_rules(db,actor,action,resource,decision,reason):
    request_id=uuid4()
    event=evaluate(db,actor,action,resource,request_id);db.commit()
    saved=db.get(AuditEvent,event.id)
    assert saved.decision==decision and saved.reason_code==reason and saved.request_id==request_id
    assert saved.occurred_at and saved.actor_email


def test_default_deny_no_roles(db):
    db.execute(text('UPDATE user_role SET active=false WHERE user_id=7'));db.commit()
    assert evaluate(db,7,'READ',1,uuid4()).decision=='DENIED'


def test_inactive_role_and_assignment(db):
    db.get(Role,3).active=False;db.commit()
    assert evaluate(db,7,'READ',1,uuid4()).decision=='DENIED'
    assert evaluate(db,7,'READ',7,uuid4()).decision=='ALLOWED'


def test_multiple_roles_deterministic_match_and_history(db):
    mutate(db,1,'assign_role',{'user_id':7,'role_id':4});db.commit()
    event=evaluate(db,7,'READ',7,uuid4());db.commit()
    assert event.matching_role_id==4  # Editor before Viewer by role ID.
    snapshot=event.matching_role_name
    mutate(db,1,'revoke_role',{'user_id':7,'role_id':4});db.commit()
    event2=evaluate(db,7,'READ',7,uuid4());db.commit()
    assert event2.matching_role_id==5
    assert db.get(AuditEvent,event.id).matching_role_name==snapshot
    assert ('READ','document') in effective_permissions(db,7)


def test_revocation_and_atomic_policy_history(db):
    original=db.scalar(select(func.count()).select_from(PolicyChange))
    mutate(db,1,'revoke_role',{'user_id':7,'role_id':3});db.commit()
    assert evaluate(db,7,'READ',1,uuid4()).reason_code=='NO_MATCHING_PERMISSION'
    assert db.scalar(select(func.count()).select_from(PolicyChange))==original+1
    change=db.scalar(select(PolicyChange).where(PolicyChange.operation=='revoke_role',PolicyChange.actor_user_id==1))
    assert change.details['user_id']==7 and change.details['role_name']=='Report Analyst'


@pytest.mark.parametrize('statement',[
    'INSERT INTO user_role(user_id,role_id,assigned_by) VALUES(7,3,1)',
    'INSERT INTO user_role(user_id,role_id,assigned_by) VALUES(9999,3,1)',
    'INSERT INTO role_permission(role_id,permission_id) VALUES(1,1)',
    "INSERT INTO permission(action,resource_type) VALUES('READ','report')",
    "INSERT INTO permission(action,resource_type) VALUES('EXEC','report')",
    "INSERT INTO resource(resource_type,resource_key,name,owner_user_id) VALUES('report','R42','Duplicate',7)",
    "INSERT INTO app_user(name,email,password_hash) VALUES('Dup','admin@example.com','hash')",
    "INSERT INTO role(name,kind) VALUES('Invalid','owner')",
    "INSERT INTO resource(resource_type,resource_key,name,owner_user_id) VALUES('report','Orphan','Bad owner',9999)"])
def test_database_constraints(db,statement):
    with pytest.raises(IntegrityError):
        db.execute(text(statement));db.commit()
    db.rollback()


def test_duplicate_assignment_prevention_and_reactivation(db):
    with pytest.raises(HTTPException) as exc: mutate(db,1,'assign_role',{'user_id':7,'role_id':3})
    assert exc.value.status_code==409;db.rollback()
    mutate(db,1,'revoke_role',{'user_id':7,'role_id':3});db.commit()
    mutate(db,1,'assign_role',{'user_id':7,'role_id':3});db.commit()
    assert db.get(UserRole,(7,3)).active
    assert db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id==7,UserRole.role_id==3))==1


@pytest.mark.parametrize('operation,data', [('user_status',{'id':1,'active':False}),('revoke_role',{'user_id':1,'role_id':1}),('role_status',{'id':1,'active':False})])
def test_last_admin_protection(db,operation,data):
    db.get(User,2).active=False;db.get(User,3).active=False;db.commit()
    before=db.scalar(select(func.count()).select_from(PolicyChange))
    with pytest.raises(HTTPException) as exc: mutate(db,1,operation,data)
    assert exc.value.status_code==409;db.rollback()
    assert db.get(User,1).active and db.get(UserRole,(1,1)).active and db.get(Role,1).active
    assert db.scalar(select(func.count()).select_from(PolicyChange))==before


def test_concurrent_last_admin_removals(pg_engine,db):
    db.get(User,3).active=False;db.commit()
    barrier=Barrier(2)
    def deactivate(actor):
        with Session(pg_engine) as session:
            barrier.wait(timeout=5)
            try:
                mutate(session,actor,'user_status',{'id':actor,'active':False});session.commit();return 'ok'
            except HTTPException as e:
                session.rollback();return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(deactivate,[1,2]))
    assert sorted(str(x) for x in results)==['409','ok']
    db.expire_all()
    assert sum(db.get(User,i).active for i in [1,2,3])==1


def test_request_id_replay_and_conflict(client,sign_in,db):
    _,csrf=sign_in('analyst@example.com');rid=str(uuid4())
    payload={'action':'READ','resource_id':1,'request_id':rid}
    headers={'X-CSRF-Token':csrf}
    one=client.post('/api/access',json=payload,headers=headers)
    two=client.post('/api/access',json=payload,headers=headers)
    assert one.status_code==200 and one.json()==two.json()
    assert one.headers['x-request-id']==rid
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.request_id==UUID(rid)))==1
    conflict=client.post('/api/access',json={**payload,'action':'DELETE'},headers=headers)
    assert conflict.status_code==409
    assert client.post('/api/access',json={**payload,'actor_user_id':1},headers=headers).status_code==422


def test_concurrent_idempotent_access(pg_engine,db):
    rid=uuid4();barrier=Barrier(2)
    def request(_):
        with Session(pg_engine) as session:
            barrier.wait(timeout=5)
            event=evaluate(session,7,'READ',1,rid);session.commit();return event.id
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(request,[1,2]))
    assert results[0]==results[1]
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.request_id==rid))==1


def install_failure(engine,table):
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE OR REPLACE FUNCTION reject_test_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected audit failure'; END $$")
        conn.exec_driver_sql(f'CREATE TRIGGER injected_failure BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION reject_test_audit()')


def remove_failure(engine,table):
    with engine.begin() as conn:
        conn.exec_driver_sql(f'DROP TRIGGER IF EXISTS injected_failure ON {table}')
        conn.exec_driver_sql('DROP FUNCTION IF EXISTS reject_test_audit()')


@pytest.mark.parametrize('operation,data,table,key',[
    ('assign_role',{'user_id':9,'role_id':3},UserRole,(9,3)),
    ('map_permission',{'role_id':5,'permission_id':5},RolePermission,(5,5)),
    ('revoke_role',{'user_id':7,'role_id':3},UserRole,(7,3)),
    ('unmap_permission',{'role_id':3,'permission_id':5},RolePermission,(3,5))])
def test_policy_audit_failure_rolls_back(pg_engine,db,operation,data,table,key):
    install_failure(pg_engine,'policy_change')
    try:
        with pytest.raises(DBAPIError): mutate(db,1,operation,data);db.commit()
        db.rollback()
        if operation=='revoke_role': assert db.get(table,key).active
        elif operation=='unmap_permission': assert db.get(table,key) is not None
        else: assert db.get(table,key) is None
    finally:
        db.rollback()
        remove_failure(pg_engine,'policy_change')


def test_audit_insert_failure_never_returns_allowed(pg_engine,client,sign_in,db):
    _,csrf=sign_in('analyst@example.com');rid=str(uuid4())
    install_failure(pg_engine,'audit_event')
    try:
        response=client.post('/api/access',json={'action':'READ','resource_id':1,'request_id':rid},headers={'X-CSRF-Token':csrf})
        assert response.status_code==503 and 'ALLOWED' not in response.text
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.request_id==UUID(rid)))==0
    finally:
        db.rollback()
        remove_failure(pg_engine,'audit_event')


def test_existing_inactive_session_evaluation_denied(client,sign_in,db):
    _,csrf=sign_in('analyst@example.com')
    db.get(User,7).active=False;db.commit()
    response=client.post('/api/access',json={'action':'READ','resource_id':1,'request_id':str(uuid4())},headers={'X-CSRF-Token':csrf})
    assert response.status_code==200 and response.json()['reason_code']=='INACTIVE_ACCOUNT'
    assert client.get('/api/resources').status_code==401


def test_audit_filters_and_personal_scope(client,sign_in,db):
    sign_in('auditor@example.com')
    today=datetime.now(timezone.utc).date()
    response=client.get('/api/audit',params={'actor':7,'action':'READ','decision':'ALLOWED','resource':'R42','start':str(today-timedelta(days=25)),'end':str(today)})
    assert response.status_code==200 and 'analyst@example.com' in response.text
    assert response.json()['items']
    assert client.get('/api/audit?q=%27%20OR%201%3D1%20--').status_code==200
    assert client.get('/api/audit?q=%27%20OR%201%3D1%20--').json()['items']==[]
    client.cookies.clear();sign_in('viewer@example.com')
    response=client.get('/api/history?actor=7')
    assert response.json()['items']==[]
    other=db.scalar(select(AuditEvent).where(AuditEvent.actor_user_id==7))
    assert client.get(f'/api/events/{other.id}').status_code==403


def test_csv_filtered_export_and_restrictions(client,sign_in):
    sign_in('auditor@example.com');today=datetime.now(timezone.utc).date()
    params={'start':str(today-timedelta(days=25)),'end':str(today),'actor':7,'decision':'ALLOWED','resource':'R42'}
    response=client.get('/api/audit/export',params=params)
    assert response.status_code==200 and response.headers['content-type'].startswith('text/csv')
    rows=list(csv.DictReader(io.StringIO(response.text)))
    assert rows and all(r['actor_email']=='analyst@example.com' and r['decision']=='ALLOWED' and r['resource_key']=='R42' for r in rows)
    assert 'password_hash' not in response.text and 'token_hash' not in response.text
    assert client.get('/api/audit/export').status_code==422
    assert client.get('/api/audit/export?start=2020-01-01&end=2030-01-01').status_code==422
    client.cookies.clear();sign_in('analyst@example.com')
    assert client.get('/api/audit/export',params=params).status_code==403


def test_export_row_cap(client,sign_in,pg_engine):
    sign_in('auditor@example.com')
    with pg_engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO audit_event(id,actor_user_id,actor_email,action,resource_id,resource_type,resource_key,decision,reason_code,request_id) SELECT gen_random_uuid(),7,'analyst@example.com','DELETE',1,'report','R42','DENIED','NO_MATCHING_PERMISSION',gen_random_uuid() FROM generate_series(1,5001)")
    today=str(datetime.now(timezone.utc).date())
    assert client.get('/api/audit/export',params={'start':today,'end':today}).status_code==422


@pytest.mark.parametrize('value', ['=HYPERLINK("bad")','+1','-2','@formula','   =3','\t=4','\r5'])
def test_csv_formula_safety(value):
    assert csv_cell(value).startswith("'")


@pytest.mark.parametrize('path', ['/api/audit?start=invalid','/api/audit?start=2026-11-21&end=2026-11-20','/api/audit?sort=DROP%20TABLE','/api/audit?action=EXECUTE','/api/audit?decision=UNKNOWN','/api/audit?actor=bad','/api/audit?page=0','/api/users?sort=bad','/api/resources?sort=bad','/api/assignments?page=no'])
def test_invalid_filter_input(client,sign_in,path):
    sign_in()
    assert client.get(path).status_code==422


def test_admin_workflow(client,sign_in,db):
    _,csrf=sign_in()
    def post(operation,values):
        data=dict(values)
        paths={'create_user':'/users','create_role':'/roles','create_permission':'/permissions','map_permission':'/mappings','assign_role':'/assignments','create_resource':'/resources'}
        method='POST'
        if operation in ('user_status','role_status','resource_status'):
            collection={'user_status':'users','role_status':'roles','resource_status':'resources'}[operation]
            path=f"/{collection}/{data.pop('id')}/status";method='PATCH';data['active']=data['active']=='true'
        elif operation=='update_role': path=f"/roles/{data.pop('id')}";method='PUT'
        elif operation=='unmap_permission': path=f"/mappings/{data['role_id']}/{data['permission_id']}";method='DELETE';data=None
        elif operation=='revoke_role': path=f"/assignments/{data['user_id']}/{data['role_id']}";method='DELETE';data=None
        else: path=paths[operation]
        response=client.request(method,'/api'+path,json=data,headers={'X-CSRF-Token':csrf})
        assert response.status_code in (200,201),response.text
    post('create_user',{'name':'Taylor Reed','email':'taylor@example.com','password':'SecurePassword123!'})
    new=db.scalar(select(User).where(User.email=='taylor@example.com'))
    assert verify_password('SecurePassword123!',new.password_hash)
    post('create_role',{'name':'Support Reader','description':'Read support documents'})
    role=db.scalar(select(Role).where(Role.name=='Support Reader'))
    post('update_role',{'id':role.id,'name':'Support Reviewer','description':'Updated description'})
    post('create_permission',{'action':'READ','resource_type':'dataset'})
    perm=db.scalar(select(Permission).where(Permission.resource_type=='dataset'))
    post('map_permission',{'role_id':role.id,'permission_id':perm.id})
    post('assign_role',{'user_id':new.id,'role_id':role.id})
    post('create_resource',{'name':'Support dataset','resource_type':'dataset','resource_key':'S01','owner_user_id':new.id})
    resource=db.scalar(select(Resource).where(Resource.resource_key=='S01'))
    assert evaluate(db,new.id,'READ',resource.id,uuid4()).decision=='ALLOWED';db.commit()
    post('resource_status',{'id':resource.id,'active':'false'})
    assert evaluate(db,new.id,'READ',resource.id,uuid4()).reason_code=='INACTIVE_RESOURCE';db.commit()
    post('unmap_permission',{'role_id':role.id,'permission_id':perm.id})
    post('revoke_role',{'user_id':new.id,'role_id':role.id})
    post('role_status',{'id':role.id,'active':'false'})
    post('user_status',{'id':new.id,'active':'false'})
    db.expire_all()
    assert not db.get(User,new.id).active
    assert 'SecurePassword123!' not in str(list(db.scalars(select(PolicyChange.details))))


def test_input_validation_and_safe_duplicate_errors(client,sign_in):
    _,csrf=sign_in();headers={'X-CSRF-Token':csrf}
    invalid=client.post('/api/users',headers=headers,json={'name':'A','email':'not-email','password':'short'})
    assert invalid.status_code==422 and 'password' in [e['field'] for e in invalid.json()['errors']]
    duplicate=client.post('/api/users',headers=headers,json={'name':'Duplicate','email':'ADMIN@example.com','password':'StrongPassword123!'})
    assert duplicate.status_code==409 and 'password_hash' not in duplicate.text
    assert client.post('/api/resources',headers=headers,json={'name':'Resource','resource_key':'X','resource_type':"x';DROP TABLE role;--",'owner_user_id':7}).status_code==422
    assert client.post('/api/access',json={'action':'EXECUTE','resource_id':1,'request_id':'invalid'},headers=headers).status_code==422
    assert client.get('/api/users?q=%25').json()['items']==[]


def test_runtime_role_cannot_modify_history_or_schema(pg_engine):
    with pg_engine.connect() as conn:
        for statement in ['UPDATE audit_event SET reason_code=reason_code','DELETE FROM policy_change','DELETE FROM security_event','CREATE TABLE unauthorized_test(id int)','SELECT * FROM alembic_version']:
            conn.exec_driver_sql('SET LOCAL ROLE dac_app')
            with pytest.raises(DBAPIError): conn.exec_driver_sql(statement)
            conn.rollback()
        conn.exec_driver_sql('SET LOCAL ROLE dac_app')
        assert conn.exec_driver_sql('SELECT count(*) FROM audit_event').scalar()==180
        conn.rollback()


def test_model_migration_and_sql_demonstrations(pg_engine):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.database import Base
    with pg_engine.connect() as conn:
        diffs=compare_metadata(MigrationContext.configure(conn),Base.metadata)
        assert diffs==[]
        conn.exec_driver_sql(Path('sql/queries.sql').read_text())
        conn.exec_driver_sql(Path('sql/indexes.sql').read_text())
        conn.exec_driver_sql(Path('sql/constraints.sql').read_text())
        conn.exec_driver_sql(Path('sql/transactions.sql').read_text())
        conn.commit()
        assert conn.exec_driver_sql('SELECT count(*) FROM effective_user_permission').scalar()>0
        assert conn.exec_driver_sql('SELECT count(*) FROM daily_access_summary').scalar()>0


def test_historical_role_name_survives_rename(db):
    event=evaluate(db,7,'READ',1,uuid4());db.commit()
    mutate(db,1,'update_role',{'id':3,'name':'Reporting Reader','description':'Renamed role'});db.commit()
    db.expire_all()
    assert db.get(AuditEvent,event.id).matching_role_name=='Report Analyst'
    assert evaluate(db,7,'READ',1,uuid4()).matching_role_name=='Reporting Reader'


def test_standalone_schema_seed_views(pg_engine):
    # An empty independent schema validates the standalone SQL distribution.
    with pg_engine.connect() as conn:
        conn.exec_driver_sql('CREATE SCHEMA standalone_demo')
        conn.exec_driver_sql('SET search_path TO standalone_demo')
        conn.commit()
        try:
            for name in ['schema.sql','seed.sql','views.sql']:
                conn.exec_driver_sql(Path('sql',name).read_text());conn.commit()
            assert conn.exec_driver_sql('SELECT count(*) FROM app_user').scalar()==10
            assert conn.exec_driver_sql('SELECT count(*) FROM audit_event').scalar()==180
            assert conn.exec_driver_sql('SELECT version_num FROM alembic_version').scalar()=='0001'
            assert conn.exec_driver_sql('SELECT count(*) FROM effective_user_permission').scalar()>0
            conn.rollback()
        finally:
            conn.exec_driver_sql('SET search_path TO public')
            conn.exec_driver_sql('DROP SCHEMA standalone_demo CASCADE')
            conn.commit()


def test_selection_bounds_and_cors(client,sign_in,pg_engine):
    _,csrf=sign_in()
    with pg_engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO role(name,description,kind) SELECT 'Selection '||g,'Options test','user' FROM generate_series(1,60) g")
    options=client.get('/api/options/roles').json()
    assert len(options['items'])==50 and options['has_more']
    filtered=client.get('/api/options/roles?q=Selection%2060').json()
    assert len(filtered['items'])==1
    assert client.get('/api/users?status=unsupported').status_code==422
    assert client.get('/api/users?page=100001').status_code==422
    assert client.patch('/api/users/7/status',json={'active':'false'},headers={'X-CSRF-Token':csrf}).status_code==422
    cors=client.options('/api/users',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in cors.headers


def test_public_api_contract_and_spa(client):
    schema=client.get('/api/openapi.json')
    assert schema.status_code==200
    assert '/api/users' in schema.json()['paths'] and '/api/access' in schema.json()['paths']
    assert client.get('/api/nonexistent').status_code==404
    # Built frontend is intentionally public; its protected data endpoints require sessions.
    response=client.get('/users')
    if response.status_code==200: assert 'id="root"' in response.text
    else: assert response.status_code==503  # API-only development checkout before npm build.
