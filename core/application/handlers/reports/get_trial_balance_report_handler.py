# core/application/handlers/reports/get_trial_balance_report_handler.py
"""
Get Trial Balance Report Handler - معالج تقرير ميزان المراجعة
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetTrialBalanceReportHandler(BaseQueryHandler):
    """
    معالج تقرير ميزان المراجعة
    
    يقوم بتوليد ميزان المراجعة في تاريخ محدد
    """
    
    def __init__(self, ledger_engine):
        self._ledger_engine = ledger_engine
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد ميزان المراجعة
        
        Args:
            query: GetTrialBalanceReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: ميزان المراجعة
        """
        logger.info(f"Generating trial balance as of: {query.as_of_date}")
        
        # جلب ميزان المراجعة
        balances = self._ledger_engine.get_trial_balance(
            as_of=query.as_of_date,
            currency=query.currency
        )
        
        # حساب الإجماليات
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        balance_list = []
        for account_code, balance in balances.items():
            amount = balance.amount
            balance_list.append({
                'account_code': account_code.code,
                'account_name': '',  # سيتم تعبئته من قاعدة البيانات
                'debit': float(amount) if amount > 0 else 0,
                'credit': float(-amount) if amount < 0 else 0,
                'balance': float(amount),
                'currency': balance.currency
            })
            
            if amount > 0:
                total_debits += amount
            else:
                total_credits += abs(amount)
        
        return {
            "success": True,
            "report_type": "trial_balance",
            "as_of_date": query.as_of_date.isoformat(),
            "currency": query.currency,
            "accounts": balance_list,
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "is_balanced": abs(total_debits - total_credits) < Decimal('0.01'),
            "difference": float(abs(total_debits - total_credits)),
            "account_count": len(balance_list),
            "generated_at": datetime.now().isoformat()
        }