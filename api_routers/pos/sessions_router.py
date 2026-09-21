# api_routers/pos/sessions_router.py
"""
Point of Sale (POS) Sessions - جلسات نقطة البيع
"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.pos.dtos import (
    OpenSessionRequest,
    CloseSessionRequest,
)
from api_routers.pos.pos_service import (
    open_pos_session,
    close_pos_session,
    list_pos_sessions,
    get_pos_session,
    list_terminals,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["pos-sessions"])

PERM = {
    "open": "pos.open_session",
    "close": "pos.close_session",
    "reconcile": "pos.reconcile_cash",
    "view": "pos.view_sales",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


def _actor(current_user: dict) -> str:
    return str(current_user.get("id") or "system")


@router.post("/api/pos/sessions", response_model=ApiResponse)
async def create_session(
    request: OpenSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["open"])
    try:
        with bootstrap.uow() as uow:
            result = open_pos_session(
                uow,
                opening_cash=request.opening_cash,
                terminal_id=request.terminal_id,
                device_id=request.device_id,
                warehouse_id=request.warehouse_id,
                branch_id=request.branch_id,
                notes=request.notes,
                created_by=_actor(current_user),
            )
            uow.commit()
            return ApiResponse(
                success=True,
                message="تم فتح جلسة نقطة البيع بنجاح",
                data=result,
            )
    except Exception as e:
        logger.error(f"Error opening POS session: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/pos/sessions", response_model=ApiResponse)
async def all_sessions(
    status: Optional[str] = Query(None),
    terminal_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            data = list_pos_sessions(
                uow,
                status=status,
                terminal_id=terminal_id,
                skip=skip,
                limit=limit,
            )
            return ApiResponse(success=True, message="تم جلب جلسات نقطة البيع", data=data)
    except Exception as e:
        logger.error(f"Error listing POS sessions: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/pos/sessions/{session_id}", response_model=ApiResponse)
async def session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            data = get_pos_session(uow, session_id)
            return ApiResponse(success=True, message="تم جلب تفاصيل الجلسة", data=data)
    except Exception as e:
        logger.error(f"Error getting POS session: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/pos/sessions/{session_id}/close", response_model=ApiResponse)
async def close_session_endpoint(
    session_id: str,
    request: CloseSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    _ctx = get_current_user_context()
    if request.tolerance > 0:
        _check_perm(PERM["reconcile"])
    else:
        _check_perm(PERM["close"])
    try:
        with bootstrap.uow() as uow:
            result = close_pos_session(
                uow,
                session_id=session_id,
                declared_cash=request.declared_cash,
                tolerance=request.tolerance,
                notes=request.notes,
                created_by=_actor(current_user),
                notify_user_id=(_ctx.user_id if _ctx else None),
            )
            uow.commit()
            if result["mismatch"]:
                message = "تم إغلاق الجلسة مع وجود فرق في الصندوق"
            else:
                message = "تم إغلاق جلسة نقطة البيع بنجاح"
            return ApiResponse(success=True, message=message, data=result)
    except Exception as e:
        logger.error(f"Error closing POS session: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/pos/terminals", response_model=ApiResponse)
async def all_terminals(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            data = list_terminals(uow, status=status, skip=skip, limit=limit)
            return ApiResponse(success=True, message="تم جلب أجهزة نقطة البيع", data=data)
    except Exception as e:
        logger.error(f"Error listing POS terminals: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])