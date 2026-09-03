"""
YAseen ERP - API Authorization Dependencies
FastAPI dependencies for permission and role checking.

IMPORTANT: These must be used AFTER get_current_user in the endpoint signature,
because they rely on the UserContext being set by get_current_user.
"""
from fastapi import HTTPException, Depends

from core.application.security.authorization import get_current_user_context


def require_permission(permission: str):
    """
    FastAPI dependency factory - requires a specific permission.
    The endpoint MUST also have get_current_user as a dependency (listed BEFORE this).
    Usage:
        @router.post("/users")
        async def create_user(..., current_user: dict = Depends(get_current_user), _auth: object = require_permission("settings.manage_users")):
    """
    async def dependency():
        ctx = get_current_user_context()
        if ctx is None:
            raise HTTPException(status_code=401, detail="غير مصرح - يرجى تسجيل الدخول")
        if not ctx.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"ليس لديك صلاحية: {permission}",
            )
        return ctx
    return Depends(dependency)


def require_role(role: str):
    """FastAPI dependency - requires a specific role."""
    async def dependency():
        ctx = get_current_user_context()
        if ctx is None:
            raise HTTPException(status_code=401, detail="غير مصرح - يرجى تسجيل الدخول")
        if not ctx.has_role(role):
            raise HTTPException(
                status_code=403,
                detail=f"ليس لديك الدور المطلوب: {role}",
            )
        return ctx
    return Depends(dependency)


def require_any_role(*roles: str):
    """Require any of the specified roles."""
    async def dependency():
        ctx = get_current_user_context()
        if ctx is None:
            raise HTTPException(status_code=401, detail="غير مصرح - يرجى تسجيل الدخول")
        if not ctx.has_any_role(*roles):
            raise HTTPException(
                status_code=403,
                detail=f"يجب أن يكون لديك أحد الأدوار: {', '.join(roles)}",
            )
        return ctx
    return Depends(dependency)
