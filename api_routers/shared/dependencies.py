"""
YAseen ERP - Shared Dependencies
get_uow, get_current_user, JWT helpers, session helpers
"""
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Depends, status
from jose import JWTError, jwt

from api_routers.shared.config import (
    bootstrap, SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
    pwd_context, oauth2_scheme, logger,
)


def filter_fields(data: dict, allowed_fields: list) -> dict:
    """Filter a dictionary to only include allowed fields. Prevents mass-assignment."""
    return {k: v for k, v in data.items() if k in allowed_fields}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


_ROLE_DISPLAY = {
    "admin": "مدير النظام",
    "accountant": "محاسب",
    "auditor": "مدقق",
    "financial_analyst": "محلل مالي",
    "user": "مستخدم",
}


def _user_primary_role(user) -> str:
    roles = getattr(user, 'roles', None)
    if roles:
        first = roles[0]
        name = first.name if hasattr(first, 'name') else first
        return name or 'user'
    return 'user'


def _user_primary_role_display(user) -> str:
    role = _user_primary_role(user)
    return _ROLE_DISPLAY.get(role, role)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": now,
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": now,
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# Session Management Helpers
# =============================================================================

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_jti() -> str:
    return str(uuid.uuid4())


def _generate_family_id() -> str:
    return str(uuid.uuid4())


def _create_user_session(
    uow, user_id: str, refresh_token: str, jti: str, family_id: str,
    generation: int = 1, ip_address: str = None, user_agent: str = None,
    expires_in_days: int = None,
):
    from core.infrastructure.db.models.auth_models import UserSessionModel
    if expires_in_days is None:
        expires_in_days = REFRESH_TOKEN_EXPIRE_DAYS
    session = UserSessionModel(
        user_id=uuid.UUID(user_id),
        refresh_token_hash=_hash_token(refresh_token),
        jti=jti,
        family_id=family_id,
        generation=generation,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        last_used_at=datetime.now(timezone.utc),
    )
    uow.session.add(session)
    return session


def _revoke_session_by_jti(uow, jti: str, reason: str = "logout"):
    from sqlalchemy import text
    uow.session.execute(
        text("UPDATE user_sessions SET revoked_at = :now, revoked_reason = :reason WHERE jti = :jti"),
        {"now": datetime.now(timezone.utc), "reason": reason, "jti": jti}
    )


def _revoke_all_user_sessions(uow, user_id: str, reason: str = "security"):
    from sqlalchemy import text
    uow.session.execute(
        text("UPDATE user_sessions SET revoked_at = :now, revoked_reason = :reason WHERE user_id = :user_id AND revoked_at IS NULL"),
        {"now": datetime.now(timezone.utc), "reason": reason, "user_id": uuid.UUID(user_id)}
    )


def _is_session_valid(session) -> bool:
    if session.revoked_at is not None:
        return False
    if session.expires_at < datetime.now(timezone.utc):
        return False
    return True


def _detect_token_reuse(uow, refresh_token_hash: str) -> bool:
    from sqlalchemy import text
    result = uow.session.execute(
        text("SELECT revoked_at FROM user_sessions WHERE refresh_token_hash = :hash"),
        {"hash": refresh_token_hash}
    ).fetchone()
    if result and result[0] is not None:
        return True
    return False


# =============================================================================
# FastAPI Dependencies
# =============================================================================

def get_uow():
    try:
        with bootstrap.uow() as uow:
            return uow
    except Exception as e:
        logger.error(f"Error getting UOW: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = verify_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        from core.domain.auth.value_objects import UserId
        try:
            parsed_user_id = UserId.from_string(user_id) if isinstance(user_id, str) else user_id
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        with bootstrap.uow() as uow:
            user_repo = uow.users
            user = user_repo.get_by_id(parsed_user_id)
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            if not user.is_active:
                raise HTTPException(status_code=403, detail="User is inactive")

            jti = payload.get("jti")
            if jti:
                from sqlalchemy import text as _sa_text
                active_sessions = uow.session.execute(
                    _sa_text("SELECT COUNT(*) FROM user_sessions WHERE user_id = :uid AND revoked_at IS NULL AND expires_at > :now"),
                    {"uid": user_id, "now": datetime.now(timezone.utc)}
                ).scalar()
                if active_sessions == 0:
                    raise HTTPException(status_code=401, detail="All sessions revoked")

            user_dict = {
                "id": str(user.id.value),
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles],
                "permissions": sorted({p.code for r in user.roles for p in r.permissions}),
                "is_super_admin": user.is_super_admin,
            }

            from core.application.security.authorization import UserContext, set_current_user_context
            set_current_user_context(UserContext(
                user_id=user_dict["id"],
                username=user_dict["username"],
                roles=set(user_dict["roles"]),
                permissions=set(user_dict["permissions"]),
                is_super_admin=user_dict["is_super_admin"],
            ))

            return user_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
