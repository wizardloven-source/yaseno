# core/application/financial_statements/converters.py
"""
Financial Statements Converters - دوال تحويل القوائم المالية
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal

from core.domain.financial_statements.entities import (
    FinancialStatement,
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
    EquityStatement,
)
from core.domain.financial_statements.value_objects import (
    StatementLine,
    StatementSection,
    CashFlowItem,
    AccountCategory,
    CashFlowType,
)

from .dtos import (
    StatementLineDTO,
    StatementSectionDTO,
    IncomeStatementDTO,
    BalanceSheetDTO,
    CashFlowItemDTO,
    CashFlowStatementDTO,
    EquityStatementDTO,
    TrialBalanceDTO,
)


# =============================================================================
# دوال مساعدة للتحويل الآمن
# =============================================================================

def _safe_decimal(value: Any) -> Decimal:
    """تحويل آمن إلى Decimal"""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except:
            return Decimal('0')
    if hasattr(value, 'amount'):
        return _safe_decimal(value.amount)
    return Decimal('0')


def _safe_str(value: Any) -> str:
    """تحويل آمن إلى str"""
    if value is None:
        return ""
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value)


def _safe_currency(value: Any) -> str:
    """استخراج العملة بشكل آمن"""
    if value is None:
        return "USD"
    if hasattr(value, 'currency'):
        return _safe_str(value.currency)
    if isinstance(value, str) and len(value) == 3:
        return value.upper()
    return "USD"


# =============================================================================
# تحويل الأسطر والأقسام
# =============================================================================

def line_to_dto(line: StatementLine) -> Optional[StatementLineDTO]:
    """تحويل StatementLine إلى DTO"""
    if not line:
        return None
    
    return StatementLineDTO(
        code=line.code,
        name=line.name,
        amount=_safe_decimal(line.amount),
        currency=_safe_currency(line.currency),
        level=line.level or 0,
        is_total=line.is_total or False,
        is_subtotal=line.is_subtotal or False,
        is_section_header=line.is_section_header or False,
        parent_id=_safe_str(line.parent_id) if hasattr(line, 'parent_id') else None
    )


def section_to_dto(section: StatementSection) -> Optional[StatementSectionDTO]:
    """تحويل StatementSection إلى DTO"""
    if not section:
        return None
    
    return StatementSectionDTO(
        id=_safe_str(section.id),
        name=section.name,
        category=section.category.value if hasattr(section.category, 'value') else _safe_str(section.category),
        lines=[line_to_dto(line) for line in (section.lines or []) if line],
        total=_safe_decimal(section.total),
        currency=_safe_currency(section.currency)
    )


def sections_to_dto_list(sections: List[StatementSection]) -> List[StatementSectionDTO]:
    """تحويل قائمة أقسام إلى DTOs"""
    if not sections:
        return []
    return [section_to_dto(s) for s in sections if s]


# =============================================================================
# تحويل CashFlowItem
# =============================================================================

def cash_flow_item_to_dto(item: CashFlowItem) -> Optional[CashFlowItemDTO]:
    """تحويل CashFlowItem إلى DTO"""
    if not item:
        return None
    
    return CashFlowItemDTO(
        code=item.code,
        name=item.name,
        amount=_safe_decimal(item.amount),
        currency=_safe_currency(item.currency),
        flow_type=item.flow_type.value if hasattr(item.flow_type, 'value') else _safe_str(item.flow_type)
    )


# =============================================================================
# تحويل القوائم المالية الرئيسية
# =============================================================================

def income_statement_to_dto(statement: IncomeStatement) -> Optional[IncomeStatementDTO]:
    """تحويل IncomeStatement إلى DTO"""
    if not statement:
        return None
    
    return IncomeStatementDTO(
        id=_safe_str(statement.id),
        period_start=statement.period_info.start_date,
        period_end=statement.period_info.end_date,
        currency=_safe_currency(statement.currency),
        generated_at=statement.generated_at,
        generated_by=_safe_str(statement.generated_by),
        
        revenue=_safe_decimal(statement.revenue),
        cogs=_safe_decimal(statement.cogs),
        gross_profit=_safe_decimal(statement.gross_profit),
        operating_expenses=_safe_decimal(statement.operating_expenses),
        operating_profit=_safe_decimal(statement.operating_profit),
        other_income=_safe_decimal(statement.other_income),
        other_expenses=_safe_decimal(statement.other_expenses),
        net_income_before_tax=_safe_decimal(statement.net_income_before_tax),
        income_tax=_safe_decimal(statement.income_tax),
        net_income=_safe_decimal(statement.net_income),
        
        gross_margin=statement.gross_margin,
        operating_margin=statement.operating_margin,
        net_margin=statement.net_margin,
        
        sections=sections_to_dto_list(statement.sections),
        
        revenue_breakdown=getattr(statement, 'revenue_breakdown', {}),
        cogs_breakdown=getattr(statement, 'cogs_breakdown', {}),
        operating_expenses_breakdown=getattr(statement, 'operating_expenses_breakdown', {}),
        other_income_breakdown=getattr(statement, 'other_income_breakdown', {}),
        other_expenses_breakdown=getattr(statement, 'other_expenses_breakdown', {}),
        income_tax_breakdown=getattr(statement, 'income_tax_breakdown', {}),
    )


def balance_sheet_to_dto(statement: BalanceSheet) -> Optional[BalanceSheetDTO]:
    """تحويل BalanceSheet إلى DTO"""
    if not statement:
        return None
    
    return BalanceSheetDTO(
        id=_safe_str(statement.id),
        as_of_date=statement.period_info.end_date,
        currency=_safe_currency(statement.currency),
        generated_at=statement.generated_at,
        generated_by=_safe_str(statement.generated_by),
        
        current_assets=_safe_decimal(statement.current_assets),
        fixed_assets=_safe_decimal(statement.fixed_assets),
        intangible_assets=_safe_decimal(statement.intangible_assets),
        other_assets=_safe_decimal(statement.other_assets),
        total_assets=_safe_decimal(statement.total_assets),
        
        current_liabilities=_safe_decimal(statement.current_liabilities),
        long_term_liabilities=_safe_decimal(statement.long_term_liabilities),
        total_liabilities=_safe_decimal(statement.total_liabilities),
        
        paid_in_capital=_safe_decimal(statement.paid_in_capital),
        retained_earnings=_safe_decimal(statement.retained_earnings),
        other_equity=_safe_decimal(getattr(statement, 'other_equity', Decimal('0'))),
        total_equity=_safe_decimal(statement.total_equity),
        
        working_capital=statement.working_capital,
        current_ratio=statement.current_ratio,
        quick_ratio=getattr(statement, 'quick_ratio', None),
        debt_to_equity=statement.debt_to_equity,
        debt_to_assets=getattr(statement, 'debt_to_assets', None),
        
        is_balanced=statement.is_balanced,
        difference=getattr(statement, 'difference', None),
        
        sections=sections_to_dto_list(statement.sections),
        
        current_assets_breakdown=getattr(statement, 'current_assets_breakdown', {}),
        fixed_assets_breakdown=getattr(statement, 'fixed_assets_breakdown', {}),
        intangible_assets_breakdown=getattr(statement, 'intangible_assets_breakdown', {}),
        other_assets_breakdown=getattr(statement, 'other_assets_breakdown', {}),
        current_liabilities_breakdown=getattr(statement, 'current_liabilities_breakdown', {}),
        long_term_liabilities_breakdown=getattr(statement, 'long_term_liabilities_breakdown', {}),
    )


def cash_flow_to_dto(statement: CashFlowStatement) -> Optional[CashFlowStatementDTO]:
    """تحويل CashFlowStatement إلى DTO"""
    if not statement:
        return None
    
    return CashFlowStatementDTO(
        id=_safe_str(statement.id),
        period_start=statement.period_info.start_date,
        period_end=statement.period_info.end_date,
        currency=_safe_currency(statement.currency),
        generated_at=statement.generated_at,
        generated_by=_safe_str(statement.generated_by),
        method=getattr(statement, 'method', 'indirect'),
        
        operating_cash_flow=_safe_decimal(statement.operating_cash_flow),
        operating_activities=[cash_flow_item_to_dto(item) for item in (statement.operating_activities or []) if item],
        
        investing_cash_flow=_safe_decimal(statement.investing_cash_flow),
        investing_activities=[cash_flow_item_to_dto(item) for item in (statement.investing_activities or []) if item],
        
        financing_cash_flow=_safe_decimal(statement.financing_cash_flow),
        financing_activities=[cash_flow_item_to_dto(item) for item in (statement.financing_activities or []) if item],
        
        net_cash_flow=_safe_decimal(statement.net_cash_flow),
        beginning_cash=_safe_decimal(statement.beginning_cash),
        ending_cash=_safe_decimal(statement.ending_cash),
        
        free_cash_flow=statement.free_cash_flow,
        cash_flow_to_debt=getattr(statement, 'cash_flow_to_debt', None),
        
        sections=sections_to_dto_list(statement.sections),
        
        operating_activities_breakdown=getattr(statement, 'operating_activities_breakdown', {}),
        investing_activities_breakdown=getattr(statement, 'investing_activities_breakdown', {}),
        financing_activities_breakdown=getattr(statement, 'financing_activities_breakdown', {}),
    )


def equity_statement_to_dto(statement) -> Optional[EquityStatementDTO]:
    """تحويل EquityStatement إلى DTO"""
    if not statement:
        return None
    
    return EquityStatementDTO(
        id=_safe_str(statement.id),
        period_start=statement.period_info.start_date,
        period_end=statement.period_info.end_date,
        currency=_safe_currency(statement.currency),
        generated_at=statement.generated_at,
        generated_by=_safe_str(statement.generated_by),
        
        beginning_capital=_safe_decimal(getattr(statement, 'beginning_capital', Decimal('0'))),
        additional_capital=_safe_decimal(getattr(statement, 'additional_capital', Decimal('0'))),
        ending_capital=_safe_decimal(getattr(statement, 'ending_capital', Decimal('0'))),
        
        beginning_retained_earnings=_safe_decimal(getattr(statement, 'beginning_retained_earnings', Decimal('0'))),
        net_income=_safe_decimal(getattr(statement, 'net_income', Decimal('0'))),
        dividends_paid=_safe_decimal(getattr(statement, 'dividends_paid', Decimal('0'))),
        ending_retained_earnings=_safe_decimal(getattr(statement, 'ending_retained_earnings', Decimal('0'))),
        
        other_equity_beginning=_safe_decimal(getattr(statement, 'other_equity_beginning', Decimal('0'))),
        other_equity_changes=_safe_decimal(getattr(statement, 'other_equity_changes', Decimal('0'))),
        other_equity_ending=_safe_decimal(getattr(statement, 'other_equity_ending', Decimal('0'))),
        
        total_beginning_equity=_safe_decimal(getattr(statement, 'total_beginning_equity', Decimal('0'))),
        total_ending_equity=_safe_decimal(getattr(statement, 'total_ending_equity', Decimal('0'))),
        
        sections=sections_to_dto_list(statement.sections),
    )


def statement_to_dto(statement: FinancialStatement):
    """
    تحويل أي قائمة مالية إلى DTO المناسب حسب نوعها
    """
    if not statement:
        return None
    
    if isinstance(statement, IncomeStatement):
        return income_statement_to_dto(statement)
    elif isinstance(statement, BalanceSheet):
        return balance_sheet_to_dto(statement)
    elif isinstance(statement, CashFlowStatement):
        return cash_flow_to_dto(statement)
    elif isinstance(statement, EquityStatement):
        return equity_statement_to_dto(statement)
    else:
        # Generic conversion
        return {
            'id': _safe_str(statement.id),
            'type': statement.statement_type.value if hasattr(statement.statement_type, 'value') else _safe_str(statement.statement_type),
            'period_start': statement.period_info.start_date,
            'period_end': statement.period_info.end_date,
            'currency': _safe_currency(statement.currency),
            'total': _safe_decimal(statement.total),
            'generated_at': statement.generated_at,
            'generated_by': _safe_str(statement.generated_by),
            'sections': sections_to_dto_list(statement.sections),
        }


# =============================================================================
# تحويل القوائم إلى قاموس (للتخزين والتصدير)
# =============================================================================

def statement_to_dict(statement: FinancialStatement) -> Dict[str, Any]:
    """
    تحويل أي قائمة مالية إلى قاموس (للتخزين والتصدير)
    """
    if not statement:
        return {}
    
    result = {
        'id': _safe_str(statement.id),
        'type': statement.statement_type.value if hasattr(statement.statement_type, 'value') else _safe_str(statement.statement_type),
        'period_start': statement.period_info.start_date.isoformat(),
        'period_end': statement.period_info.end_date.isoformat(),
        'period_name': statement.period_info.period_name,
        'fiscal_year': statement.period_info.fiscal_year,
        'currency': _safe_currency(statement.currency),
        'total': float(_safe_decimal(statement.total)),
        'generated_at': statement.generated_at.isoformat(),
        'generated_by': _safe_str(statement.generated_by),
        'version': statement.version,
    }
    
    # إضافة الأقسام
    if statement.sections:
        result['sections'] = []
        for section in statement.sections:
            result['sections'].append({
                'id': section.id,
                'name': section.name,
                'category': section.category.value if hasattr(section.category, 'value') else _safe_str(section.category),
                'total': float(_safe_decimal(section.total)),
                'currency': _safe_currency(section.currency),
                'lines': [
                    {
                        'code': line.code,
                        'name': line.name,
                        'amount': float(_safe_decimal(line.amount)),
                        'currency': _safe_currency(line.currency),
                        'level': line.level,
                        'is_total': line.is_total,
                        'is_subtotal': line.is_subtotal,
                    }
                    for line in (section.lines or []) if line
                ]
            })
    
    # إضافة حقول خاصة حسب نوع القائمة
    if isinstance(statement, IncomeStatement):
        result.update({
            'revenue': float(_safe_decimal(statement.revenue)),
            'cogs': float(_safe_decimal(statement.cogs)),
            'gross_profit': float(_safe_decimal(statement.gross_profit)),
            'operating_expenses': float(_safe_decimal(statement.operating_expenses)),
            'operating_profit': float(_safe_decimal(statement.operating_profit)),
            'other_income': float(_safe_decimal(statement.other_income)),
            'other_expenses': float(_safe_decimal(statement.other_expenses)),
            'net_income_before_tax': float(_safe_decimal(statement.net_income_before_tax)),
            'income_tax': float(_safe_decimal(statement.income_tax)),
            'net_income': float(_safe_decimal(statement.net_income)),
            'gross_margin': float(statement.gross_margin) if statement.gross_margin else None,
            'operating_margin': float(statement.operating_margin) if statement.operating_margin else None,
            'net_margin': float(statement.net_margin) if statement.net_margin else None,
        })
    
    elif isinstance(statement, BalanceSheet):
        result.update({
            'current_assets': float(_safe_decimal(statement.current_assets)),
            'fixed_assets': float(_safe_decimal(statement.fixed_assets)),
            'intangible_assets': float(_safe_decimal(statement.intangible_assets)),
            'other_assets': float(_safe_decimal(statement.other_assets)),
            'total_assets': float(_safe_decimal(statement.total_assets)),
            'current_liabilities': float(_safe_decimal(statement.current_liabilities)),
            'long_term_liabilities': float(_safe_decimal(statement.long_term_liabilities)),
            'total_liabilities': float(_safe_decimal(statement.total_liabilities)),
            'paid_in_capital': float(_safe_decimal(statement.paid_in_capital)),
            'retained_earnings': float(_safe_decimal(statement.retained_earnings)),
            'total_equity': float(_safe_decimal(statement.total_equity)),
            'is_balanced': statement.is_balanced,
            'working_capital': float(statement.working_capital) if statement.working_capital else None,
            'current_ratio': float(statement.current_ratio) if statement.current_ratio else None,
            'debt_to_equity': float(statement.debt_to_equity) if statement.debt_to_equity else None,
        })
    
    elif isinstance(statement, CashFlowStatement):
        result.update({
            'operating_cash_flow': float(_safe_decimal(statement.operating_cash_flow)),
            'investing_cash_flow': float(_safe_decimal(statement.investing_cash_flow)),
            'financing_cash_flow': float(_safe_decimal(statement.financing_cash_flow)),
            'net_cash_flow': float(_safe_decimal(statement.net_cash_flow)),
            'beginning_cash': float(_safe_decimal(statement.beginning_cash)),
            'ending_cash': float(_safe_decimal(statement.ending_cash)),
            'free_cash_flow': float(statement.free_cash_flow) if statement.free_cash_flow else None,
        })
    
    return result


# =============================================================================
# دوال إضافية للتحويل إلى قاموس (للمعالجات)
# =============================================================================

def income_statement_to_dict(statement: IncomeStatement) -> Dict[str, Any]:
    """
    تحويل قائمة الدخل إلى قاموس (للاستخدام في المعالجات والتقارير)
    
    Args:
        statement: كيان قائمة الدخل
    
    Returns:
        Dict[str, Any]: قاموس يحتوي على بيانات قائمة الدخل
    """
    if not statement:
        return {}
    
    return {
        'id': _safe_str(statement.id),
        'period_start': statement.period_info.start_date.isoformat() if statement.period_info.start_date else None,
        'period_end': statement.period_info.end_date.isoformat() if statement.period_info.end_date else None,
        'currency': _safe_currency(statement.currency),
        'generated_at': statement.generated_at.isoformat() if statement.generated_at else None,
        'generated_by': _safe_str(statement.generated_by),
        'revenue': float(_safe_decimal(statement.revenue)),
        'cogs': float(_safe_decimal(statement.cogs)),
        'gross_profit': float(_safe_decimal(statement.gross_profit)),
        'operating_expenses': float(_safe_decimal(statement.operating_expenses)),
        'operating_profit': float(_safe_decimal(statement.operating_profit)),
        'other_income': float(_safe_decimal(statement.other_income)),
        'other_expenses': float(_safe_decimal(statement.other_expenses)),
        'net_income_before_tax': float(_safe_decimal(statement.net_income_before_tax)),
        'income_tax': float(_safe_decimal(statement.income_tax)),
        'net_income': float(_safe_decimal(statement.net_income)),
        'gross_margin': float(statement.gross_margin) if statement.gross_margin else None,
        'operating_margin': float(statement.operating_margin) if statement.operating_margin else None,
        'net_margin': float(statement.net_margin) if statement.net_margin else None,
        'sections': [
            {
                'id': section.id,
                'name': section.name,
                'category': section.category.value if hasattr(section.category, 'value') else _safe_str(section.category),
                'total': float(_safe_decimal(section.total)),
                'currency': _safe_currency(section.currency),
                'lines': [
                    {
                        'code': line.code,
                        'name': line.name,
                        'amount': float(_safe_decimal(line.amount)),
                        'currency': _safe_currency(line.currency),
                        'level': line.level,
                        'is_total': line.is_total,
                        'is_subtotal': line.is_subtotal,
                    }
                    for line in (section.lines or []) if line
                ]
            }
            for section in (statement.sections or [])
        ],
        'revenue_breakdown': {
            k: float(v) for k, v in getattr(statement, 'revenue_breakdown', {}).items()
        },
        'cogs_breakdown': {
            k: float(v) for k, v in getattr(statement, 'cogs_breakdown', {}).items()
        },
        'operating_expenses_breakdown': {
            k: float(v) for k, v in getattr(statement, 'operating_expenses_breakdown', {}).items()
        },
        'version': statement.version,
    }


def balance_sheet_to_dict(statement: BalanceSheet) -> Dict[str, Any]:
    """
    تحويل الميزانية العمومية إلى قاموس (للاستخدام في المعالجات والتقارير)
    
    Args:
        statement: كيان الميزانية العمومية
    
    Returns:
        Dict[str, Any]: قاموس يحتوي على بيانات الميزانية العمومية
    """
    if not statement:
        return {}
    
    return {
        'id': _safe_str(statement.id),
        'as_of_date': statement.period_info.end_date.isoformat() if statement.period_info.end_date else None,
        'currency': _safe_currency(statement.currency),
        'generated_at': statement.generated_at.isoformat() if statement.generated_at else None,
        'generated_by': _safe_str(statement.generated_by),
        
        # الأصول
        'current_assets': float(_safe_decimal(statement.current_assets)),
        'fixed_assets': float(_safe_decimal(statement.fixed_assets)),
        'intangible_assets': float(_safe_decimal(statement.intangible_assets)),
        'other_assets': float(_safe_decimal(statement.other_assets)),
        'total_assets': float(_safe_decimal(statement.total_assets)),
        
        # الخصوم
        'current_liabilities': float(_safe_decimal(statement.current_liabilities)),
        'long_term_liabilities': float(_safe_decimal(statement.long_term_liabilities)),
        'total_liabilities': float(_safe_decimal(statement.total_liabilities)),
        
        # حقوق الملكية
        'paid_in_capital': float(_safe_decimal(statement.paid_in_capital)),
        'retained_earnings': float(_safe_decimal(statement.retained_earnings)),
        'other_equity': float(_safe_decimal(getattr(statement, 'other_equity', Decimal('0')))),
        'total_equity': float(_safe_decimal(statement.total_equity)),
        
        # المؤشرات المالية
        'working_capital': float(statement.working_capital) if statement.working_capital else None,
        'current_ratio': float(statement.current_ratio) if statement.current_ratio else None,
        'quick_ratio': float(getattr(statement, 'quick_ratio', 0)) if getattr(statement, 'quick_ratio', None) else None,
        'debt_to_equity': float(statement.debt_to_equity) if statement.debt_to_equity else None,
        'debt_to_assets': float(getattr(statement, 'debt_to_assets', 0)) if getattr(statement, 'debt_to_assets', None) else None,
        
        # حالة التوازن
        'is_balanced': statement.is_balanced,
        'difference': float(getattr(statement, 'difference', 0)) if getattr(statement, 'difference', None) else None,
        
        # الأقسام
        'sections': [
            {
                'id': section.id,
                'name': section.name,
                'category': section.category.value if hasattr(section.category, 'value') else _safe_str(section.category),
                'total': float(_safe_decimal(section.total)),
                'currency': _safe_currency(section.currency),
                'lines': [
                    {
                        'code': line.code,
                        'name': line.name,
                        'amount': float(_safe_decimal(line.amount)),
                        'currency': _safe_currency(line.currency),
                        'level': line.level,
                        'is_total': line.is_total,
                        'is_subtotal': line.is_subtotal,
                    }
                    for line in (section.lines or []) if line
                ]
            }
            for section in (statement.sections or [])
        ],
        
        # تفصيلات إضافية
        'current_assets_breakdown': {
            k: float(v) for k, v in getattr(statement, 'current_assets_breakdown', {}).items()
        },
        'fixed_assets_breakdown': {
            k: float(v) for k, v in getattr(statement, 'fixed_assets_breakdown', {}).items()
        },
        'current_liabilities_breakdown': {
            k: float(v) for k, v in getattr(statement, 'current_liabilities_breakdown', {}).items()
        },
        'version': statement.version,
    }


def cash_flow_to_dict(statement: CashFlowStatement) -> Dict[str, Any]:
    """
    تحويل قائمة التدفقات النقدية إلى قاموس
    
    Args:
        statement: كيان قائمة التدفقات النقدية
    
    Returns:
        Dict[str, Any]: قاموس يحتوي على بيانات قائمة التدفقات النقدية
    """
    if not statement:
        return {}
    
    return {
        'id': _safe_str(statement.id),
        'period_start': statement.period_info.start_date.isoformat() if statement.period_info.start_date else None,
        'period_end': statement.period_info.end_date.isoformat() if statement.period_info.end_date else None,
        'currency': _safe_currency(statement.currency),
        'generated_at': statement.generated_at.isoformat() if statement.generated_at else None,
        'generated_by': _safe_str(statement.generated_by),
        'method': getattr(statement, 'method', 'indirect'),
        'operating_cash_flow': float(_safe_decimal(statement.operating_cash_flow)),
        'investing_cash_flow': float(_safe_decimal(statement.investing_cash_flow)),
        'financing_cash_flow': float(_safe_decimal(statement.financing_cash_flow)),
        'net_cash_flow': float(_safe_decimal(statement.net_cash_flow)),
        'beginning_cash': float(_safe_decimal(statement.beginning_cash)),
        'ending_cash': float(_safe_decimal(statement.ending_cash)),
        'free_cash_flow': float(statement.free_cash_flow) if statement.free_cash_flow else None,
        'cash_flow_to_debt': float(getattr(statement, 'cash_flow_to_debt', 0)) if getattr(statement, 'cash_flow_to_debt', None) else None,
        'sections': sections_to_dto_list(statement.sections),
        'version': statement.version,
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # تحويل الأسطر والأقسام
    'line_to_dto',
    'section_to_dto',
    'sections_to_dto_list',
    
    # تحويل القوائم المالية
    'income_statement_to_dto',
    'balance_sheet_to_dto',
    'cash_flow_to_dto',
    'equity_statement_to_dto',
    'statement_to_dto',
    
    # تحويل إلى قاموس (للتخزين والتصدير)
    'statement_to_dict',
    
    # دوال إضافية للتحويل إلى قاموس (للمعالجات)
    'income_statement_to_dict',
    'balance_sheet_to_dict',
    'cash_flow_to_dict',
    
    # دوال مساعدة
    '_safe_decimal',
    '_safe_str',
    '_safe_currency',
]