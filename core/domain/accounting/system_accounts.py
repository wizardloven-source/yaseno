# core/domain/accounting/system_accounts.py
"""
سجل الحسابات النظامية الأساسية
================================

الحسابات التي يعتمد عليها المحرك المحاسبي بشكل صريح (أكواد مضمّنة في
المنطق) تُنشأ تلقائياً عند أول ترحيل يستخدمها، بدلاً من بذر دليل حسابات
جاهز. هذا يتيح للمستخدم إضافة حساباته بنفسه مع بقاء النظام قادراً على
الترحيل دون أخطاء "حساب غير موجود".
"""

import logging
from typing import Dict, Optional

from core.domain.accounting.interfaces import Account
from core.domain.shared.value_objects import AccountCode

logger = logging.getLogger(__name__)

# الكود -> (الاسم، النوع، الوصف، العملة)
SYSTEM_ACCOUNTS: Dict[str, Dict[str, Optional[str]]] = {
    "1010": {"name": "الصندوق", "account_type": "asset", "description": "حساب الصندوق النقدي الرئيسي", "currency": "USD"},
    "1020": {"name": "المدينون", "account_type": "asset", "description": "حساب العملاء والمدينون", "currency": "USD"},
    "1030": {"name": "المخزون", "account_type": "asset", "description": "حساب المخزون", "currency": "USD"},
    "2010": {"name": "الدائنون", "account_type": "liability", "description": "حساب الموردين والدائنون", "currency": "USD"},
    "2100": {"name": "ضريبة القيمة المضافة", "account_type": "liability", "description": "ضريبة القيمة المضافة المستحقة", "currency": "USD"},
    "3010": {"name": "رأس المال", "account_type": "equity", "description": "رأس المال المدفوع", "currency": "USD"},
    "3990": {"name": "ملخص الدخل", "account_type": "equity", "description": "حساب ملخص الدخل للإقفال", "currency": "USD"},
    "4010": {"name": "إيرادات المبيعات", "account_type": "revenue", "description": "إيرادات المبيعات", "currency": "USD"},
    "5010": {"name": "تكلفة البضاعة المباعة", "account_type": "expense", "description": "تكلفة البضاعة المباعة", "currency": "USD"},
    "5900": {"name": "فروقات العملات", "account_type": "expense", "description": "فروقات العملات والتسوية", "currency": "USD"},
}


def ensure_system_accounts(account_repo, codes) -> None:
    """
    إنشاء الحسابات النظامية الناقصة التي تشير إليها أسطر القيد.

    Args:
        account_repo: مستودع الحسابات (يجب أن يكون مرتبطاً بجلسة UoW الحالية)
        codes: قائمة بأكواد الحسابات المطلوبة (AccountCode أو str)
    """
    if account_repo is None:
        return

    created = False
    for code in codes:
        code_str = str(code)
        if code_str not in SYSTEM_ACCOUNTS:
            continue

        account_code = AccountCode(code_str)
        if account_repo.exists(account_code):
            continue

        meta = SYSTEM_ACCOUNTS[code_str]
        account = Account(
            code=account_code,
            name=meta["name"],
            account_type=meta["account_type"],
            description=meta["description"],
            currency=meta["currency"],
            is_active=True,
        )
        try:
            account_repo.save(account)
            created = True
            logger.info(f"   ✅ System account auto-created: {code_str} ({meta['name']})")
        except Exception as e:
            logger.warning(f"Failed to auto-create system account {code_str}: {e}")

    # بعض المستودعات لا تُفرّغ الجلسة عند الحفظ (autoflush=False)، لذا نُفرّغها
    # هنا حتى ترى القراءات اللاحقة داخل نفس المعاملة الحسابات المُنشأة.
    if created:
        session = getattr(account_repo, "_session", None)
        if session is not None:
            try:
                session.flush()
            except Exception as e:
                logger.warning(f"Failed to flush after creating system accounts: {e}")
