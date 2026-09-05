from fastapi import APIRouter, Query, Depends, status
from typing import List, Optional
from datetime import date
from datetime import date as date_type
from decimal import Decimal
import uuid

from pydantic import BaseModel, Field

from api_routers.shared import (
    bootstrap, logger, ApiResponse,
    get_current_user,
)

router = APIRouter(prefix="", tags=["reports"])


# =============================================================================
# 11. REPORTS
# =============================================================================

@router.get("/api/reports/trial-balance", response_model=ApiResponse)
async def trial_balance_report(
    as_of_date: Optional[date] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    include_zero_balances: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text

        def signed_balance(account_type, debit, credit):
            if account_type in ("asset", "expense"):
                return debit - credit
            return credit - debit

        with bootstrap.uow() as uow:
            accounts = uow.accounts.get_all_accounts()
            acct_meta = {
                str(a.code): {
                    'name': a.name if hasattr(a, 'name') else '',
                    'account_type': a.account_type if hasattr(a, 'account_type') else 'asset',
                    'currency': a.currency if hasattr(a, 'currency') else 'USD',
                }
                for a in accounts
            }

            if from_date and to_date:
                if from_date > to_date:
                    return ApiResponse(success=False, message="تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

                movement_rows = uow.session.execute(text(
                    "SELECT a.code AS code, COALESCE(SUM(l.debit_amount), 0) AS debit, "
                    "COALESCE(SUM(l.credit_amount), 0) AS credit "
                    "FROM ledger_entries l JOIN accounts a ON a.id = l.account_id "
                    "WHERE l.entry_date::date >= :from_date AND l.entry_date::date <= :to_date "
                    "GROUP BY a.code"
                ), {"from_date": from_date, "to_date": to_date}).mappings().all()

                opening_rows = uow.session.execute(text(
                    "SELECT a.code AS code, COALESCE(SUM(l.debit_amount), 0) AS debit, "
                    "COALESCE(SUM(l.credit_amount), 0) AS credit "
                    "FROM ledger_entries l JOIN accounts a ON a.id = l.account_id "
                    "WHERE l.entry_date::date < :from_date "
                    "GROUP BY a.code"
                ), {"from_date": from_date}).mappings().all()

                movement = {}
                for r in movement_rows:
                    movement[str(r['code'])] = (Decimal(r['debit']), Decimal(r['credit']))
                opening = {}
                for r in opening_rows:
                    opening[str(r['code'])] = (Decimal(r['debit']), Decimal(r['credit']))

                result = []
                all_codes = set(list(movement.keys()) + list(opening.keys()) + list(acct_meta.keys()))
                for code in sorted(all_codes):
                    op_d, op_c = opening.get(code, (Decimal('0'), Decimal('0')))
                    mv_d, mv_c = movement.get(code, (Decimal('0'), Decimal('0')))
                    meta = acct_meta.get(code, {'name': '', 'account_type': 'asset', 'currency': 'USD'})
                    op_balance = signed_balance(meta['account_type'], op_d, op_c)
                    close_balance = signed_balance(meta['account_type'], op_d + mv_d, op_c + mv_c)
                    if not include_zero_balances and op_balance == 0 and mv_d == 0 and mv_c == 0 and close_balance == 0:
                        continue
                    result.append({
                        'account_code': code,
                        'name': meta['name'],
                        'account_type': meta['account_type'],
                        'currency': meta['currency'],
                        'opening_balance': float(op_balance),
                        'debit': float(mv_d),
                        'credit': float(mv_c),
                        'balance': float(close_balance),
                    })
                totals = {
                    'opening_balance': sum(i['opening_balance'] for i in result),
                    'debit': sum(i['debit'] for i in result),
                    'credit': sum(i['credit'] for i in result),
                    'balance': sum(i['balance'] for i in result),
                }
                return ApiResponse(success=True, message="تم جلب ميزان المراجعة بنجاح",
                                   data={'from_date': from_date.isoformat(), 'to_date': to_date.isoformat(),
                                         'items': result, 'totals': totals, 'total': len(result)})
            else:
                as_of = as_of_date or date.today()
                balances = uow.ledger.get_trial_balance(as_of)
                result = []
                for code, balance in balances.items():
                    code = str(code)
                    meta = acct_meta.get(code, {'name': '', 'account_type': 'asset', 'currency': 'USD'})
                    amt = Decimal(balance.amount)
                    if not include_zero_balances and amt == 0:
                        continue
                    result.append({
                        'account_code': code,
                        'name': meta['name'],
                        'account_type': meta['account_type'],
                        'currency': balance.currency or meta['currency'],
                        'opening_balance': 0.0,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': float(amt),
                    })
                return ApiResponse(success=True, message="تم جلب ميزان المراجعة بنجاح",
                                   data={'as_of': as_of.isoformat(), 'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting trial balance: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/reports/accounts", response_model=ApiResponse)
async def accounts_report(
    include_inactive: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            accounts = uow.accounts.get_all_accounts(include_inactive=include_inactive)
            result = [
                {
                    'code': str(a.code),
                    'name': a.name if hasattr(a, 'name') else '',
                    'account_type': a.account_type if hasattr(a, 'account_type') else '',
                }
                for a in accounts
            ]
            return ApiResponse(success=True, message="تم جلب الحسابات بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting accounts report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class IncomeStatementRequest(BaseModel):
    period_start: date
    period_end: date
    currency: str = "USD"
    include_comparative: bool = False


class BalanceSheetRequest(BaseModel):
    as_of_date: date
    currency: str = "USD"


class CashFlowRequest(BaseModel):
    period_start: date
    period_end: date
    currency: str = "USD"
    method: str = "indirect"


@router.post("/api/reports/income-statement", response_model=ApiResponse)
async def income_statement_report(
    request: IncomeStatementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import GenerateIncomeStatementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = GenerateIncomeStatementCommand(
            period_start=request.period_start,
            period_end=request.period_end,
            currency=request.currency,
            include_comparative=request.include_comparative,
            generated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم توليد قائمة الدخل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error generating income statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/reports/balance-sheet", response_model=ApiResponse)
async def balance_sheet_report(
    request: BalanceSheetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import GenerateBalanceSheetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = GenerateBalanceSheetCommand(
            as_of_date=request.as_of_date,
            currency=request.currency,
            generated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم توليد الميزانية العمومية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error generating balance sheet: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/reports/cash-flow", response_model=ApiResponse)
async def cash_flow_report(
    request: CashFlowRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import GenerateCashFlowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = GenerateCashFlowCommand(
            period_start=request.period_start,
            period_end=request.period_end,
            currency=request.currency,
            method=request.method,
            generated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم توليد قائمة التدفقات النقدية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error generating cash flow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/reports/financial-statements", response_model=ApiResponse)
async def list_financial_statements(
    statement_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import ListFinancialStatementsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = ListFinancialStatementsQuery(statement_type=statement_type, limit=limit)
        items = query_bus.dispatch(query) or []
        return ApiResponse(success=True, message="تم جلب القوائم المالية بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error listing financial statements: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/accounts/{account_code}/statement", response_model=ApiResponse)
async def account_statement(
    account_code: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        to_date = to_date or date.today()
        with bootstrap.uow() as uow:
            acct = uow.session.execute(text(
                "SELECT id, code, name, account_type, currency FROM accounts WHERE code = :code"
            ), {"code": account_code}).mappings().first()
            if acct is None:
                return ApiResponse(success=False, message="الحساب غير موجود")

            rows = uow.session.execute(text(
                "SELECT je.id AS entry_id, je.entry_date AS entry_date, je.description AS description, "
                "jl.debit_amount AS debit, jl.credit_amount AS credit "
                "FROM journal_lines jl "
                "JOIN journal_entries je ON je.id = jl.journal_entry_id "
                "JOIN accounts a ON a.id = jl.account_id "
                "WHERE a.code = :code AND je.is_posted = TRUE AND je.entry_date::date <= :to "
                "ORDER BY je.entry_date, jl.line_order"
            ), {"code": account_code, "to": to_date}).mappings().all()

            account_type = acct["account_type"]

            def signed(d, c):
                d = Decimal(str(d)); c = Decimal(str(c))
                if account_type in ("asset", "expense"):
                    return d - c
                return c - d

            opening = sum(signed(r["debit"], r["credit"]) for r in rows if from_date and r["entry_date"] < from_date)
            filtered = [r for r in rows if not from_date or r["entry_date"] >= from_date]

            items = []
            if from_date and opening != 0:
                items.append({"date": from_date, "entry_id": None, "description": "رصيد افتتاحي",
                              "debit": 0.0, "credit": 0.0, "balance": float(opening)})
            running = opening
            for r in filtered:
                running += signed(r["debit"], r["credit"])
                items.append({
                    "date": r["entry_date"],
                    "entry_id": str(r["entry_id"]),
                    "description": r["description"] or "",
                    "debit": float(r["debit"]),
                    "credit": float(r["credit"]),
                    "balance": float(running),
                })

            return ApiResponse(success=True, message="تم جلب كشف حساب الحساب بنجاح",
                               data={
                                   "account_code": account_code,
                                   "account_name": acct["name"],
                                   "account_type": account_type,
                                   "currency": acct["currency"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat(),
                                   "items": items,
                                   "balance": float(running),
                               })
    except Exception as e:
        logger.error(f"Error getting account statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 32. BUDGETS (الميزانيات التقديرية)
# =============================================================================

def _ensure_budget_tables(uow):
    from sqlalchemy import text
    statements = [
        "CREATE TABLE IF NOT EXISTS budgets ("
        " id UUID PRIMARY KEY, name VARCHAR(200) NOT NULL, period_start DATE NOT NULL, period_end DATE NOT NULL, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', status VARCHAR(20) NOT NULL DEFAULT 'active', "
        " created_by VARCHAR(100), created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        "CREATE TABLE IF NOT EXISTS budget_lines ("
        " id UUID PRIMARY KEY, budget_id UUID NOT NULL, account_code VARCHAR(20) NOT NULL, "
        " amount NUMERIC(15,2) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    ]
    for stmt in statements:
        uow.session.execute(text(stmt))


class BudgetLineRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    amount: Decimal = Field(..., ge=0)


class CreateBudgetRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    period_start: date_type
    period_end: date_type
    currency: str = "USD"
    lines: List[BudgetLineRequest] = Field(..., min_length=1)


@router.post("/api/budgets", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(request: CreateBudgetRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        if request.period_start > request.period_end:
            return ApiResponse(success=False, message="تاريخ بداية الميزانية يجب أن يكون قبل تاريخ نهايتها")
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            for line in request.lines:
                exists = uow.session.execute(text(
                    "SELECT code FROM accounts WHERE code = :code"
                ), {"code": line.account_code}).scalar()
                if not exists:
                    return ApiResponse(success=False, message=f"الحساب {line.account_code} غير موجود")

            budget_id = uuid.uuid4()
            uow.session.execute(
                text("INSERT INTO budgets (id, name, period_start, period_end, currency, status, created_by) "
                     "VALUES (:id, :name, :start, :end, :currency, 'active', :by)"),
                {
                    "id": budget_id,
                    "name": request.name,
                    "start": request.period_start,
                    "end": request.period_end,
                    "currency": request.currency,
                    "by": current_user["username"],
                },
            )
            for line in request.lines:
                uow.session.execute(
                    text("INSERT INTO budget_lines (id, budget_id, account_code, amount) VALUES (:id, :bid, :code, :amount)"),
                    {"id": uuid.uuid4(), "bid": budget_id, "code": line.account_code, "amount": line.amount},
                )
            uow.commit()

            total_budget = sum(line.amount for line in request.lines)
            return ApiResponse(success=True, message="تم إنشاء الميزانية بنجاح",
                               data={
                                   "id": str(budget_id),
                                   "name": request.name,
                                   "period_start": request.period_start.isoformat(),
                                   "period_end": request.period_end.isoformat(),
                                   "currency": request.currency,
                                   "total_budget": float(total_budget),
                                   "lines_count": len(request.lines),
                               })
    except Exception as e:
        logger.error(f"Error creating budget: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/budgets", response_model=ApiResponse)
async def list_budgets(current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            rows = uow.session.execute(text(
                "SELECT b.id, b.name, b.period_start, b.period_end, b.currency, b.status, b.created_by, b.created_at, "
                "COALESCE(SUM(bl.amount), 0) AS total_budget, COUNT(bl.id) AS lines_count "
                "FROM budgets b LEFT JOIN budget_lines bl ON bl.budget_id = b.id "
                "GROUP BY b.id ORDER BY b.created_at DESC"
            )).mappings().all()
            items = [{
                "id": str(r["id"]),
                "name": r["name"],
                "period_start": r["period_start"].isoformat(),
                "period_end": r["period_end"].isoformat(),
                "currency": r["currency"],
                "status": r["status"],
                "created_by": r["created_by"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "total_budget": float(r["total_budget"]),
                "lines_count": r["lines_count"],
            } for r in rows]
            return ApiResponse(success=True, message="تم جلب الميزانيات بنجاح",
                               data={"items": items, "total": len(items)})
    except Exception as e:
        logger.error(f"Error listing budgets: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/budgets/{budget_id}", response_model=ApiResponse)
async def get_budget(budget_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            b = uow.session.execute(text(
                "SELECT id, name, period_start, period_end, currency, status, created_by, created_at "
                "FROM budgets WHERE id::text = :bid"
            ), {"bid": budget_id}).mappings().first()
            if b is None:
                return ApiResponse(success=False, message="الميزانية غير موجودة")
            lines = uow.session.execute(text(
                "SELECT id, account_code, amount FROM budget_lines WHERE budget_id::text = :bid ORDER BY account_code"
            ), {"bid": budget_id}).mappings().all()
            return ApiResponse(success=True, message="تم جلب الميزانية بنجاح",
                               data={
                                   "id": str(b["id"]),
                                   "name": b["name"],
                                   "period_start": b["period_start"].isoformat(),
                                   "period_end": b["period_end"].isoformat(),
                                   "currency": b["currency"],
                                   "status": b["status"],
                                   "created_by": b["created_by"],
                                   "created_at": b["created_at"].isoformat() if b["created_at"] else None,
                                   "lines": [{
                                       "id": str(l["id"]),
                                       "account_code": l["account_code"],
                                       "amount": float(l["amount"]),
                                   } for l in lines],
                                   "total_budget": float(sum(l["amount"] for l in lines)),
                               })
    except Exception as e:
        logger.error(f"Error getting budget: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/reports/budget-vs-actual", response_model=ApiResponse)
async def budget_vs_actual_report(
    budget_id: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            budgets = []
            if budget_id:
                b = uow.session.execute(text(
                    "SELECT id, name, period_start, period_end, currency FROM budgets WHERE id::text = :bid"
                ), {"bid": budget_id}).mappings().first()
                if b is None:
                    return ApiResponse(success=False, message="الميزانية غير موجودة")
                budgets = [b]
            else:
                rows = uow.session.execute(text(
                    "SELECT id, name, period_start, period_end, currency FROM budgets "
                    "WHERE status = 'active' ORDER BY created_at DESC"
                )).mappings().all()
                budgets = rows

            all_reports = []
            for b in budgets:
                p_start = period_start or b["period_start"]
                p_end = period_end or b["period_end"]
                lines = uow.session.execute(text(
                    "SELECT account_code, amount FROM budget_lines WHERE budget_id::text = :bid ORDER BY account_code"
                ), {"bid": str(b["id"])}).mappings().all()

                actual_map = {}
                for l in lines:
                    acct = uow.session.execute(text(
                        "SELECT account_type FROM accounts WHERE code = :code"
                    ), {"code": l["account_code"]}).mappings().first()
                    account_type = acct["account_type"] if acct else "expense"
                    row = uow.session.execute(text(
                        "SELECT COALESCE(SUM(jl.debit_amount), 0) AS debit, COALESCE(SUM(jl.credit_amount), 0) AS credit "
                        "FROM journal_entries je "
                        "JOIN journal_lines jl ON jl.journal_entry_id = je.id "
                        "JOIN accounts a ON a.id = jl.account_id "
                        "WHERE a.code = :code AND je.is_posted = TRUE "
                        "AND je.entry_date::date BETWEEN :start AND :end"
                    ), {"code": l["account_code"], "start": p_start, "end": p_end}).mappings().first()
                    debit = Decimal(str(row["debit"]))
                    credit = Decimal(str(row["credit"]))
                    if account_type in ("asset", "expense"):
                        actual = debit - credit
                    else:
                        actual = credit - debit
                    actual_map[l["account_code"]] = actual

                items = []
                for l in lines:
                    budget_amt = Decimal(str(l["amount"]))
                    actual_amt = actual_map.get(l["account_code"], Decimal("0"))
                    variance = budget_amt - actual_amt
                    variance_pct = (variance / budget_amt * Decimal("100")) if budget_amt != 0 else None
                    items.append({
                        "account_code": l["account_code"],
                        "budget": float(budget_amt),
                        "actual": float(actual_amt),
                        "variance": float(variance),
                        "variance_pct": float(variance_pct) if variance_pct is not None else None,
                    })
                all_reports.append({
                    "budget_id": str(b["id"]),
                    "name": b["name"],
                    "currency": b["currency"],
                    "period_start": p_start.isoformat(),
                    "period_end": p_end.isoformat(),
                    "items": items,
                    "total_budget": float(sum(i["budget"] for i in items)),
                    "total_actual": float(sum(i["actual"] for i in items)),
                    "total_variance": float(sum(i["variance"] for i in items)),
                })
            return ApiResponse(success=True, message="تم جلب تقرير الميزانية مقابل الفعلي بنجاح",
                               data={"reports": all_reports})
    except Exception as e:
        logger.error(f"Error getting budget vs actual report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
