import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone
from fastapi import Request, HTTPException
from app.config import settings
from app.models import LoginSession, User
from app.services.policy import category

COOKIE = 'dac_session'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_signature(value):
    return hmac.new(settings().secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def login_csrf():
    value = f'{int(time.time())}.{secrets.token_hex(24)}'
    return f'{value}.{csrf_signature(value)}'


def valid_login_csrf(value):
    try:
        stamp, nonce, sig = value.split('.')
        return 0 <= time.time() - int(stamp) < 3600 and hmac.compare_digest(csrf_signature(f'{stamp}.{nonce}'), sig)
    except (ValueError, AttributeError):
        return False


def identity(request: Request, db, allow_inactive=False):
    token = request.cookies.get(COOKIE, '')
    session = db.get(LoginSession, digest(token)) if token else None
    now = datetime.now(timezone.utc)
    if not session or session.expires_at <= now:
        raise HTTPException(401, 'Your session has expired. Please sign in again.')
    user = db.get(User, session.user_id)
    if not user or (not user.active and not allow_inactive):
        raise HTTPException(401, 'Your account is inactive. Contact an administrator.')
    return user, session


def csrf_check(form, session):
    token = form.get('csrf_token', '')
    if not isinstance(token, str) or not hmac.compare_digest(token, session.csrf_token):
        raise HTTPException(403, 'This form has expired. Refresh the page and try again.')


def authorize_category(db, user, allowed):
    kind = category(db, user.id)
    if kind not in allowed:
        raise HTTPException(403, 'Your current role does not have access to this page.')
    return kind
