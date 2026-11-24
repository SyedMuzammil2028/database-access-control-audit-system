"""Shared authentication logic for the JSON API, with no browser token storage."""
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy import select, func, or_, text, delete
from app.models import User, SecurityEvent, LoginSession
from app.config import settings
from app.security.passwords import verify_password, DUMMY_HASH
from app.security.sessions import digest, csrf_signature, COOKIE


def authenticate(db, request, email, password):
    email = email.strip().lower()
    ip_hash = csrf_signature(request.client.host if request.client else 'unknown')
    # Both keys are locked in sorted order: limits remain race safe across sources.
    keys = sorted({int(ip_hash[:15],16), int(csrf_signature('email:'+email)[:15],16)})
    for key in keys:
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key':key})
    cutoff = datetime.now(timezone.utc)-timedelta(minutes=15)
    count = db.scalar(select(func.count()).select_from(SecurityEvent).where(
        SecurityEvent.operation=='LOGIN_FAILED', SecurityEvent.occurred_at>=cutoff,
        or_(SecurityEvent.email==email, SecurityEvent.ip_hash==ip_hash)))
    if count >= 10:
        raise HTTPException(429, 'Too many sign-in attempts. Try again in 15 minutes.')
    user = db.scalar(select(User).where(User.email==email))
    valid = verify_password(password, user.password_hash if user else DUMMY_HASH)
    ok = bool(user and user.active and valid)
    db.add(SecurityEvent(actor_user_id=user.id if user else None, email=email,
        ip_hash=ip_hash, operation='LOGIN_SUCCESS' if ok else 'LOGIN_FAILED', request_id=request.state.request_id))
    if not ok:
        db.commit()
        raise HTTPException(400, 'Email or password is incorrect, or your account is inactive.')
    old = request.cookies.get(COOKIE)
    if old: db.execute(delete(LoginSession).where(LoginSession.token_hash==digest(old)))
    token=secrets.token_urlsafe(48)
    session=LoginSession(token_hash=digest(token), user_id=user.id, csrf_token=secrets.token_hex(32),
        expires_at=datetime.now(timezone.utc)+timedelta(hours=settings().session_hours))
    db.add(session); db.commit()
    return user, session, token
