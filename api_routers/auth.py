from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from jose import JWTError, jwt
from api_routers.shared import (
    bootstrap, logger, ApiResponse, LoginRequest, LoginResponse,
    filter_fields, verify_password, get_password_hash,
    create_access_token, create_refresh_token, get_current_user, rate_limiter,
    _generate_jti, _generate_family_id, _create_user_session,
    _revoke_session_by_jti, _revoke_all_user_sessions, _hash_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM,
)
from api_routers.shared.auth_deps import require_permission
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="/api/auth", tags=["auth"])

_ROLE_DISPLAY = {
    "admin": "مدير النظام",
    "accountant": "محاسب",
    "auditor": "مدقق",
    "financial_analyst": "محلل مالي",
    "user": "مستخدم",
}


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, rate_limit: None = Depends(rate_limiter(10, 60))):
    with bootstrap.uow() as uow:
        user_repo = uow.users
        user = user_repo.get_by_username(request.username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة المرور غير صحيحة",
            )

        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة المرور غير صحيحة",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="الحساب معطل",
            )

        token_data = {
            "sub": str(user.id.value),
            "username": user.username,
            "roles": [r.name for r in user.roles],
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Create session - extract JTI from the refresh token JWT
        refresh_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = refresh_payload.get("jti", _generate_jti())
        family_id = _generate_family_id()
        _create_user_session(
            uow=uow,
            user_id=str(user.id.value),
            refresh_token=refresh_token,
            jti=jti,
            family_id=family_id,
            generation=1,
        )

        user.last_login = datetime.now(timezone.utc)
        user_repo.save(user)
        uow.commit()

        # ✅ حساب الصلاحيات: المدير العام (super_admin) يحصل على كل الصلاحيات
        from core.application.security.authorization import Permission, get_user_permissions_from_db
        if getattr(user, 'is_super_admin', False):
            permission_codes = sorted(p.value for p in Permission)
        else:
            permission_codes = sorted(get_user_permissions_from_db(str(user.id.value), uow))

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": str(user.id.value),
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles],
                "permissions": permission_codes,
                "is_super_admin": bool(getattr(user, 'is_super_admin', False)),
            }
        )


@router.post("/refresh")
async def refresh_token(request: dict, rate_limit: None = Depends(rate_limiter(10, 60))):
    try:
        data = filter_fields(request, ["token", "refresh_token"])
        token = data.get("token") or data.get("refresh_token")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        # Decode the refresh token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user_id = payload.get("sub")
        username = payload.get("username")
        roles = payload.get("roles", [])
        jti = payload.get("jti")

        with bootstrap.uow() as uow:
            from sqlalchemy import text

            # Find the session by JTI
            session = uow.session.execute(
                text("SELECT * FROM user_sessions WHERE jti = :jti"),
                {"jti": jti}
            ).fetchone()

            if not session:
                raise HTTPException(status_code=401, detail="Session not found")

            # Check if session is revoked (reuse detection)
            if session.revoked_at is not None:
                # Token reuse detected! Revoke ALL sessions for this user
                _revoke_all_user_sessions(uow, user_id, reason="token_reuse_detected")
                uow.commit()
                logger.warning(f"Token reuse detected for user {user_id}. All sessions revoked.")
                raise HTTPException(status_code=401, detail="Token reuse detected. All sessions revoked.")

            # Check if session is expired
            if session.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Refresh token expired")

            # Revoke the current session (rotation)
            _revoke_session_by_jti(uow, jti, reason="rotated")

            # Create new tokens
            token_data = {
                "sub": user_id,
                "username": username,
                "roles": roles,
            }
            new_access_token = create_access_token(token_data)
            new_refresh_token = create_refresh_token(token_data)
            # Extract JTI from the new refresh token JWT
            new_refresh_payload = jwt.decode(new_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            new_jti = new_refresh_payload.get("jti", _generate_jti())

            # Create new session with incremented generation
            _create_user_session(
                uow=uow,
                user_id=user_id,
                refresh_token=new_refresh_token,
                jti=new_jti,
                family_id=session.family_id,
                generation=session.generation + 1,
            )

            uow.commit()

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(request: dict = None, current_user: dict = Depends(get_current_user)):
    """Logout: revoke the current session if refresh token is provided, otherwise revoke all sessions."""
    try:
        with bootstrap.uow() as uow:
            if request and isinstance(request, dict):
                refresh_token = request.get("token")
                if refresh_token:
                    # Revoke specific session
                    token_hash = _hash_token(refresh_token)
                    from sqlalchemy import text
                    uow.session.execute(
                        text("UPDATE user_sessions SET revoked_at = :now, revoked_reason = 'logout' WHERE refresh_token_hash = :hash"),
                        {"now": datetime.now(timezone.utc), "hash": token_hash}
                    )
                else:
                    # Revoke all user sessions
                    _revoke_all_user_sessions(uow, current_user["id"], reason="logout")
            else:
                # Revoke all user sessions
                _revoke_all_user_sessions(uow, current_user["id"], reason="logout")

            uow.commit()
            return {"message": "تم تسجيل الخروج بنجاح"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"message": "تم تسجيل الخروج بنجاح"}


@router.post("/change-password")
async def change_password(request: dict, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(10, 60))):
    data = filter_fields(request, ["old_password", "new_password"])
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="كلمة المرور القديمة والجديدة مطلوبتان")

    if len(new_password) < 10:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 10 أحرف على الأقل")

    with bootstrap.uow() as uow:
        user_repo = uow.users
        user = user_repo.get_by_id(current_user["id"])

        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")

        user.password_hash = get_password_hash(new_password)
        user.updated_by = current_user["username"]
        user_repo.save(user)
        uow.commit()

        return {"message": "تم تغيير كلمة المرور بنجاح"}


@router.get("/users", response_model=ApiResponse)
async def list_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_users"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية إدارة المستخدمين")
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            rows = uow.session.execute(sa_text(
                "SELECT u.id::text, u.username, u.email, u.full_name, u.is_active, "
                "r.name AS role, r.display_name AS role_display "
                "FROM users u "
                "LEFT JOIN LATERAL (SELECT r2.name, r2.display_name FROM user_roles ur "
                "  JOIN roles r2 ON r2.id = ur.role_id WHERE ur.user_id = u.id ORDER BY r2.name LIMIT 1) r ON TRUE "
                "ORDER BY u.username LIMIT :lim OFFSET :off"
            ), {"lim": limit, "off": offset}).mappings().all()

            count = uow.session.execute(sa_text("SELECT COUNT(*) FROM users")).scalar() or 0
            result = []
            for r in rows:
                names = (r["full_name"] or "").strip().split(" ", 1)
                role = r["role"] or "user"
                result.append({
                    'id': r["id"],
                    'username': r["username"],
                    'email': r["email"] or "",
                    'first_name': names[0] if names else "",
                    'last_name': names[1] if len(names) > 1 else "",
                    'role': role,
                    'role_name': r["role_display"] or _ROLE_DISPLAY.get(role, role),
                    'is_active': r["is_active"],
                })
            return ApiResponse(success=True, message="تم جلب المستخدمين بنجاح",
                               data={'items': result, 'total': count})
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/users", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_user(request: dict, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(100, 60))):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_users"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية إدارة المستخدمين")
    try:
        data = filter_fields(request, [
            "username", "email", "first_name", "last_name", "password", "role", "is_active",
        ])
        if not data.get("username"):
            raise HTTPException(status_code=400, detail="username مطلوب")
        if not data.get("password") or len(data["password"]) < 10:
            raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 10 أحرف على الأقل")

        # Prevent privilege escalation: non-admins cannot create admin users
        requested_role = data.get("role", "user")
        if requested_role == "admin" and not (_ctx and _ctx.is_super_admin):
            raise HTTPException(status_code=403, detail="لا يمكنك إنشاء مستخدمين بأدوار إدارية")

        with bootstrap.uow() as uow:
            user_repo = uow.users
            from core.domain.auth.entities import User
            from core.domain.auth.value_objects import UserId
            existing = user_repo.get_by_username(data['username'])
            if existing:
                raise HTTPException(status_code=409, detail="اسم المستخدم موجود مسبقاً")
            new_user = User(
                id=UserId.generate(),
                username=data['username'],
                email=data.get('email') or f"{data['username']}@placeholder.local",
                full_name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                password_hash=get_password_hash(data.get('password', '')),
                is_active=bool(data.get('is_active', True)),
                is_super_admin=False,
                created_by=current_user["username"],
                updated_by=current_user["username"],
            )
            user_repo.save(new_user)
            uow.commit()
            # تعيين الدور إذا تم إرساله
            role = data.get('role')
            if role:
                try:
                    from sqlalchemy import text as sa_text
                    allowed_roles = ["admin", "accountant", "auditor", "financial_analyst", "user"]
                    if role not in allowed_roles:
                        role = "user"
                    role_row = uow.session.execute(sa_text(
                        "SELECT id FROM roles WHERE name = :name AND is_active = TRUE"
                    ), {"name": role}).first()
                    if role_row:
                        uow.session.execute(sa_text(
                            "INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"
                        ), {"uid": str(new_user.id.value), "rid": str(role_row[0])})
                        uow.commit()
                except Exception as role_e:
                    logger.error(f"Error assigning role to user {data.get('username')}: {role_e}")
            return ApiResponse(success=True, message="تم إنشاء المستخدم بنجاح",
                               data={'id': str(new_user.id.value), 'username': new_user.username})
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/users/{user_id}", response_model=ApiResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_users"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية إدارة المستخدمين")
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            row = uow.session.execute(sa_text(
                "SELECT u.id::text, u.username, u.email, u.full_name, u.is_active, "
                "r.name AS role, r.display_name AS role_display "
                "FROM users u "
                "LEFT JOIN LATERAL (SELECT r2.name, r2.display_name FROM user_roles ur "
                "  JOIN roles r2 ON r2.id = ur.role_id WHERE ur.user_id = u.id ORDER BY r2.name LIMIT 1) r ON TRUE "
                "WHERE u.id::text = :uid"
            ), {"uid": user_id}).mappings().first()
            if not row:
                return ApiResponse(success=False, message="المستخدم غير موجود")
            names = (row["full_name"] or "").strip().split(" ", 1)
            role = row["role"] or "user"
            data = {
                'id': row["id"],
                'username': row["username"],
                'email': row["email"] or "",
                'first_name': names[0] if names else "",
                'last_name': names[1] if len(names) > 1 else "",
                'role': role,
                'role_name': row["role_display"] or _ROLE_DISPLAY.get(role, role),
                'is_active': row["is_active"],
            }
            return ApiResponse(success=True, message="تم جلب المستخدم بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/users/{user_id}", response_model=ApiResponse)
async def update_user(user_id: str, request: dict, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(100, 60))):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_users"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية إدارة المستخدمين")
    try:
        data = filter_fields(request, [
            "username", "email", "first_name", "last_name", "password", "role", "is_active",
        ])

        # Prevent privilege escalation: non-admins cannot assign admin role
        requested_role = data.get("role")
        if requested_role == "admin":
            if not (_ctx and _ctx.is_super_admin):
                raise HTTPException(status_code=403, detail="لا يمكنك تعيين دور إداري")

        # Prevent self-deactivation
        if str(user_id) == str(current_user["id"]) and data.get("is_active") == False:
            raise HTTPException(status_code=400, detail="لا يمكنك تعطيل حسابك الخاص")

        with bootstrap.uow() as uow:
            user_repo = uow.users
            from core.domain.auth.value_objects import UserId as _UserId
            user = user_repo.get_by_id(_UserId.from_string(user_id))
            if not user:
                return ApiResponse(success=False, message="المستخدم غير موجود")
            uid = user.id.value if hasattr(user.id, 'value') else str(user.id)
            if 'username' in data:
                user.username = data['username']
            if 'email' in data and data['email']:
                user.email = data['email']
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'is_active' in data:
                user.is_active = bool(data['is_active'])
            if 'password' in data and data['password']:
                user.password_hash = get_password_hash(data['password'])
            user.updated_by = current_user["username"]
            user_repo.save(user)
            # تحديث الدور إذا تم إرساله
            if 'role' in data and data['role']:
                from sqlalchemy import text as sa_text
                role_row = uow.session.execute(sa_text(
                    "SELECT id FROM roles WHERE name = :name AND is_active = TRUE"
                ), {"name": data['role']}).first()
                if role_row:
                    uow.session.execute(sa_text(
                        "DELETE FROM user_roles WHERE user_id = :uid"
                    ), {"uid": uid})
                    uow.session.execute(sa_text(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"
                    ), {"uid": uid, "rid": str(role_row[0])})
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المستخدم بنجاح")
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(100, 60))):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_users"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية إدارة المستخدمين")
    try:
        # Prevent self-deletion
        if str(user_id) == str(current_user["id"]):
            raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك الخاص")

        with bootstrap.uow() as uow:
            user_repo = uow.users
            from core.domain.auth.value_objects import UserId as _UserId
            user = user_repo.get_by_id(_UserId.from_string(user_id))
            if not user:
                return ApiResponse(success=False, message="المستخدم غير موجود")
            user_repo.delete(_UserId.from_string(user_id))
            uow.commit()
            return ApiResponse(success=True, message="تم حذف المستخدم بنجاح")
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
