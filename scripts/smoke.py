"""Live JSON API smoke check for synthetic data only; creates real history."""
import argparse
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import httpx


def run(base):
    clients=[]
    def login(email):
        c=httpx.Client(base_url=base,timeout=20)
        token=c.get('/api/auth/csrf').json()['csrf_token']
        r=c.post('/api/auth/login',json={'email':email,'password':'AccessDemo!2026#','csrf_token':token});assert r.status_code==200,r.text
        csrf=r.json()['csrf_token'];clients.append((c,csrf));assert c.get('/api/dashboard').status_code==200
        return c,csrf
    def evaluate(c,csrf,action):
        r=c.post('/api/access',headers={'X-CSRF-Token':csrf},json={'action':action,'resource_id':1,'request_id':str(uuid4())})
        assert r.status_code==200,r.text
        return r.json()['decision']
    assert httpx.get(base+'/health').json()=={'status':'ok'}
    admin,csrf=login('admin@example.com')
    for path in ['users','roles','permissions','mappings','assignments','resources','audit','policy','security','auth/session']:
        assert admin.get('/api/'+path).status_code==200,path
    analyst,a=login('analyst@example.com')
    assert evaluate(analyst,a,'READ')=='ALLOWED' and evaluate(analyst,a,'DELETE')=='DENIED'
    viewer,v=login('viewer@example.com');assert evaluate(viewer,v,'READ')=='DENIED'
    assert admin.post('/api/assignments',headers={'X-CSRF-Token':csrf},json={'user_id':9,'role_id':3}).status_code==201
    assert evaluate(viewer,v,'READ')=='ALLOWED'
    assert admin.delete('/api/assignments/9/3',headers={'X-CSRF-Token':csrf}).status_code==200
    assert evaluate(viewer,v,'READ')=='DENIED'
    auditor,u=login('auditor@example.com');assert auditor.get('/api/users').status_code==403
    today=datetime.now(timezone.utc).date()
    exported=auditor.get('/api/audit/export',params={'start':str(today-timedelta(days=25)),'end':str(today),'decision':'DENIED','resource':'R42'})
    assert exported.status_code==200 and 'DENIED' in exported.text
    for c,t in clients:
        assert c.post('/api/auth/logout',headers={'X-CSRF-Token':t}).status_code==200
        assert c.get('/api/auth/session').status_code==401;c.close()
    print('PASS: live health, three role dashboards, administration, allowed/denied decisions, grant/revocation, audit restrictions, filtered CSV and logout.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://localhost:8000')
    run(parser.parse_args().base_url)
