# core/application/funds/converters.py
"""
Converters for Funds - تحويل بين Domain Entities و DTOs
✅ مصحح: دعم التحويل الآمن من Money إلى float
✅ مصحح: دعم جميع الحقول من نوع Money
✅ مصحح: دعم القيم None
✅ مصحح: التعامل مع الكائنات التي لها خاصية value أو id
"""

from decimal import Decimal
from typing import List, Optional, Union, Any

from core.domain.funds.entities import Fund, FundTransaction, FundTransfer
from core.domain.funds.value_objects import FundId, FundCode, FundType, TransactionType, FundStatus, Money
from .dtos import FundDTO, FundMovementDTO


# تعريف FundMovement كـ Alias لـ FundTransaction للتوافق
FundMovement = FundTransaction
MovementType = TransactionType  # Alias للتوافق


# =============================================================================
# دوال مساعدة للتحويل الآمن
# =============================================================================

def safe_get_value(obj: Any) -> Any:
    """
    استخراج القيمة من كائن بأمان
    
    يدعم:
        - كائنات لها خاصية value (مثل FundId, FundCode, Enum)
        - كائنات لها خاصية id
        - النصوص العادية
        - None
    
    Args:
        obj: الكائن المراد استخراج قيمته
    
    Returns:
        Any: القيمة المستخرجة أو النص الأصلي
    """
    if obj is None:
        return None
    
    # ✅ إذا كان له خاصية value
    if hasattr(obj, 'value'):
        return obj.value
    
    # ✅ إذا كان له خاصية id
    if hasattr(obj, 'id'):
        return obj.id
    
    # ✅ إذا كان نصاً أو رقماً
    if isinstance(obj, (str, int, float)):
        return obj
    
    return str(obj)


def safe_str(obj: Any) -> str:
    """
    تحويل آمن إلى str
    
    Args:
        obj: الكائن المراد تحويله
    
    Returns:
        str: النص الناتج
    """
    if obj is None:
        return ""
    
    # ✅ استخراج القيمة أولاً
    value = safe_get_value(obj)
    
    if value is None:
        return ""
    
    return str(value)


def safe_money_to_float(value: Union[Money, Decimal, float, int, str, None]) -> float:
    """
    تحويل آمن لأي قيمة إلى float
    
    يدعم:
        - Money: يستخرج amount
        - Decimal: يحول إلى float
        - int, float: يعيد القيمة كما هي
        - str: يحاول التحويل
        - None: يعيد 0.0
    
    Args:
        value: القيمة المراد تحويلها
    
    Returns:
        float: القيمة كرقم عشري
    """
    if value is None:
        return 0.0
    
    # ✅ إذا كان Money (له خاصية amount)
    if hasattr(value, 'amount'):
        try:
            return float(value.amount)
        except (TypeError, ValueError):
            return 0.0
    
    # ✅ إذا كان Decimal
    if isinstance(value, Decimal):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    # ✅ إذا كان رقماً
    if isinstance(value, (int, float)):
        return float(value)
    
    # ✅ إذا كان نصاً
    if isinstance(value, str):
        try:
            # إزالة الفواصل والمسافات
            cleaned = value.replace(',', '').replace(' ', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    return 0.0


def safe_decimal_to_float(value: Union[Decimal, float, int, str, None]) -> float:
    """
    تحويل آمن من Decimal إلى float
    
    Args:
        value: القيمة المراد تحويلها
    
    Returns:
        float: القيمة كرقم عشري
    """
    if value is None:
        return 0.0
    
    if isinstance(value, Decimal):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        try:
            cleaned = value.replace(',', '').replace(' ', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    return 0.0


# =============================================================================
# دوال التحويل الرئيسية
# =============================================================================

def movement_to_dto(movement: FundMovement) -> Optional[FundMovementDTO]:
    """
    تحويل حركة صندوق إلى DTO
    
    Args:
        movement: كيان حركة الصندوق من Domain Layer
    
    Returns:
        FundMovementDTO: كائن نقل البيانات للحركة
    """
    if not movement:
        return None
    
    return FundMovementDTO(
        id=safe_str(movement.id),
        fund_id=safe_str(movement.fund_id),
        movement_type=safe_str(movement.transaction_type),
        amount=safe_money_to_float(movement.amount),
        currency=safe_str(movement.amount.currency) if hasattr(movement.amount, 'currency') else "USD",
        balance_after=safe_money_to_float(movement.balance_after),
        reason=safe_str(movement.description),
        created_at=movement.created_at,
        created_by=safe_str(movement.created_by),
        reference_id=safe_str(movement.reference_id),
        exchange_rate_used=None,
        from_fund_code=None,
        to_fund_code=None
    )


def fund_to_dto(fund: Fund) -> Optional[FundDTO]:
    """
    تحويل صندوق من Domain إلى DTO
    
    ✅ مصحح: جميع الحقول من نوع Money تستخدم safe_money_to_float
    ✅ مصحح: دعم القيم None
    ✅ مصحح: استخدام safe_str للتحويل الآمن
    
    Args:
        fund: كيان الصندوق من Domain Layer
    
    Returns:
        FundDTO: كائن نقل البيانات للصندوق
    """
    if not fund:
        return None
    
    # تحويل الحركات
    movements = []
    for tx in fund.get_transactions():
        movements.append(movement_to_dto(tx))
    
    return FundDTO(
        # ✅ استخدام safe_str للتحويل الآمن
        id=safe_str(fund.id),
        code=safe_str(fund.code),
        name=safe_str(fund.name),
        fund_type=safe_str(fund.fund_type),
        account_code=safe_str(fund.account_code),
        currency=safe_str(fund.currency),
        
        # ✅ جميع الحقول من نوع Money تستخدم safe_money_to_float
        balance=safe_money_to_float(fund.current_balance),
        daily_limit=safe_money_to_float(fund.daily_limit),
        monthly_limit=safe_money_to_float(fund.monthly_limit),
        min_balance_alert=safe_money_to_float(fund.min_balance_alert),
        max_balance_alert=safe_money_to_float(fund.max_balance_alert),
        approval_threshold=safe_money_to_float(fund.approval_threshold),
        
        status=safe_str(fund.status),
        requires_approval=bool(fund.requires_approval),
        
        created_at=fund.created_at,
        created_by=safe_str(fund.created_by),
        updated_at=fund.updated_at,
        updated_by=safe_str(fund.updated_by),
        version=int(fund.version) if fund.version else 1,
        is_active=bool(fund.is_active),
        movements=movements
    )


def dto_to_fund(dto: FundDTO) -> Optional[Fund]:
    """
    تحويل DTO إلى كيان صندوق في Domain
    
    ✅ مصحح: تحويل float إلى Decimal بشكل آمن
    
    Args:
        dto: كائن نقل البيانات للصندوق
    
    Returns:
        Fund: كيان الصندوق من Domain Layer
    """
    if not dto:
        return None
    
    from core.domain.funds.entities import utc_now
    
    # دالة مساعدة للتحويل إلى Decimal
    def to_decimal(value: float) -> Decimal:
        try:
            return Decimal(str(value))
        except (TypeError, ValueError):
            return Decimal('0')
    
    # دالة مساعدة لإنشاء Money
    def to_money(amount: float, currency: str) -> Money:
        try:
            return Money(to_decimal(amount), currency)
        except (TypeError, ValueError):
            return Money(Decimal('0'), currency)
    
    fund = Fund(
        id=FundId.from_string(dto.id) if dto.id else FundId.generate(),
        code=FundCode(dto.code),
        name=dto.name,
        fund_type=FundType(dto.fund_type),
        account_code=dto.account_code,
        currency=dto.currency,
        status=FundStatus(dto.status),
        
        # ✅ تحويل float إلى Money
        daily_limit=to_money(dto.daily_limit, dto.currency),
        monthly_limit=to_money(dto.monthly_limit, dto.currency),
        min_balance_alert=to_money(dto.min_balance_alert, dto.currency),
        max_balance_alert=to_money(dto.max_balance_alert, dto.currency),
        approval_threshold=to_money(dto.approval_threshold, dto.currency),
        
        requires_approval=dto.requires_approval,
        created_at=dto.created_at or utc_now(),
        created_by=dto.created_by or "system",
        updated_at=dto.updated_at or utc_now(),
        updated_by=dto.updated_by or "system",
        version=dto.version or 1
    )
    
    return fund


# =============================================================================
# دوال إضافية للتحويلات (FundTransfer)
# =============================================================================

def transfer_to_dict(transfer: FundTransfer) -> dict:
    """
    تحويل FundTransfer إلى قاموس
    
    Args:
        transfer: كيان التحويل من Domain Layer
    
    Returns:
        dict: قاموس يحتوي على بيانات التحويل
    """
    if not transfer:
        return {}
    
    return {
        'id': safe_str(transfer.id),
        'from_fund_id': safe_str(transfer.from_fund_id),
        'to_fund_id': safe_str(transfer.to_fund_id),
        'amount': safe_money_to_float(transfer.amount),
        'from_currency': safe_str(transfer.from_currency),
        'to_currency': safe_str(transfer.to_currency),
        'exchange_rate': safe_decimal_to_float(transfer.exchange_rate),
        'converted_amount': safe_money_to_float(transfer.converted_amount),
        'status': safe_str(transfer.status),
        'reason': safe_str(transfer.reason),
        'journal_entry_id': safe_str(transfer.journal_entry_id),
        'created_at': transfer.created_at.isoformat() if transfer.created_at else None,
        'created_by': safe_str(transfer.created_by),
        'approved_at': transfer.approved_at.isoformat() if transfer.approved_at else None,
        'approved_by': safe_str(transfer.approved_by),
        'completed_at': transfer.completed_at.isoformat() if transfer.completed_at else None
    }


def dict_to_transfer(data: dict) -> dict:
    """
    تحويل قاموس إلى بيانات تحويل (للاستخدام في Service Layer)
    
    Args:
        data: قاموس يحتوي على بيانات التحويل
    
    Returns:
        dict: قاموس مع البيانات المحولة
    """
    if not data:
        return {}
    
    return {
        'from_fund_id': data.get('from_fund_id'),
        'to_fund_id': data.get('to_fund_id'),
        'amount': safe_decimal_to_float(data.get('amount', 0)),
        'reason': safe_str(data.get('reason', '')),
        'manual_rate': safe_decimal_to_float(data.get('manual_rate')) if data.get('manual_rate') else None,
        'created_by': safe_str(data.get('created_by', 'system'))
    }


# =============================================================================
# دوال مساعدة للقوائم
# =============================================================================

def funds_to_dto_list(funds: List[Fund]) -> List[FundDTO]:
    """
    تحويل قائمة صناديق إلى قائمة DTOs
    
    Args:
        funds: قائمة كيانات الصناديق
    
    Returns:
        List[FundDTO]: قائمة كائنات نقل البيانات
    """
    if not funds:
        return []
    
    return [fund_to_dto(fund) for fund in funds if fund]


def movements_to_dto_list(movements: List[FundMovement]) -> List[FundMovementDTO]:
    """
    تحويل قائمة حركات إلى قائمة DTOs
    
    Args:
        movements: قائمة كيانات الحركات
    
    Returns:
        List[FundMovementDTO]: قائمة كائنات نقل البيانات
    """
    if not movements:
        return []
    
    return [movement_to_dto(movement) for movement in movements if movement]


# =============================================================================
# دوال للتحقق من صحة البيانات
# =============================================================================

def validate_fund_dto(dto: FundDTO) -> List[str]:
    """
    التحقق من صحة FundDTO
    
    Args:
        dto: كائن نقل البيانات للصندوق
    
    Returns:
        List[str]: قائمة بأخطاء التحقق
    """
    errors = []
    
    if not dto.code or len(dto.code.strip()) < 2:
        errors.append("كود الصندوق مطلوب (أقل من حرفين)")
    
    if not dto.name or len(dto.name.strip()) < 2:
        errors.append("اسم الصندوق مطلوب (أقل من حرفين)")
    
    if not dto.account_code or len(dto.account_code.strip()) < 3:
        errors.append("كود حساب الأستاذ مطلوب (أقل من 3 أحرف)")
    
    if dto.balance < 0:
        errors.append(f"الرصيد لا يمكن أن يكون سالباً: {dto.balance}")
    
    if dto.daily_limit < 0:
        errors.append(f"الحد اليومي لا يمكن أن يكون سالباً: {dto.daily_limit}")
    
    if dto.monthly_limit < 0:
        errors.append(f"الحد الشهري لا يمكن أن يكون سالباً: {dto.monthly_limit}")
    
    return errors


# =============================================================================
# تصدير الكلاسات والأسماء المستعارة
# =============================================================================

__all__ = [
    # دوال التحويل الأساسية
    'movement_to_dto',
    'fund_to_dto',
    'dto_to_fund',
    'transfer_to_dict',
    'dict_to_transfer',
    
    # دوال القوائم
    'funds_to_dto_list',
    'movements_to_dto_list',
    
    # دوال مساعدة
    'safe_money_to_float',
    'safe_decimal_to_float',
    'safe_str',
    'safe_get_value',
    'validate_fund_dto',
    
    # الأسماء المستعارة
    'FundMovement',
    'MovementType'
]