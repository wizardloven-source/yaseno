from fastapi import APIRouter, Query, Depends, status
from typing import Optional
from datetime import date

from api_routers.shared import (
    bootstrap, logger, ApiResponse,
    CreateJournalEntryRequest, CreateAccountRequest,
    get_current_user, filter_fields,
)

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
