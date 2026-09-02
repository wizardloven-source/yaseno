# core/application/invoicing/converters.py
"""
Converters - دوال تحويل بين Domain Entities و DTOs

هذا الملف يحتوي على دوال التحويل المشتركة التي تستخدمها جميع Handlers
لمنع الاستيرادات الدائرية (Circular Imports)

✅ محدث: دعم جميع حقول الضرائب
✅ محدث: دعم التفاصيل الضريبية لكل سطر
✅ محدث: دعم العملات المتعددة في الضرائب
✅ محدث: دعم التحويل الآمن للقيم
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal

from core.domain.invoicing.entities import Invoice, InvoiceLine
from core.domain.invoicing.value_objects import InvoiceStatus, PaymentType
from core.domain.shared.value_objects import Money, AccountCode
from core.domain.accounting.entities import JournalLine

from .dtos import InvoiceDTO, InvoiceLineDTO


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


def _safe_breakdown(breakdown: Dict[str, Any]) -> Dict[str, Decimal]:
    """تحويل تفصيل الضرائب بشكل آمن"""
    result = {}
    for key, value in (breakdown or {}).items():
        if isinstance(value, Money):
            result[_safe_str(key)] = value.amount
        elif hasattr(value, 'amount'):
            result[_safe_str(key)] = _safe_decimal(value.amount)
        else:
            result[_safe_str(key)] = _safe_decimal(value)
    return result


# =============================================================================
# دوال التحويل الرئيسية
# =============================================================================

def invoice_to_dto(invoice: Invoice) -> InvoiceDTO:
    """
    تحويل كيان الفاتورة (Domain Entity) إلى DTO
    ✅ محدث: دعم جميع حقول الضرائب
    
    Args:
        invoice: كيان الفاتورة من Domain Layer
    
    Returns:
        InvoiceDTO: كائن نقل البيانات للفاتورة
    """
    if not invoice:
        return None
    
    # تحويل تفصيل الضرائب
    tax_breakdown = {}
    for key, value in invoice.tax_breakdown.items():
        if isinstance(value, Money):
            tax_breakdown[_safe_str(key)] = value.amount
        else:
            tax_breakdown[_safe_str(key)] = _safe_decimal(value)
    
    return InvoiceDTO(
        # المعلومات الأساسية
        id=_safe_str(invoice.id),
        number=_safe_str(invoice.number) if invoice.number else None,
        date=invoice.date,
        
        # أطراف المعاملة
        customer_id=_safe_str(invoice.customer_id),
        customer_name=_safe_str(invoice.customer_name),
        site_id=_safe_str(invoice.site_id) if invoice.site_id else None,
        site_name=_safe_str(invoice.site_name) if invoice.site_name else None,
        
        # المعلومات المالية
        currency=_safe_currency(invoice.currency),
        payment_currency=getattr(invoice, 'payment_currency', 'USD'),
        payment_type=invoice.payment_type.value if invoice.payment_type else "cash",
        fund_id=_safe_str(invoice.fund_id) if invoice.fund_id else None,
        
        # حالة الفاتورة
        status=invoice.status.value if invoice.status else "draft",
        
        # المبالغ
        subtotal=_safe_decimal(invoice.subtotal),
        tax_amount=_safe_decimal(invoice.tax_amount),
        total=_safe_decimal(invoice.total),
        
        # ✅ حقول الضرائب الإضافية
        tax_breakdown=tax_breakdown,
        tax_rates_applied=invoice.tax_rates_applied or [],
        is_tax_inclusive=getattr(invoice, 'is_tax_inclusive', False),
        total_with_tax=_safe_decimal(invoice.total_with_tax) if hasattr(invoice, 'total_with_tax') else _safe_decimal(invoice.total),
        
        # البنود
        notes=_safe_str(invoice.notes),
        lines=[line_to_dto(line) for line in invoice.lines],
        
        # الربط مع المحاسبة
        journal_entry_id=_safe_str(invoice.journal_entry_id) if invoice.journal_entry_id else None,
        
        # بيانات التدقيق
        created_at=invoice.created_at,
        created_by=_safe_str(invoice.created_by),
        posted_at=invoice.posted_at,
        posted_by=_safe_str(invoice.posted_by) if invoice.posted_by else None
    )


def line_to_dto(line: InvoiceLine) -> InvoiceLineDTO:
    """
    تحويل سطر الفاتورة (Domain Entity) إلى DTO
    ✅ محدث: دعم جميع حقول الضرائب
    
    Args:
        line: كيان سطر الفاتورة من Domain Layer
    
    Returns:
        InvoiceLineDTO: كائن نقل البيانات لسطر الفاتورة
    """
    if not line:
        return None
    
    return InvoiceLineDTO(
        # المعلومات الأساسية
        line_id=_safe_str(line.line_id),
        product_code=_safe_str(line.product_code),
        product_name=_safe_str(line.product_name),
        
        # الكميات والأسعار
        quantity=_safe_decimal(line.quantity),
        unit_price=_safe_decimal(line.unit_price),
        total=_safe_decimal(line.total),
        currency=_safe_currency(line.unit_price),
        
        # ✅ حقول الضرائب للسطر
        tax_rate=float(line.tax_rate) if hasattr(line, 'tax_rate') else 0.0,
        tax_amount=_safe_decimal(line.tax_amount) if hasattr(line, 'tax_amount') else Decimal('0'),
        tax_breakdown=_safe_breakdown(line.tax_breakdown) if hasattr(line, 'tax_breakdown') else {},
        is_tax_inclusive=getattr(line, 'is_tax_inclusive', False),
        total_with_tax=_safe_decimal(line.total_with_tax) if hasattr(line, 'total_with_tax') else _safe_decimal(line.total),
        
        # ملاحظات
        notes=_safe_str(line.notes)
    )


def lines_to_journal_lines(lines_data: List[Dict[str, Any]]) -> List[JournalLine]:
    """
    تحويل بيانات الأسطر (من API/Command) إلى كائنات JournalLine
    ✅ محدث: دعم القيم الاختيارية
    
    Args:
        lines_data: قائمة من القواميس تحتوي على account_code, debit, credit, currency
    
    Returns:
        List[JournalLine]: قائمة كائنات JournalLine للاستخدام في المحاسبة
    """
    journal_lines = []
    for line_data in lines_data:
        journal_lines.append(
            JournalLine(
                account_code=AccountCode(_safe_str(line_data.get("account_code"))),
                debit=Money(
                    _safe_decimal(line_data.get("debit", 0)), 
                    _safe_currency(line_data.get("currency", "USD"))
                ),
                credit=Money(
                    _safe_decimal(line_data.get("credit", 0)), 
                    _safe_currency(line_data.get("currency", "USD"))
                )
            )
        )
    return journal_lines


def dto_to_invoice(dto: InvoiceDTO) -> Dict[str, Any]:
    """
    تحويل InvoiceDTO إلى قاموس (للاستخدام في Service Layer)
    ✅ محدث: دعم جميع حقول الضرائب
    
    Args:
        dto: كائن نقل البيانات للفاتورة
    
    Returns:
        Dict: قاموس يحتوي على بيانات الفاتورة
    """
    if not dto:
        return None
    
    return {
        # المعلومات الأساسية
        'id': _safe_str(dto.id),
        'number': _safe_str(dto.number) if dto.number else None,
        'date': dto.date,
        
        # أطراف المعاملة
        'customer_id': _safe_str(dto.customer_id),
        'customer_name': _safe_str(dto.customer_name),
        'site_id': _safe_str(dto.site_id) if dto.site_id else None,
        'site_name': _safe_str(dto.site_name) if dto.site_name else None,
        
        # المعلومات المالية
        'currency': _safe_currency(dto.currency),
        'payment_currency': getattr(dto, 'payment_currency', 'USD'),
        'payment_type': _safe_str(dto.payment_type),
        'fund_id': _safe_str(dto.fund_id) if dto.fund_id else None,
        
        # حالة الفاتورة
        'status': _safe_str(dto.status),
        
        # المبالغ
        'subtotal': float(_safe_decimal(dto.subtotal)),
        'tax_amount': float(_safe_decimal(dto.tax_amount)),
        'total': float(_safe_decimal(dto.total)),
        
        # ✅ حقول الضرائب الإضافية
        'tax_breakdown': {k: float(v) for k, v in dto.tax_breakdown.items()} if dto.tax_breakdown else {},
        'tax_rates_applied': dto.tax_rates_applied or [],
        'is_tax_inclusive': getattr(dto, 'is_tax_inclusive', False),
        'total_with_tax': float(_safe_decimal(dto.total_with_tax)) if hasattr(dto, 'total_with_tax') else float(_safe_decimal(dto.total)),
        
        # البنود
        'notes': _safe_str(dto.notes),
        'lines': [
            {
                'line_id': _safe_str(line.line_id),
                'product_code': _safe_str(line.product_code),
                'product_name': _safe_str(line.product_name),
                'quantity': float(_safe_decimal(line.quantity)),
                'unit_price': float(_safe_decimal(line.unit_price)),
                'total': float(_safe_decimal(line.total)),
                'currency': _safe_currency(line.currency),
                'notes': _safe_str(line.notes),
                # ✅ حقول الضرائب للسطر
                'tax_rate': float(line.tax_rate) if hasattr(line, 'tax_rate') else 0.0,
                'tax_amount': float(_safe_decimal(line.tax_amount)) if hasattr(line, 'tax_amount') else 0.0,
                'tax_breakdown': {k: float(v) for k, v in line.tax_breakdown.items()} if hasattr(line, 'tax_breakdown') else {},
                'is_tax_inclusive': getattr(line, 'is_tax_inclusive', False),
                'total_with_tax': float(_safe_decimal(line.total_with_tax)) if hasattr(line, 'total_with_tax') else float(_safe_decimal(line.total))
            }
            for line in dto.lines
        ],
        
        # الربط مع المحاسبة
        'journal_entry_id': _safe_str(dto.journal_entry_id) if dto.journal_entry_id else None,
        
        # بيانات التدقيق
        'created_at': dto.created_at,
        'created_by': _safe_str(dto.created_by),
        'posted_at': dto.posted_at,
        'posted_by': _safe_str(dto.posted_by) if dto.posted_by else None
    }


def invoice_to_dict(invoice: Invoice) -> Dict[str, Any]:
    """
    تحويل كيان الفاتورة إلى قاموس (للاستخدام في التقارير والتصدير)
    ✅ محدث: دعم جميع حقول الضرائب
    
    Args:
        invoice: كيان الفاتورة من Domain Layer
    
    Returns:
        Dict: قاموس يحتوي على جميع بيانات الفاتورة
    """
    if not invoice:
        return None
    
    return {
        'id': _safe_str(invoice.id),
        'number': _safe_str(invoice.number) if invoice.number else None,
        'date': invoice.date.isoformat() if invoice.date else None,
        'customer_id': _safe_str(invoice.customer_id),
        'customer_name': _safe_str(invoice.customer_name),
        'site_id': _safe_str(invoice.site_id) if invoice.site_id else None,
        'site_name': _safe_str(invoice.site_name) if invoice.site_name else None,
        'currency': _safe_currency(invoice.currency),
        'payment_currency': getattr(invoice, 'payment_currency', 'USD'),
        'payment_type': invoice.payment_type.value if invoice.payment_type else "cash",
        'fund_id': _safe_str(invoice.fund_id) if invoice.fund_id else None,
        'status': invoice.status.value if invoice.status else "draft",
        'subtotal': float(_safe_decimal(invoice.subtotal)),
        'tax_amount': float(_safe_decimal(invoice.tax_amount)),
        'tax_breakdown': {k: float(v.amount) if isinstance(v, Money) else float(v) for k, v in invoice.tax_breakdown.items()},
        'tax_rates_applied': invoice.tax_rates_applied or [],
        'is_tax_inclusive': getattr(invoice, 'is_tax_inclusive', False),
        'total': float(_safe_decimal(invoice.total)),
        'total_with_tax': float(_safe_decimal(invoice.total_with_tax)) if hasattr(invoice, 'total_with_tax') else float(_safe_decimal(invoice.total)),
        'notes': _safe_str(invoice.notes),
        'lines': [line_to_dict(line) for line in invoice.lines],
        'journal_entry_id': _safe_str(invoice.journal_entry_id) if invoice.journal_entry_id else None,
        'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
        'created_by': _safe_str(invoice.created_by),
        'posted_at': invoice.posted_at.isoformat() if invoice.posted_at else None,
        'posted_by': _safe_str(invoice.posted_by) if invoice.posted_by else None,
        'version': invoice.version
    }


def line_to_dict(line: InvoiceLine) -> Dict[str, Any]:
    """
    تحويل سطر الفاتورة إلى قاموس (للاستخدام في التقارير والتصدير)
    ✅ محدث: دعم جميع حقول الضرائب
    
    Args:
        line: كيان سطر الفاتورة من Domain Layer
    
    Returns:
        Dict: قاموس يحتوي على بيانات السطر
    """
    if not line:
        return None
    
    return {
        'line_id': _safe_str(line.line_id),
        'product_code': _safe_str(line.product_code),
        'product_name': _safe_str(line.product_name),
        'quantity': float(_safe_decimal(line.quantity)),
        'unit_price': float(_safe_decimal(line.unit_price)),
        'total': float(_safe_decimal(line.total)),
        'currency': _safe_currency(line.unit_price),
        'tax_rate': float(line.tax_rate) if hasattr(line, 'tax_rate') else 0.0,
        'tax_amount': float(_safe_decimal(line.tax_amount)) if hasattr(line, 'tax_amount') else 0.0,
        'tax_breakdown': {k: float(v) for k, v in line.tax_breakdown.items()} if hasattr(line, 'tax_breakdown') else {},
        'is_tax_inclusive': getattr(line, 'is_tax_inclusive', False),
        'total_with_tax': float(_safe_decimal(line.total_with_tax)) if hasattr(line, 'total_with_tax') else float(_safe_decimal(line.total)),
        'notes': _safe_str(line.notes)
    }


def invoices_to_dto_list(invoices: List[Invoice]) -> List[InvoiceDTO]:
    """
    تحويل قائمة فواتير إلى قائمة DTOs
    
    Args:
        invoices: قائمة كيانات الفواتير
    
    Returns:
        List[InvoiceDTO]: قائمة كائنات نقل البيانات
    """
    if not invoices:
        return []
    return [invoice_to_dto(inv) for inv in invoices if inv]


def dto_list_to_dict_list(dtos: List[InvoiceDTO]) -> List[Dict[str, Any]]:
    """
    تحويل قائمة DTOs إلى قائمة قواميس
    
    Args:
        dtos: قائمة كائنات نقل البيانات
    
    Returns:
        List[Dict]: قائمة قواميس
    """
    if not dtos:
        return []
    return [dto_to_invoice(dto) for dto in dtos if dto]


# =============================================================================
# تصدير جميع الدوال
# =============================================================================

__all__ = [
    # دوال التحويل الأساسية
    "invoice_to_dto",
    "line_to_dto",
    "dto_to_invoice",
    
    # دوال القوائم
    "invoices_to_dto_list",
    "dto_list_to_dict_list",
    
    # دوال القواميس
    "invoice_to_dict",
    "line_to_dict",
    
    # دوال التحويل المحاسبي
    "lines_to_journal_lines",
    
    # دوال مساعدة
    "_safe_decimal",
    "_safe_str",
    "_safe_currency",
    "_safe_breakdown",
]