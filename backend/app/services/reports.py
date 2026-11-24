from datetime import date, datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select, or_
from app.models import AuditEvent, PolicyChange


def date_window(params, required=False):
    start, end = params.get('start'), params.get('end')
    if required and (not start or not end):
        raise HTTPException(422, 'Select both a start and end date before exporting.')
    try:
        begin = datetime.combine(date.fromisoformat(start), datetime.min.time(), timezone.utc) if start else None
        finish = datetime.combine(date.fromisoformat(end), datetime.min.time(), timezone.utc) + timedelta(days=1) if end else None
    except (ValueError, OverflowError):
        raise HTTPException(422, 'Use valid dates in YYYY-MM-DD format.')
    if begin and finish and begin >= finish:
        raise HTTPException(422, 'End date must be on or after start date.')
    if required and (finish - begin).days > 93:
        raise HTTPException(422, 'Exports are limited to a 93-day date range.')
    return begin, finish


def audit_query(params, personal_id=None, export=False):
    q = select(AuditEvent)
    if personal_id is not None:
        q = q.where(AuditEvent.actor_user_id == personal_id)
    search = params.get('q', '').strip()[:200]
    if search:
        q = q.where(or_(AuditEvent.actor_email.icontains(search, autoescape=True), AuditEvent.resource_key.icontains(search, autoescape=True)))
    if params.get('actor'):
        try:
            actor = int(params['actor'])
            if actor <= 0: raise ValueError
        except ValueError:
            raise HTTPException(422, 'Choose a valid actor.')
        q = q.where(AuditEvent.actor_user_id == actor)
    if params.get('action'):
        if params['action'] not in ('READ', 'CREATE', 'UPDATE', 'DELETE'):
            raise HTTPException(422, 'Choose a supported action.')
        q = q.where(AuditEvent.action == params['action'])
    if params.get('decision'):
        if params['decision'] not in ('ALLOWED', 'DENIED'):
            raise HTTPException(422, 'Choose an allowed or denied decision.')
        q = q.where(AuditEvent.decision == params['decision'])
    if params.get('resource'):
        q = q.where(AuditEvent.resource_key == params['resource'][:80])
    start, end = date_window(params, required=export)
    if start: q = q.where(AuditEvent.occurred_at >= start)
    if end: q = q.where(AuditEvent.occurred_at < end)
    sorting = {'newest': AuditEvent.occurred_at.desc(), 'oldest': AuditEvent.occurred_at.asc(),
               'actor': AuditEvent.actor_email.asc(), 'action': AuditEvent.action.asc()}
    sort = params.get('sort', 'newest')
    if sort not in sorting: raise HTTPException(422, 'Choose a supported sort order.')
    return q.order_by(sorting[sort], AuditEvent.id)


def policy_query(params):
    q = select(PolicyChange)
    if params.get('q'):
        q = q.where(or_(PolicyChange.actor_email.icontains(params['q'][:200], autoescape=True),
                        PolicyChange.operation.icontains(params['q'][:200], autoescape=True)))
    if params.get('actor'):
        try: actor = int(params['actor'])
        except ValueError: raise HTTPException(422, 'Choose a valid administrator.')
        q = q.where(PolicyChange.actor_user_id == actor)
    start, end = date_window(params)
    if start: q = q.where(PolicyChange.occurred_at >= start)
    if end: q = q.where(PolicyChange.occurred_at < end)
    return q.order_by(PolicyChange.occurred_at.desc(), PolicyChange.id)
