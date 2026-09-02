# core/application/handlers/reports/get_general_ledger_report_handler.py
"""
Get General Ledger Report Handler - معالج تقرير دفتر الأستاذ العام
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetGeneralLedgerReportHandler(BaseQueryHandler):
    """
    معالج تقرير دفتر الأستاذ العام
    
    يقوم بتوليد دفتر الأستاذ العام لفترة محددة
    """
    
    def __init__(self, ledger_repo):
        self._ledger_repo = ledger_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد دفتر الأستاذ العام
        
        Args:
            query: GetGeneralLedgerReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: دفتر الأستاذ العام
        """
        logger.info(f"Generating general ledger for period: {query.from_date} to {query.to_date}")
        
        # جلب حركات الأستاذ
        entries = self._ledger_repo.get_entries_by_date_range(
            from_date=query.from_date,
            to_date=query.to_date
        )
        
        # تجميع حسب الحساب
        ledger_data = {}
        for entry in entries:
            account_code = entry.account_code.code
            if account_code not in ledger_data:
                ledger_data[account_code] = {
                    'account_code': account_code,
                    'transactions': [],
                    'total_debit': 0,
                    'total_credit': 0,
                    'balance': 0
                }
            
            ledger_data[account_code]['transactions'].append({
                'date': entry.date.isoformat(),
                'description': entry.description,
                'debit': float(entry.debit.amount),
                'credit': float(entry.credit.amount),
                'balance': float(entry.amount.amount)
            })
            
            ledger_data[account_code]['total_debit'] += float(entry.debit.amount)
            ledger_data[account_code]['total_credit'] += float(entry.credit.amount)
            ledger_data[account_code]['balance'] += float(entry.amount.amount)
        
        return {
            "success": True,
            "report_type": "general_ledger",
            "from_date": query.from_date.isoformat(),
            "to_date": query.to_date.isoformat(),
            "currency": query.currency,
            "accounts": list(ledger_data.values()),
            "total_entries": len(entries),
            "account_count": len(ledger_data),
            "generated_at": datetime.now().isoformat()
        }