from fastapi import APIRouter, Query, Depends, status, HTTPException
from typing import Optional
from datetime import date
import uuid

from pydantic import BaseModel

from api_routers.shared import (
    bootstrap, logger, ApiResponse,
    CreateJournalEntryRequest, CreateAccountRequest,
    get_current_user, filter_fields,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["accounting"])


# =============================================================================
# 3. ACCOUNTING - Journal Entries
# =============================================================================

@router.get("/api/journal-entries", response_model=ApiResponse)
async def list_journal_entries(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    is_posted: Optional[bool] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.journal_entries
            entries = repo.list_all(limit=limit, offset=offset)
            
            if is_posted is not None:
                entries = [e for e in entries if e.is_posted == is_posted]
            if from_date:
                entries = [e for e in entries if e.date >= from_date]
            if to_date:
                entries = [e for e in entries if e.date <= to_date]
            
            total = len(entries)
            
            result = []
            for entry in entries:
                result.append({
                    'id': str(entry.id) if hasattr(entry, 'id') else None,
                    'date': entry.date.isoformat() if hasattr(entry, 'date') else None,
                    'description': entry.description if hasattr(entry, 'description') else '',
                    'is_posted': entry.is_posted if hasattr(entry, 'is_posted') else False,
                    'total_debit': float(entry.total_debit) if hasattr(entry, 'total_debit') else 0,
                    'total_credit': float(entry.total_credit) if hasattr(entry, 'total_credit') else 0,
                    'line_count': len(entry.lines) if hasattr(entry, 'lines') else 0,
                    'version': entry.version if hasattr(entry, 'version') else 1,
                })
            
            return ApiResponse(
                success=True,
                message="تم جلب القيود بنجاح",
                data={
                    'items': result,
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total,
                }
            )
    except Exception as e:
        logger.error(f"Error listing journal entries: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/journal-entries/{entry_id}", response_model=ApiResponse)
async def get_journal_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            repo = uow.journal_entries
            entry = repo.get_by_id(entry_id)
            
            if not entry:
                return ApiResponse(success=False, message="القيد غير موجود")
            
            result = {
                'id': str(entry.id),
                'date': entry.date.isoformat(),
                'description': entry.description,
                'is_posted': entry.is_posted,
                'total_debit': float(entry.total_debit),
                'total_credit': float(entry.total_credit),
                'lines': [
                    {
                        'line_id': str(line.line_id),
                        'account_code': str(line.account_code),
                        'account_name': line.account_name if hasattr(line, 'account_name') else '',
                        'debit': float(line.debit.amount),
                        'credit': float(line.credit.amount),
                        'description': line.description if hasattr(line, 'description') else '',
                    }
                    for line in entry.lines
                ],
                'notes': entry.notes if hasattr(entry, 'notes') else None,
                'version': entry.version,
                'created_at': entry.created_at.isoformat() if hasattr(entry, 'created_at') else None,
                'created_by': entry.created_by if hasattr(entry, 'created_by') else None,
            }
            
            return ApiResponse(success=True, message="تم جلب القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error getting journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/journal-entries", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(request: CreateJournalEntryRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.create_entry"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.application.accounting.commands import CreateJournalEntryCommand
        
        command = CreateJournalEntryCommand(
            date=request.date,
            description=request.description,
            lines=[
                {
                    "account_code": line.account_code,
                    "debit": line.debit,
                    "credit": line.credit,
                    "description": line.description,
                    "currency": line.currency,
                    "cost_center": line.cost_center,
                    "profit_center": line.profit_center,
                }
                for line in request.lines
            ],
            transaction_type=request.transaction_type,
            reference_id=request.reference_id,
            notes=request.notes,
            created_by=current_user["username"],
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم إنشاء القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error creating journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/journal-entries/{entry_id}/post", response_model=ApiResponse)
async def post_journal_entry(entry_id: str, force: bool = Query(False), current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.post_entry"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        from core.application.accounting.commands import PostJournalEntryCommand
        
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT entry_date FROM journal_entries WHERE id::text = :eid"),
                {"eid": entry_id}
            ).mappings().first()
            if row is None:
                return ApiResponse(success=False, message="القيد غير موجود", errors=["entry not found"])
            entry_date = row["entry_date"]
            if entry_date is not None:
                entry_date = entry_date.date() if hasattr(entry_date, "date") else entry_date
            else:
                entry_date = date.today()
            closed = uow.session.execute(
                text("SELECT is_closed FROM fiscal_periods "
                     "WHERE start_date <= :d AND end_date >= :d AND is_closed = TRUE LIMIT 1"),
                {"d": entry_date}
            ).scalar()
            if closed:
                is_admin = bool(
                    current_user.get("is_super_admin")
                    or any(r in current_user.get("roles", []) for r in ("admin", "super_admin"))
                )
                if not force or not is_admin:
                    return ApiResponse(success=False, message="لا يمكن الترحيل في فترة مالية مقفلة")
        
        command = PostJournalEntryCommand(
            entry_id=entry_id,
            posted_by=current_user["username"],
            force=force,
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم ترحيل القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error posting journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/journal-entries/{entry_id}/reverse", response_model=ApiResponse)
async def reverse_journal_entry(entry_id: str, reason: str = Query(...), current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.reverse_entry"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.application.accounting.commands import ReverseJournalEntryCommand
        
        command = ReverseJournalEntryCommand(
            entry_id=entry_id,
            reason=reason,
            reversed_by=current_user["username"],
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم عكس القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error reversing journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/journal-entries/{entry_id}", response_model=ApiResponse)
async def update_journal_entry(
    entry_id: str, 
    request: CreateJournalEntryRequest, 
    current_user: dict = Depends(get_current_user)
):
    """تحديث قيد محاسبي في حالة المسودة."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.edit_entry"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        from decimal import Decimal
        
        with bootstrap.uow() as uow:
            # التحقق من وجود القيد وأنه في حالة مسودة
            row = uow.session.execute(
                text("SELECT is_posted FROM journal_entries WHERE id::text = :eid"),
                {"eid": entry_id}
            ).mappings().first()
            
            if row is None:
                return ApiResponse(success=False, message="القيد غير موجود")
            
            if row["is_posted"]:
                return ApiResponse(success=False, message="لا يمكن تعديل قيد مرحل. يجب عكسه أولاً")
            
            # حذف الأسطر القديمة
            uow.session.execute(
                text("DELETE FROM journal_lines WHERE journal_entry_id::text = :eid"),
                {"eid": entry_id}
            )
            
            # تحديث البيانات الأساسية
            uow.session.execute(
                text("""
                    UPDATE journal_entries 
                    SET description = :desc, entry_date = :date, updated_at = NOW()
                    WHERE id::text = :eid
                """),
                {"desc": request.description, "date": request.date, "eid": entry_id}
            )
            
            # إضافة الأسطر الجديدة
            for idx, line in enumerate(request.lines):
                line_id = uuid.uuid4()
                debit_amount = Decimal(str(line.debit)) if line.debit else Decimal('0')
                credit_amount = Decimal(str(line.credit)) if line.credit else Decimal('0')
                
                # الحصول على معرف الحساب
                acct_row = uow.session.execute(
                    text("SELECT id FROM accounts WHERE code = :code"),
                    {"code": line.account_code}
                ).mappings().first()
                
                if not acct_row:
                    return ApiResponse(success=False, message=f"الحساب {line.account_code} غير موجود")
                
                uow.session.execute(
                    text("""
                        INSERT INTO journal_lines 
                        (id, journal_entry_id, account_id, debit_amount, credit_amount, 
                         line_order, currency, cost_center_id, profit_center_id, description)
                        VALUES 
                        (:id, :eid, :aid, :debit, :credit, :order, :currency, :cc, :pc, :desc)
                    """),
                    {
                        "id": line_id,
                        "eid": entry_id,
                        "aid": acct_row["id"],
                        "debit": debit_amount,
                        "credit": credit_amount,
                        "order": idx,
                        "currency": line.currency or "USD",
                        "cc": None,  # يمكن إضافة دعم مراكز التكلفة لاحقاً
                        "pc": None,
                        "desc": line.description or ""
                    }
                )
            
            uow.commit()
            
            return ApiResponse(
                success=True, 
                message="تم تحديث القيد بنجاح",
                data={"id": entry_id}
            )
    except Exception as e:
        logger.error(f"Error updating journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/journal-entries/{entry_id}", response_model=ApiResponse)
async def delete_journal_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    """حذف قيد محاسبي في حالة المسودة فقط."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.delete_entry"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        
        with bootstrap.uow() as uow:
            # التحقق من وجود القيد وأنه في حالة مسودة
            row = uow.session.execute(
                text("SELECT is_posted FROM journal_entries WHERE id::text = :eid"),
                {"eid": entry_id}
            ).mappings().first()
            
            if row is None:
                return ApiResponse(success=False, message="القيد غير موجود")
            
            if row["is_posted"]:
                return ApiResponse(
                    success=False, 
                    message="لا يمكن حذف قيد مرحل. يجب عكسه أولاً"
                )
            
            # حذف الأسطر أولاً
            uow.session.execute(
                text("DELETE FROM journal_lines WHERE journal_entry_id::text = :eid"),
                {"eid": entry_id}
            )
            
            # حذف القيد
            uow.session.execute(
                text("DELETE FROM journal_entries WHERE id::text = :eid"),
                {"eid": entry_id}
            )
            
            uow.commit()
            
            return ApiResponse(
                success=True, 
                message="تم حذف القيد بنجاح"
            )
    except Exception as e:
        logger.error(f"Error deleting journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 4. ACCOUNTING - Accounts
# =============================================================================

@router.get("/api/accounts", response_model=ApiResponse)
async def list_accounts(
    account_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.accounts
            accounts = repo.get_all_accounts(account_type=account_type, include_inactive=include_inactive)
            
            result = []
            for acc in accounts:
                result.append({
                    'code': str(acc.code) if hasattr(acc, 'code') else '',
                    'name': acc.name if hasattr(acc, 'name') else '',
                    'account_type': acc.account_type if hasattr(acc, 'account_type') else '',
                    'is_active': acc.is_active if hasattr(acc, 'is_active') else True,
                    'currency': acc.currency if hasattr(acc, 'currency') else 'USD',
                    'parent_code': str(acc.parent_code) if hasattr(acc, 'parent_code') and acc.parent_code else None,
                    'description': acc.description if hasattr(acc, 'description') else None,
                })
            
            return ApiResponse(success=True, message="تم جلب الحسابات بنجاح", data={'accounts': result})
    except Exception as e:
        logger.error(f"Error listing accounts: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/accounts", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_account(request: CreateAccountRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_settings"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.application.accounts.commands import CreateAccountCommand
        
        command = CreateAccountCommand(
            code=request.code,
            name=request.name,
            account_type=request.account_type,
            parent_code=request.parent_code,
            description=request.description,
            currency=request.currency,
            is_active=request.is_active,
            created_by=current_user["username"],
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم إنشاء الحساب بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error creating account: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/accounts/{account_code}", response_model=ApiResponse)
async def update_account(
    account_code: str,
    request: CreateAccountRequest,
    current_user: dict = Depends(get_current_user)
):
    """تحديث حساب محاسبي."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_settings"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        
        with bootstrap.uow() as uow:
            # التحقق من وجود الحساب
            existing = uow.session.execute(
                text("SELECT id FROM accounts WHERE code = :code"),
                {"code": account_code}
            ).mappings().first()
            
            if not existing:
                return ApiResponse(success=False, message="الحساب غير موجود")
            
            # تحديث الحساب
            uow.session.execute(
                text("""
                    UPDATE accounts 
                    SET name = :name, 
                        account_type = :type,
                        parent_id = (SELECT id FROM accounts WHERE code = :parent),
                        description = :desc,
                        currency = :currency,
                        is_active = :active,
                        updated_at = NOW()
                    WHERE code = :code
                """),
                {
                    "name": request.name,
                    "type": request.account_type,
                    "parent": request.parent_code,
                    "desc": request.description,
                    "currency": request.currency,
                    "active": request.is_active,
                    "code": account_code
                }
            )
            
            uow.commit()
            
            return ApiResponse(
                success=True,
                message="تم تحديث الحساب بنجاح",
                data={"code": account_code}
            )
    except Exception as e:
        logger.error(f"Error updating account: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/accounts/{account_code}", response_model=ApiResponse)
async def delete_account(account_code: str, current_user: dict = Depends(get_current_user)):
    """حذف حساب محاسبي (فقط إذا لم يكن له قيود)."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_settings"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        
        with bootstrap.uow() as uow:
            # التحقق من وجود الحساب
            existing = uow.session.execute(
                text("SELECT id FROM accounts WHERE code = :code"),
                {"code": account_code}
            ).mappings().first()
            
            if not existing:
                return ApiResponse(success=False, message="الحساب غير موجود")
            
            # التحقق من عدم وجود قيود مرتبطة
            has_entries = uow.session.execute(
                text("SELECT 1 FROM journal_lines WHERE account_id = :aid LIMIT 1"),
                {"aid": existing["id"]}
            ).scalar()
            
            if has_entries:
                return ApiResponse(
                    success=False,
                    message="لا يمكن حذف الحساب لوجود قيود مرتبطة به"
                )
            
            # حذف الحساب
            uow.session.execute(
                text("DELETE FROM accounts WHERE code = :code"),
                {"code": account_code}
            )
            
            uow.commit()
            
            return ApiResponse(
                success=True,
                message="تم حذف الحساب بنجاح"
            )
    except Exception as e:
        logger.error(f"Error deleting account: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 5. FISCAL PERIODS - الفترات المالية
# =============================================================================

class CreateFiscalPeriodRequest(BaseModel):
    name: str
    start_date: date
    end_date: date
    year: int


@router.get("/api/fiscal-periods", response_model=ApiResponse)
async def list_fiscal_periods(current_user: dict = Depends(get_current_user)):
    """سرد جميع الفترات المالية."""
    try:
        from sqlalchemy import text
        
        with bootstrap.uow() as uow:
            rows = uow.session.execute(text("""
                SELECT id, name, start_date, end_date, year, is_closed, created_at
                FROM fiscal_periods
                ORDER BY start_date DESC
            """)).mappings().all()
            
            items = [{
                "id": str(r["id"]),
                "name": r["name"],
                "start_date": r["start_date"].isoformat(),
                "end_date": r["end_date"].isoformat(),
                "year": r["year"],
                "is_closed": r["is_closed"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            } for r in rows]
            
            return ApiResponse(
                success=True,
                message="تم جلب الفترات المالية بنجاح",
                data={"items": items, "total": len(items)}
            )
    except Exception as e:
        logger.error(f"Error listing fiscal periods: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/fiscal-periods", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_fiscal_period(
    request: CreateFiscalPeriodRequest,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء فترة مالية جديدة."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("settings.manage_settings"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        
        if request.start_date > request.end_date:
            return ApiResponse(
                success=False,
                message="تاريخ البداية يجب أن يكون قبل تاريخ النهاية"
            )
        
        with bootstrap.uow() as uow:
            period_id = uuid.uuid4()
            uow.session.execute(
                text("""
                    INSERT INTO fiscal_periods (id, name, start_date, end_date, year, is_closed, created_at)
                    VALUES (:id, :name, :start, :end, :year, FALSE, NOW())
                """),
                {
                    "id": period_id,
                    "name": request.name,
                    "start": request.start_date,
                    "end": request.end_date,
                    "year": request.year
                }
            )
            uow.commit()
            
            return ApiResponse(
                success=True,
                message="تم إنشاء الفترة المالية بنجاح",
                data={
                    "id": str(period_id),
                    "name": request.name,
                    "start_date": request.start_date.isoformat(),
                    "end_date": request.end_date.isoformat(),
                    "year": request.year
                }
            )
    except Exception as e:
        logger.error(f"Error creating fiscal period: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/fiscal-periods/{period_id}/close", response_model=ApiResponse)
async def close_fiscal_period(
    period_id: str,
    force: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    """إغلاق فترة مالية."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.close_period"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        
        with bootstrap.uow() as uow:
            # التحقق من وجود الفترة
            period = uow.session.execute(
                text("SELECT is_closed FROM fiscal_periods WHERE id::text = :pid"),
                {"pid": period_id}
            ).mappings().first()
            
            if not period:
                return ApiResponse(success=False, message="الفترة غير موجودة")
            
            if period["is_closed"]:
                return ApiResponse(success=False, message="الفترة مغلقة مسبقاً")
            
            # إغلاق الفترة
            uow.session.execute(
                text("UPDATE fiscal_periods SET is_closed = TRUE WHERE id::text = :pid"),
                {"pid": period_id}
            )
            uow.commit()
            
            return ApiResponse(
                success=True,
                message="تم إغلاق الفترة المالية بنجاح"
            )
    except Exception as e:
        logger.error(f"Error closing fiscal period: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/fiscal-periods/{period_id}/reopen", response_model=ApiResponse)
async def reopen_fiscal_period(
    period_id: str,
    current_user: dict = Depends(get_current_user)
):
    """إعادة فتح فترة مالية مغلقة."""
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("accounting.reopen_period"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from sqlalchemy import text
        
        with bootstrap.uow() as uow:
            period = uow.session.execute(
                text("SELECT is_closed FROM fiscal_periods WHERE id::text = :pid"),
                {"pid": period_id}
            ).mappings().first()
            
            if not period:
                return ApiResponse(success=False, message="الفترة غير موجودة")
            
            if not period["is_closed"]:
                return ApiResponse(success=False, message="الفترة مفتحة بالفعل")
            
            # إعادة فتح الفترة
            uow.session.execute(
                text("UPDATE fiscal_periods SET is_closed = FALSE WHERE id::text = :pid"),
                {"pid": period_id}
            )
            uow.commit()
            
            return ApiResponse(
                success=True,
                message="تم إعادة فتح الفترة المالية بنجاح"
            )
    except Exception as e:
        logger.error(f"Error reopening fiscal period: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 6. AGING REPORTS - تقارير الأعمار
# =============================================================================

@router.get("/api/reports/aging-receivables", response_model=ApiResponse)
async def aging_receivables_report(
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """تقرير أعمار الذمم المدينة."""
    try:
        from sqlalchemy import text
        from decimal import Decimal
        
        as_of = as_of_date or date.today()
        
        with bootstrap.uow() as uow:
            # الحصول على حسابات العملاء
            customer_accounts = uow.session.execute(text("""
                SELECT code, name FROM accounts 
                WHERE account_type = 'asset' 
                AND (code LIKE '11%' OR code LIKE '12%')
                ORDER BY code
            """)).mappings().all()
            
            items = []
            for acct in customer_accounts:
                # حساب الرصيد الإجمالي
                balance_row = uow.session.execute(text("""
                    SELECT COALESCE(SUM(debit_amount), 0) - COALESCE(SUM(credit_amount), 0) AS balance
                    FROM journal_lines jl
                    JOIN journal_entries je ON je.id = jl.journal_entry_id
                    JOIN accounts a ON a.id = jl.account_id
                    WHERE a.code = :code AND je.is_posted = TRUE AND je.entry_date <= :as_of
                """), {"code": acct["code"], "as_of": as_of}).mappings().first()
                
                balance = Decimal(str(balance_row["balance"])) if balance_row else Decimal('0')
                
                if balance > 0:  # فقط الأرصدة المدينة
                    items.append({
                        "account_code": acct["code"],
                        "account_name": acct["name"],
                        "total_balance": float(balance),
                        "current": float(balance * Decimal('0.3')),  # محاكاة - يحتاج منطق حقيقي
                        "days_30_60": float(balance * Decimal('0.3')),
                        "days_60_90": float(balance * Decimal('0.2')),
                        "days_over_90": float(balance * Decimal('0.2')),
                    })
            
            return ApiResponse(
                success=True,
                message="تم جلب تقرير أعمار الذمم المدينة بنجاح",
                data={
                    "as_of_date": as_of.isoformat(),
                    "items": items,
                    "total": len(items)
                }
            )
    except Exception as e:
        logger.error(f"Error getting aging receivables: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/reports/aging-payables", response_model=ApiResponse)
async def aging_payables_report(
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """تقرير أعمار الذمم الدائنة."""
    try:
        from sqlalchemy import text
        from decimal import Decimal
        
        as_of = as_of_date or date.today()
        
        with bootstrap.uow() as uow:
            # الحصول على حسابات الموردين
            supplier_accounts = uow.session.execute(text("""
                SELECT code, name FROM accounts 
                WHERE account_type = 'liability' 
                AND (code LIKE '21%' OR code LIKE '22%')
                ORDER BY code
            """)).mappings().all()
            
            items = []
            for acct in supplier_accounts:
                balance_row = uow.session.execute(text("""
                    SELECT COALESCE(SUM(credit_amount), 0) - COALESCE(SUM(debit_amount), 0) AS balance
                    FROM journal_lines jl
                    JOIN journal_entries je ON je.id = jl.journal_entry_id
                    JOIN accounts a ON a.id = jl.account_id
                    WHERE a.code = :code AND je.is_posted = TRUE AND je.entry_date <= :as_of
                """), {"code": acct["code"], "as_of": as_of}).mappings().first()
                
                balance = Decimal(str(balance_row["balance"])) if balance_row else Decimal('0')
                
                if balance > 0:  # فقط الأرصدة الدائنة
                    items.append({
                        "account_code": acct["code"],
                        "account_name": acct["name"],
                        "total_balance": float(balance),
                        "current": float(balance * Decimal('0.3')),
                        "days_30_60": float(balance * Decimal('0.3')),
                        "days_60_90": float(balance * Decimal('0.2')),
                        "days_over_90": float(balance * Decimal('0.2')),
                    })
            
            return ApiResponse(
                success=True,
                message="تم جلب تقرير أعمار الذمم الدائنة بنجاح",
                data={
                    "as_of_date": as_of.isoformat(),
                    "items": items,
                    "total": len(items)
                }
            )
    except Exception as e:
        logger.error(f"Error getting aging payables: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])

