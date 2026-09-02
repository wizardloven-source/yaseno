# core/application/handlers/reports/get_subsidiary_ledger_report_handler.py
"""
Get Subsidiary Ledger Report Handler - معالج تقرير دفتر الأستاذ المساعد
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetSubsidiaryLedgerReportHandler(BaseQueryHandler):
    """
    معالج تقرير دفتر الأستاذ المساعد
    
    يقوم بتوليد دفتر الأستاذ المساعد لحساب معين
    """
    
    def __init__(self, ledger_repo):
        self._ledger_repo = ledger_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد دفتر الأستاذ المساعد
        
        Args:
            query: GetSubsidiaryLedgerReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: دفتر الأستاذ المساعد
        """
        logger.info(f"Generating subsidiary ledger for account: {query.account_code}")
        
        # جلب حركات الحساب
        entries = self._ledger_repo.get_entries_by_account(
            account_code=query.account_code,
            from_date=query.from_date,
            to_date=query.to_date
        )
        
        # حساب الرصيد التراكمي
        running_balance = 0
        transactions = []
        
        for entry in entries:
            amount = float(entry.amount.amount)
            running_balance += amount
            
            transactions.append({
                'date': entry.date.isoformat(),
                'description': entry.description,
                'reference': entry.reference,
                'debit': float(entry.debit.amount),
                'credit': float(entry.credit.amount),
                'balance': running_balance
            })
        
        return {
            "success": True,
            "report_type": "subsidiary_ledger",
            "account_code": query.account_code,
            "from_date": query.from_date.isoformat(),
            "to_date": query.to_date.isoformat(),
            "currency": query.currency,
            "transactions": transactions,
            "total_transactions": len(transactions),
            "opening_balance": 0,
            "closing_balance": running_balance,
            "generated_at": datetime.now().isoformat()
        }