# core/infrastructure/db/postgres/financial_statement_repository.py
"""
Financial Statements Repository - مستودع القوائم المالية
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, and_, or_, func, desc, delete
from sqlalchemy.orm import Session, selectinload

from core.domain.financial_statements.entities import (
    FinancialStatement, IncomeStatement, BalanceSheet, CashFlowStatement
)
from core.domain.financial_statements.value_objects import (
    StatementId, StatementType, StatementPeriodInfo, StatementPeriod,
    StatementLine, StatementSection, AccountCategory, CashFlowType
)
from core.domain.financial_statements.interfaces import IFinancialStatementRepository

from ..models.financial_statement_model import (
    FinancialStatementModel, FinancialStatementLineModel
)


# =============================================================================
# دوال التحويل
# =============================================================================

def _model_to_domain(model: FinancialStatementModel) -> FinancialStatement:
    """تحويل ORM Model إلى Domain Entity"""
    if not model:
        return None

    period_info = StatementPeriodInfo(
        period_type=StatementPeriod(model.period_type),
        start_date=model.period_start,
        end_date=model.period_end,
        period_name=model.period_name,
        fiscal_year=model.fiscal_year,
        is_comparative=model.is_comparative,
        previous_period_start=model.previous_period_start,
        previous_period_end=model.previous_period_end
    )

    # إنشاء القائمة حسب النوع
    statement_type = StatementType(model.statement_type)
    totals = model.totals or {}

    if statement_type == StatementType.INCOME_STATEMENT:
        statement = IncomeStatement(
            id=StatementId(str(model.id)),
            period_info=period_info,
            currency=model.currency
        )
        statement.revenue = Decimal(str(totals.get('revenue', 0)))
        statement.cogs = Decimal(str(totals.get('cogs', 0)))
        statement.gross_profit = Decimal(str(totals.get('gross_profit', 0)))
        statement.operating_expenses = Decimal(str(totals.get('operating_expenses', 0)))
        statement.operating_profit = Decimal(str(totals.get('operating_profit', 0)))
        statement.other_income = Decimal(str(totals.get('other_income', 0)))
        statement.other_expenses = Decimal(str(totals.get('other_expenses', 0)))
        statement.net_income_before_tax = Decimal(str(totals.get('net_income_before_tax', 0)))
        statement.income_tax = Decimal(str(totals.get('income_tax', 0)))
        statement.net_income = Decimal(str(totals.get('net_income', 0)))
        statement.total = statement.net_income

    elif statement_type == StatementType.BALANCE_SHEET:
        statement = BalanceSheet(
            id=StatementId(str(model.id)),
            period_info=period_info,
            currency=model.currency
        )
        statement.current_assets = Decimal(str(totals.get('current_assets', 0)))
        statement.fixed_assets = Decimal(str(totals.get('fixed_assets', 0)))
        statement.intangible_assets = Decimal(str(totals.get('intangible_assets', 0)))
        statement.other_assets = Decimal(str(totals.get('other_assets', 0)))
        statement.total_assets = Decimal(str(totals.get('total_assets', 0)))
        statement.current_liabilities = Decimal(str(totals.get('current_liabilities', 0)))
        statement.long_term_liabilities = Decimal(str(totals.get('long_term_liabilities', 0)))
        statement.total_liabilities = Decimal(str(totals.get('total_liabilities', 0)))
        statement.paid_in_capital = Decimal(str(totals.get('paid_in_capital', 0)))
        statement.retained_earnings = Decimal(str(totals.get('retained_earnings', 0)))
        statement.total_equity = Decimal(str(totals.get('total_equity', 0)))
        statement.total = statement.total_assets

    elif statement_type == StatementType.CASH_FLOW:
        statement = CashFlowStatement(
            id=StatementId(str(model.id)),
            period_info=period_info,
            currency=model.currency
        )
        statement.operating_cash_flow = Decimal(str(totals.get('operating_cash_flow', 0)))
        statement.investing_cash_flow = Decimal(str(totals.get('investing_cash_flow', 0)))
        statement.financing_cash_flow = Decimal(str(totals.get('financing_cash_flow', 0)))
        statement.net_cash_flow = Decimal(str(totals.get('net_cash_flow', 0)))
        statement.beginning_cash = Decimal(str(totals.get('beginning_cash', 0)))
        statement.ending_cash = Decimal(str(totals.get('ending_cash', 0)))
        statement.total = statement.net_cash_flow

    else:
        statement = FinancialStatement(
            id=StatementId(str(model.id)),
            statement_type=statement_type,
            period_info=period_info,
            currency=model.currency,
            total=Decimal(str(totals.get('total', 0)))
        )

    statement.generated_at = model.generated_at
    statement.generated_by = model.generated_by
    statement.version = model.version

    # بناء الأقسام من البيانات
    data = model.data or {}
    sections = []
    for section_data in data.get('sections', []):
        lines = []
        for line_data in section_data.get('lines', []):
            lines.append(StatementLine(
                id=line_data.get('id', ''),
                code=line_data.get('code', ''),
                name=line_data.get('name', ''),
                amount=Decimal(str(line_data.get('amount', 0))),
                currency=line_data.get('currency', 'USD'),
                category=AccountCategory(line_data.get('category', 'other_expense')),
                level=line_data.get('level', 0),
                parent_id=line_data.get('parent_id'),
                is_total=line_data.get('is_total', False),
                is_subtotal=line_data.get('is_subtotal', False),
                is_section_header=line_data.get('is_section_header', False)
            ))
        sections.append(StatementSection(
            id=section_data.get('id', ''),
            name=section_data.get('name', ''),
            category=AccountCategory(section_data.get('category', 'other_expense')),
            lines=lines,
            total=Decimal(str(section_data.get('total', 0))),
            currency=section_data.get('currency', 'USD')
        ))
    statement.sections = sections

    return statement


def _domain_to_model(statement: FinancialStatement) -> FinancialStatementModel:
    """تحويل Domain Entity إلى ORM Model"""
    model = FinancialStatementModel(
        id=UUID(str(statement.id)),
        statement_type=statement.statement_type.value,
        period_start=statement.period_info.start_date,
        period_end=statement.period_info.end_date,
        period_name=statement.period_info.period_name,
        fiscal_year=statement.period_info.fiscal_year,
        period_type=statement.period_info.period_type.value,
        currency=statement.currency,
        is_comparative=statement.period_info.is_comparative,
        previous_period_start=statement.period_info.previous_period_start,
        previous_period_end=statement.period_info.previous_period_end,
        generated_at=statement.generated_at,
        generated_by=statement.generated_by,
        version=statement.version
    )

    # تعيين الإجماليات حسب النوع
    totals = {}
    if isinstance(statement, IncomeStatement):
        totals.update({
            'revenue': float(statement.revenue),
            'cogs': float(statement.cogs),
            'gross_profit': float(statement.gross_profit),
            'operating_expenses': float(statement.operating_expenses),
            'operating_profit': float(statement.operating_profit),
            'other_income': float(statement.other_income),
            'other_expenses': float(statement.other_expenses),
            'net_income_before_tax': float(statement.net_income_before_tax),
            'income_tax': float(statement.income_tax),
            'net_income': float(statement.net_income),
            'total': float(statement.total)
        })
    elif isinstance(statement, BalanceSheet):
        totals.update({
            'current_assets': float(statement.current_assets),
            'fixed_assets': float(statement.fixed_assets),
            'intangible_assets': float(statement.intangible_assets),
            'other_assets': float(statement.other_assets),
            'total_assets': float(statement.total_assets),
            'current_liabilities': float(statement.current_liabilities),
            'long_term_liabilities': float(statement.long_term_liabilities),
            'total_liabilities': float(statement.total_liabilities),
            'paid_in_capital': float(statement.paid_in_capital),
            'retained_earnings': float(statement.retained_earnings),
            'total_equity': float(statement.total_equity),
            'total': float(statement.total)
        })
    elif isinstance(statement, CashFlowStatement):
        totals.update({
            'operating_cash_flow': float(statement.operating_cash_flow),
            'investing_cash_flow': float(statement.investing_cash_flow),
            'financing_cash_flow': float(statement.financing_cash_flow),
            'net_cash_flow': float(statement.net_cash_flow),
            'beginning_cash': float(statement.beginning_cash),
            'ending_cash': float(statement.ending_cash),
            'total': float(statement.total)
        })
    else:
        totals['total'] = float(statement.total)

    model.totals = totals

    # بناء البيانات الكاملة
    data = {'sections': []}
    for section in statement.sections:
        section_data = {
            'id': section.id,
            'name': section.name,
            'category': section.category.value,
            'total': float(section.total),
            'currency': section.currency,
            'lines': []
        }
        for line in section.lines:
            section_data['lines'].append({
                'id': line.id,
                'code': line.code,
                'name': line.name,
                'amount': float(line.amount),
                'currency': line.currency,
                'category': line.category.value,
                'level': line.level,
                'parent_id': line.parent_id,
                'is_total': line.is_total,
                'is_subtotal': line.is_subtotal,
                'is_section_header': line.is_section_header
            })
        data['sections'].append(section_data)

    model.data = data

    return model


# =============================================================================
# Repository
# =============================================================================

class PostgresFinancialStatementRepository(IFinancialStatementRepository):
    """تطبيق PostgreSQL لمستودع القوائم المالية"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, statement: FinancialStatement) -> None:
        """حفظ القائمة المالية (مع تحديث تلقائي لنفس الفترة)"""
        existing = self._session.execute(
            select(FinancialStatementModel).where(
                FinancialStatementModel.statement_type == statement.statement_type.value,
                FinancialStatementModel.period_start == statement.period_info.start_date,
                FinancialStatementModel.period_end == statement.period_info.end_date,
                FinancialStatementModel.currency == statement.currency
            )
        ).scalar_one_or_none()

        if existing:
            # تحديث
            model = _domain_to_model(statement)
            model.id = existing.id
            self._session.merge(model)
            statement.id = StatementId(str(existing.id))
        else:
            # إنشاء جديد
            model = _domain_to_model(statement)
            self._session.add(model)

        self._session.flush()
        statement.version += 1

    def get_by_id(self, statement_id: StatementId) -> Optional[FinancialStatement]:
        """الحصول على قائمة مالية بواسطة المعرف"""
        model = self._session.execute(
            select(FinancialStatementModel).where(
                FinancialStatementModel.id == UUID(str(statement_id))
            )
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain(model)

    def get_by_type_and_period(
        self,
        statement_type: StatementType,
        period_info: StatementPeriodInfo
    ) -> Optional[FinancialStatement]:
        """الحصول على قائمة مالية حسب النوع والفترة"""
        model = self._session.execute(
            select(FinancialStatementModel).where(
                and_(
                    FinancialStatementModel.statement_type == statement_type.value,
                    FinancialStatementModel.period_start == period_info.start_date,
                    FinancialStatementModel.period_end == period_info.end_date,
                    FinancialStatementModel.currency == period_info.fiscal_year
                )
            )
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain(model)

    def list_by_type(
        self,
        statement_type: StatementType,
        limit: int = 100,
        offset: int = 0
    ) -> List[FinancialStatement]:
        """قائمة القوائم المالية حسب النوع"""
        models = self._session.execute(
            select(FinancialStatementModel)
            .where(FinancialStatementModel.statement_type == statement_type.value)
            .order_by(desc(FinancialStatementModel.generated_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_period(
        self,
        start_date: date,
        end_date: date,
        limit: int = 100
    ) -> List[FinancialStatement]:
        """قائمة القوائم المالية في نطاق زمني"""
        models = self._session.execute(
            select(FinancialStatementModel)
            .where(
                and_(
                    FinancialStatementModel.period_start >= start_date,
                    FinancialStatementModel.period_end <= end_date
                )
            )
            .order_by(desc(FinancialStatementModel.generated_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def delete(self, statement_id: StatementId) -> bool:
        """حذف قائمة مالية"""
        result = self._session.execute(
            delete(FinancialStatementModel).where(
                FinancialStatementModel.id == UUID(str(statement_id))
            )
        )
        self._session.flush()
        return result.rowcount > 0

    def get_latest_by_type(self, statement_type: StatementType) -> Optional[FinancialStatement]:
        """الحصول على أحدث قائمة مالية حسب النوع"""
        model = self._session.execute(
            select(FinancialStatementModel)
            .where(FinancialStatementModel.statement_type == statement_type.value)
            .order_by(desc(FinancialStatementModel.generated_at))
            .limit(1)
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain(model)

    def get_by_fiscal_year(
        self,
        statement_type: StatementType,
        fiscal_year: int
    ) -> List[FinancialStatement]:
        """الحصول على القوائم المالية لسنة مالية محددة"""
        models = self._session.execute(
            select(FinancialStatementModel)
            .where(
                and_(
                    FinancialStatementModel.statement_type == statement_type.value,
                    FinancialStatementModel.fiscal_year == fiscal_year
                )
            )
            .order_by(FinancialStatementModel.period_start)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]