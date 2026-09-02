from fastapi import APIRouter, Depends, status
from decimal import Decimal
from datetime import datetime, timedelta
from datetime import date as date_type
from typing import Optional
import uuid

from pydantic import BaseModel, Field

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user

router = APIRouter(prefix="", tags=["reconciliation"])


# =============================================================================
# 30. BANK RECONCILIATION (التسوية البنكية)
# =============================================================================

def _ensure_reconciliation_tables(uow):
    from sqlalchemy import text
    statements = [
        "CREATE TABLE IF NOT EXISTS bank_statements ("
        " id UUID PRIMARY KEY, account_code VARCHAR(20) NOT NULL, bank_name VARCHAR(200) NOT NULL, "
        " account_number VARCHAR(50) NOT NULL, statement_date DATE NOT NULL, "
        " opening_balance NUMERIC(15,2) NOT NULL DEFAULT 0, closing_balance NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', file_name VARCHAR(500), file_content TEXT, file_hash VARCHAR(64), "
        " uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(), uploaded_by VARCHAR(100) NOT NULL DEFAULT 'system', "
        " created_at TIMESTAMPTZ NOT NULL DEFAULT now(), statement_metadata JSONB DEFAULT '{}'::jsonb)",
        "CREATE TABLE IF NOT EXISTS reconciliations ("
        " id UUID PRIMARY KEY, bank_statement_id UUID NOT NULL UNIQUE, account_code VARCHAR(20) NOT NULL, "
        " reconciliation_date TIMESTAMPTZ NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'draft', "
        " reconciliation_type VARCHAR(20) NOT NULL DEFAULT 'bank', "
        " opening_balance NUMERIC(15,2) NOT NULL DEFAULT 0, closing_balance NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " bank_opening_balance NUMERIC(15,2) NOT NULL DEFAULT 0, bank_closing_balance NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', journal_entry_id UUID, notes TEXT, "
        " created_by VARCHAR(100) NOT NULL DEFAULT 'system', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        " updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_by VARCHAR(100), completed_at TIMESTAMPTZ, "
        " version INTEGER NOT NULL DEFAULT 1, reconciliation_metadata JSONB DEFAULT '{}'::jsonb)",
        "CREATE TABLE IF NOT EXISTS reconciliation_matches ("
        " id UUID PRIMARY KEY, reconciliation_id UUID NOT NULL, bank_line_id VARCHAR(100) NOT NULL, "
        " ledger_entry_id VARCHAR(100) NOT NULL, amount NUMERIC(15,2) NOT NULL, currency VARCHAR(3) NOT NULL DEFAULT 'USD', "
        " status VARCHAR(20) NOT NULL DEFAULT 'matched', matched_by VARCHAR(100) NOT NULL DEFAULT 'system', "
        " matched_at TIMESTAMPTZ NOT NULL DEFAULT now(), match_score INTEGER NOT NULL DEFAULT 0, notes TEXT, "
        " match_metadata JSONB DEFAULT '{}'::jsonb)",
        "CREATE TABLE IF NOT EXISTS reconciliation_items ("
        " id UUID PRIMARY KEY, reconciliation_id UUID NOT NULL, payment_id VARCHAR(100) NOT NULL, "
        " matched BOOLEAN NOT NULL DEFAULT FALSE, amount NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', created_by VARCHAR(100), created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    ]
    for stmt in statements:
        uow.session.execute(text(stmt))


class CreateReconciliationRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    as_of_date: date_type
    statement_balance: Decimal = Field(..., ge=0)
    opening_balance: Decimal = Field(Decimal("0"), ge=0)
    bank_name: Optional[str] = "حساب مصرفي"
    currency: str = "USD"
    notes: Optional[str] = None


class MatchPaymentRequest(BaseModel):
    payment_id: str
    amount: Decimal = Field(..., ge=0)
    currency: Optional[str] = None
    notes: Optional[str] = None


@router.post("/api/reconciliations", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_reconciliation(request: CreateReconciliationRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            account = uow.session.execute(text(
                "SELECT code, name FROM accounts WHERE code = :code"
            ), {"code": request.account_code}).mappings().first()
            if account is None:
                return ApiResponse(success=False, message="الحساب غير موجود")

            bank_statement_id = uuid.uuid4()
            reconciliation_id = uuid.uuid4()
            now_ts = datetime.now()
            uow.session.execute(
                text("INSERT INTO bank_statements "
                     "(id, account_code, bank_name, account_number, statement_date, opening_balance, closing_balance, "
                     " currency, uploaded_at, uploaded_by, created_at) "
                     "VALUES (:id, :account_code, :bank_name, '-', :stmt_date, :opening, :closing, :currency, :now_ts, :by, :now_ts)"),
                {
                    "id": bank_statement_id,
                    "account_code": request.account_code,
                    "bank_name": request.bank_name or "حساب مصرفي",
                    "stmt_date": request.as_of_date,
                    "opening": request.opening_balance,
                    "closing": request.statement_balance,
                    "currency": request.currency,
                    "now_ts": now_ts,
                    "by": current_user["username"],
                },
            )
            uow.session.execute(
                text("INSERT INTO reconciliations "
                     "(id, bank_statement_id, account_code, reconciliation_date, status, reconciliation_type, "
                     " opening_balance, closing_balance, bank_opening_balance, bank_closing_balance, currency, notes, "
                     " created_by, created_at, updated_at, version) "
                     "VALUES (:id, :bsid, :account_code, :rdate, 'draft', 'bank', 0, 0, :bank_opening, :bank_closing, "
                     " :currency, :notes, :by, :now_ts, :now_ts, 1)"),
                {
                    "id": reconciliation_id,
                    "bsid": bank_statement_id,
                    "account_code": request.account_code,
                    "rdate": now_ts,
                    "bank_opening": request.opening_balance,
                    "bank_closing": request.statement_balance,
                    "currency": request.currency,
                    "notes": request.notes,
                    "by": current_user["username"],
                    "now_ts": now_ts,
                },
            )
            uow.commit()

            return ApiResponse(success=True, message="تم إنشاء التسوية البنكية بنجاح",
                               data={
                                   "id": str(reconciliation_id),
                                   "account_code": request.account_code,
                                   "as_of_date": request.as_of_date.isoformat(),
                                   "status": "draft",
                                   "variance": float(Decimal(str(request.statement_balance)) - Decimal(str(request.opening_balance))),
                                   "items": [],
                               })
    except Exception as e:
        logger.error(f"Error creating reconciliation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/reconciliations", response_model=ApiResponse)
async def list_reconciliations(current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            rows = uow.session.execute(text(
                "SELECT r.id, r.account_code, r.reconciliation_date, r.status, r.reconciliation_type, "
                " r.bank_opening_balance, r.bank_closing_balance, r.opening_balance, r.closing_balance, "
                " r.currency, r.created_by, r.created_at, r.completed_at, r.notes, bs.statement_date "
                "FROM reconciliations r JOIN bank_statements bs ON bs.id = r.bank_statement_id "
                "ORDER BY r.created_at DESC"
            )).mappings().all()
            items = []
            for r in rows:
                variance = Decimal(str(r["bank_closing_balance"])) - Decimal(str(r["closing_balance"]))
                items.append({
                    "id": str(r["id"]),
                    "account_code": r["account_code"],
                    "statement_date": r["statement_date"].isoformat() if r["statement_date"] else None,
                    "reconciliation_date": r["reconciliation_date"].isoformat() if r["reconciliation_date"] else None,
                    "status": r["status"],
                    "reconciliation_type": r["reconciliation_type"],
                    "bank_opening_balance": float(r["bank_opening_balance"]),
                    "bank_closing_balance": float(r["bank_closing_balance"]),
                    "opening_balance": float(r["opening_balance"]),
                    "closing_balance": float(r["closing_balance"]),
                    "variance": float(variance),
                    "currency": r["currency"],
                    "created_by": r["created_by"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                    "notes": r["notes"],
                })
            return ApiResponse(success=True, message="تم جلب التسويات البنكية بنجاح",
                               data={"items": items, "total": len(items)})
    except Exception as e:
        logger.error(f"Error listing reconciliations: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/reconciliations/{reconciliation_id}", response_model=ApiResponse)
async def get_reconciliation(reconciliation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            r = uow.session.execute(text(
                "SELECT r.id, r.account_code, r.reconciliation_date, r.status, r.reconciliation_type, "
                " r.bank_opening_balance, r.bank_closing_balance, r.opening_balance, r.closing_balance, "
                " r.currency, r.created_by, r.created_at, r.completed_at, r.completed_by, r.notes, bs.statement_date "
                "FROM reconciliations r JOIN bank_statements bs ON bs.id = r.bank_statement_id "
                "WHERE r.id::text = :rid"
            ), {"rid": reconciliation_id}).mappings().first()
            if r is None:
                return ApiResponse(success=False, message="التسوية غير موجودة")

            matched_rows = uow.session.execute(text(
                "SELECT bank_line_id, ledger_entry_id, amount, currency, status, matched_by, matched_at, notes "
                "FROM reconciliation_matches WHERE reconciliation_id::text = :rid ORDER BY matched_at"
            ), {"rid": reconciliation_id}).mappings().all()
            items = [{
                "bank_line_id": m["bank_line_id"],
                "ledger_entry_id": m["ledger_entry_id"],
                "payment_id": m["ledger_entry_id"],
                "amount": float(m["amount"]),
                "currency": m["currency"],
                "status": m["status"],
                "matched_by": m["matched_by"],
                "matched_at": m["matched_at"].isoformat() if m["matched_at"] else None,
                "notes": m["notes"],
            } for m in matched_rows]

            suggested = []
            stmt_date = r["statement_date"]
            if stmt_date:
                sug_rows = uow.session.execute(text(
                    "SELECT id, code, payment_date, amount, currency, status FROM payments "
                    "WHERE payment_date::date BETWEEN :from_d AND :to_d ORDER BY payment_date LIMIT 50"
                ), {"from_d": (stmt_date - timedelta(days=30)).isoformat(), "to_d": stmt_date.isoformat()}).mappings().all()
                for s in sug_rows:
                    suggested.append({
                        "payment_id": str(s["id"]),
                        "code": s["code"],
                        "payment_date": s["payment_date"].isoformat() if s["payment_date"] else None,
                        "amount": float(s["amount"]),
                        "currency": s["currency"],
                        "status": s["status"],
                    })

            return ApiResponse(success=True, message="تم جلب التسوية بنجاح",
                               data={
                                   "id": str(r["id"]),
                                   "account_code": r["account_code"],
                                   "statement_date": r["statement_date"].isoformat() if r["statement_date"] else None,
                                   "status": r["status"],
                                   "reconciliation_type": r["reconciliation_type"],
                                   "bank_opening_balance": float(r["bank_opening_balance"]),
                                   "bank_closing_balance": float(r["bank_closing_balance"]),
                                   "opening_balance": float(r["opening_balance"]),
                                   "closing_balance": float(r["closing_balance"]),
                                   "variance": float(Decimal(str(r["bank_closing_balance"])) - Decimal(str(r["closing_balance"]))),
                                   "currency": r["currency"],
                                   "notes": r["notes"],
                                   "created_by": r["created_by"],
                                   "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                                   "completed_by": r["completed_by"],
                                   "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                                   "items": items,
                                   "suggested_matches": suggested,
                               })
    except Exception as e:
        logger.error(f"Error getting reconciliation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/reconciliations/{reconciliation_id}/match", response_model=ApiResponse)
async def match_reconciliation_item(reconciliation_id: str, request: MatchPaymentRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            r = uow.session.execute(text(
                "SELECT id, status, opening_balance, bank_closing_balance, currency FROM reconciliations "
                "WHERE id::text = :rid"
            ), {"rid": reconciliation_id}).mappings().first()
            if r is None:
                return ApiResponse(success=False, message="التسوية غير موجودة")
            if r["status"] in ("reconciled", "cancelled"):
                return ApiResponse(success=False, message="لا يمكن المطابقة على تسوية مكتملة أو ملغاة")

            payment = uow.session.execute(text(
                "SELECT id, code, amount, currency, status FROM payments WHERE id::text = :pid"
            ), {"pid": request.payment_id}).mappings().first()
            if payment is None:
                return ApiResponse(success=False, message="الدفعة غير موجودة")

            already_matched = uow.session.execute(text(
                "SELECT 1 FROM reconciliation_matches WHERE ledger_entry_id = :pid "
                "AND reconciliation_id::text <> :rid LIMIT 1"
            ), {"pid": request.payment_id, "rid": reconciliation_id}).scalar()
            if already_matched:
                return ApiResponse(success=False, message="الدفعة مطابقة بالفعل لتسوية أخرى")
            already_in_this = uow.session.execute(text(
                "SELECT 1 FROM reconciliation_matches WHERE ledger_entry_id = :pid "
                "AND reconciliation_id::text = :rid LIMIT 1"
            ), {"pid": request.payment_id, "rid": reconciliation_id}).scalar()
            if already_in_this:
                return ApiResponse(success=False, message="الدفعة مطابقة بالفعل لهذه التسوية")

            match_id = uuid.uuid4()
            currency = request.currency or r["currency"] or payment["currency"]
            amount = Decimal(str(request.amount))
            now_ts = datetime.now()

            uow.session.execute(
                text("INSERT INTO reconciliation_matches "
                     "(id, reconciliation_id, bank_line_id, ledger_entry_id, amount, currency, status, matched_by, "
                     " matched_at, match_score, notes) "
                     "VALUES (:id, :rid, :blid, :leid, :amount, :currency, 'matched', :by, :now_ts, 100, :notes)"),
                {
                    "id": match_id,
                    "rid": uuid.UUID(reconciliation_id),
                    "blid": str(payment["code"]) or request.payment_id,
                    "leid": request.payment_id,
                    "amount": amount,
                    "currency": currency,
                    "by": current_user["username"],
                    "now_ts": now_ts,
                    "notes": request.notes,
                },
            )
            uow.session.execute(
                text("INSERT INTO reconciliation_items "
                     "(id, reconciliation_id, payment_id, matched, amount, currency, created_by) "
                     "VALUES (:id, :rid, :pid, TRUE, :amount, :currency, :by)"),
                {
                    "id": match_id,
                    "rid": uuid.UUID(reconciliation_id),
                    "pid": request.payment_id,
                    "amount": amount,
                    "currency": currency,
                    "by": current_user["username"],
                },
            )
            uow.session.execute(
                text("UPDATE reconciliations SET "
                     " closing_balance = opening_balance + COALESCE((SELECT SUM(amount) FROM reconciliation_matches "
                     "   WHERE reconciliation_id = :rid2), 0), "
                     " status = 'in_progress', updated_at = :now_ts WHERE id::text = :rid"),
                {"rid2": uuid.UUID(reconciliation_id), "rid": reconciliation_id, "now_ts": now_ts},
            )
            uow.commit()

            closing = Decimal(str(r["opening_balance"]))
            matched_sum = uow.session.execute(text(
                "SELECT COALESCE(SUM(amount), 0) FROM reconciliation_matches WHERE reconciliation_id::text = :rid"
            ), {"rid": reconciliation_id}).scalar()
            closing += Decimal(str(matched_sum or 0))

            return ApiResponse(success=True, message="تمت مطابقة الدفعة بنجاح",
                               data={
                                   "match_id": str(match_id),
                                   "reconciliation_id": reconciliation_id,
                                   "payment_id": request.payment_id,
                                   "amount": float(amount),
                                   "currency": currency,
                                   "variance": float(Decimal(str(r["bank_closing_balance"])) - closing),
                               })
    except Exception as e:
        logger.error(f"Error matching reconciliation item: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/reconciliations/{reconciliation_id}/complete", response_model=ApiResponse)
async def complete_reconciliation(reconciliation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            r = uow.session.execute(text(
                "SELECT id, status, opening_balance, closing_balance, bank_closing_balance FROM reconciliations "
                "WHERE id::text = :rid"
            ), {"rid": reconciliation_id}).mappings().first()
            if r is None:
                return ApiResponse(success=False, message="التسوية غير موجودة")
            if r["status"] == "reconciled":
                return ApiResponse(success=False, message="التسوية مكتملة بالفعل")

            now_ts = datetime.now()
            uow.session.execute(
                text("UPDATE reconciliations SET status = 'reconciled', completed_by = :by, completed_at = :now_ts, "
                     " updated_at = :now_ts WHERE id::text = :rid"),
                {"by": current_user["username"], "now_ts": now_ts, "rid": reconciliation_id},
            )
            uow.commit()

            variance = Decimal(str(r["bank_closing_balance"])) - Decimal(str(r["closing_balance"]))
            return ApiResponse(success=True, message="تم إكمال التسوية البنكية بنجاح",
                               data={
                                   "reconciliation_id": reconciliation_id,
                                   "status": "reconciled",
                                   "completed_by": current_user["username"],
                                   "completed_at": now_ts.isoformat(),
                                   "variance": float(variance),
                               })
    except Exception as e:
        logger.error(f"Error completing reconciliation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 31. FX REVALUATION (إعادة تقييم العملات)
# =============================================================================

def _get_fx_rate(uow, base_code, target_code, as_of_date):
    from sqlalchemy import text
    if base_code == target_code:
        return Decimal("1")
    rate = uow.session.execute(text(
        "SELECT er.rate FROM exchange_rates er "
        "JOIN currencies fc ON fc.id = er.from_currency_id AND fc.code = :base "
        "JOIN currencies tc ON tc.id = er.to_currency_id AND tc.code = :target "
        "WHERE er.effective_date <= CAST(:as_of AS timestamptz) "
        "ORDER BY er.effective_date DESC LIMIT 1"
    ), {"base": base_code, "target": target_code, "as_of": as_of_date}).scalar()
    if rate is not None:
        return Decimal(str(rate))
    row = uow.session.execute(text(
        "SELECT exchange_rates FROM currencies WHERE code = :base"
    ), {"base": base_code}).scalar()
    if row:
        val = row.get(target_code)
        if val:
            return Decimal(str(val))
    return None


class RevaluationRequest(BaseModel):
    as_of_date: date_type
    fx_gain_account_code: str = Field(..., min_length=3, max_length=20)
    fx_loss_account_code: str = Field(..., min_length=3, max_length=20)
    currency: Optional[str] = None


def _extract_entry_id(result):
    if result is None:
        return None
    if hasattr(result, "id"):
        return str(result.id)
    if isinstance(result, dict):
        return result.get("id")
    return None


@router.post("/api/currency/revaluation", response_model=ApiResponse)
async def run_fx_revaluation(request: RevaluationRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        from core.application.accounting.commands import CreateJournalEntryCommand, PostJournalEntryCommand

        with bootstrap.uow() as uow:
            base_code = uow.session.execute(text(
                "SELECT code FROM currencies WHERE is_base = TRUE LIMIT 1"
            )).scalar()
            base_code = str(base_code) if base_code else "USD"

            gain = uow.session.execute(text(
                "SELECT code FROM accounts WHERE code = :code"
            ), {"code": request.fx_gain_account_code}).scalar()
            loss = uow.session.execute(text(
                "SELECT code FROM accounts WHERE code = :code"
            ), {"code": request.fx_loss_account_code}).scalar()
            if not gain:
                return ApiResponse(success=False, message="حساب أرباح فروق العملة غير موجود")
            if not loss:
                return ApiResponse(success=False, message="حساب خسائر فروق العملة غير موجود")

            rows = uow.session.execute(text(
                "SELECT a.code, a.currency, a.account_type, "
                "COALESCE(SUM(l.debit_amount), 0) AS debit, COALESCE(SUM(l.credit_amount), 0) AS credit "
                "FROM accounts a "
                "LEFT JOIN ledger_entries l ON l.account_id = a.id AND l.entry_date::date <= :as_of "
                "WHERE a.currency IS NOT NULL AND a.currency <> '' AND a.currency <> :base "
                "GROUP BY a.code, a.currency, a.account_type"
            ), {"as_of": request.as_of_date, "base": base_code}).mappings().all()

            lines = []
            summary = []
            skipped = []
            for r in rows:
                balance = Decimal(str(r["debit"])) - Decimal(str(r["credit"]))
                account_type = r["account_type"]
                if account_type in ("liability", "equity", "revenue"):
                    balance = -balance
                if abs(balance) < Decimal("0.01"):
                    continue
                rate = _get_fx_rate(uow, base_code, r["currency"], request.as_of_date)
                if rate is None:
                    skipped.append({"account_code": r["code"], "currency": r["currency"], "reason": "no_rate"})
                    continue
                diff = balance * (rate - Decimal("1"))
                if abs(diff) < Decimal("0.01"):
                    continue
                is_debit_balance = account_type in ("asset", "expense")
                if is_debit_balance:
                    if diff > 0:
                        lines.append({"account_code": r["code"], "debit": abs(diff), "description": "فروق عملة (ربح)"})
                        lines.append({"account_code": request.fx_gain_account_code, "credit": abs(diff), "description": "إعادة تقييم عملة"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "gain"})
                    else:
                        lines.append({"account_code": r["code"], "credit": abs(diff), "description": "فروق عملة (خسارة)"})
                        lines.append({"account_code": request.fx_loss_account_code, "debit": abs(diff), "description": "إعادة تقييم عملة"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "loss"})
                else:
                    if diff > 0:
                        lines.append({"account_code": request.fx_loss_account_code, "debit": abs(diff), "description": "إعادة تقييم عملة"})
                        lines.append({"account_code": r["code"], "credit": abs(diff), "description": "فروق عملة (خسارة)"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "loss"})
                    else:
                        lines.append({"account_code": r["code"], "debit": abs(diff), "description": "فروق عملة (ربح)"})
                        lines.append({"account_code": request.fx_gain_account_code, "credit": abs(diff), "description": "إعادة تقييم عملة"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "gain"})

            if not lines:
                return ApiResponse(success=True, message="لا توجد فروق عملات لإعادة تقييمها",
                                   data={"as_of_date": request.as_of_date.isoformat(), "base_currency": base_code,
                                         "adjustments": [], "skipped": skipped})

        command = CreateJournalEntryCommand(
            date=request.as_of_date,
            description="إعادة تقييم فروق العملات الأجنبية",
            lines=lines,
            transaction_type="fx_revaluation",
            reference_id=f"FX-REVALUATION-{request.as_of_date.isoformat()}",
            created_by=current_user["username"],
        )
        command_bus = bootstrap.container.resolve("command_bus")
        created = command_bus.dispatch(command)
        entry_id = _extract_entry_id(created)

        with bootstrap.uow() as uow:
            uow.session.execute(
                text("UPDATE journal_entries SET transaction_type = 'fx_revaluation', reference = :ref "
                     "WHERE id::text = :eid"),
                {"ref": f"FX-REVALUATION-{request.as_of_date.isoformat()}", "eid": entry_id},
            )
            uow.commit()

        posted = False
        try:
            command_bus.dispatch(PostJournalEntryCommand(entry_id=entry_id, posted_by=current_user["username"]))
            posted = True
        except Exception:
            posted = False

        return ApiResponse(success=True, message="تم تنفيذ إعادة تقييم العملات بنجاح",
                           data={
                               "as_of_date": request.as_of_date.isoformat(),
                               "base_currency": base_code,
                               "entry_id": entry_id,
                               "is_posted": posted,
                               "adjustments": summary,
                               "skipped": skipped,
                               "total_fx_difference": float(sum(s["fx_difference"] for s in summary)),
                           })
    except Exception as e:
        logger.error(f"Error running FX revaluation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
