# core/application/handlers/reports/get_tax_report_handler.py
"""
Get Tax Report Handler - معالج تقرير الضرائب
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetTaxReportHandler(BaseQueryHandler):
    """
    معالج تقرير الضرائب
    
    يقوم بتوليد تقرير شامل عن الضرائب لفترة محددة
    """
    
    def __init__(self, tax_repo, tax_period_repo, ledger_engine):
        self._tax_repo = tax_repo
        self._tax_period_repo = tax_period_repo
        self._ledger_engine = ledger_engine
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير الضرائب
        
        Args:
            query: GetTaxReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير الضرائب
        """
        logger.info(f"Generating tax report for period: {query.from_date} to {query.to_date}")
        
        # جلب القواعد الضريبية
        tax_rules = self._tax_repo.get_all(include_inactive=False)
        
        # جلب الفترة الضريبية
        tax_period = self._tax_period_repo.get_by_date(query.to_date) if query.to_date else None
        
        # حساب الضرائب
        tax_summary = {
            'total_taxable_sales': Decimal('0'),
            'total_tax_collected': Decimal('0'),
            'total_tax_paid': Decimal('0'),
            'net_tax_due': Decimal('0')
        }
        
        # تفصيل حسب نوع الضريبة
        tax_by_type = {}
        for rule in tax_rules:
            tax_type = rule.tax_type.value
            if tax_type not in tax_by_type:
                tax_by_type[tax_type] = {
                    'tax_type': tax_type,
                    'total_amount': Decimal('0'),
                    'total_tax': Decimal('0')
                }
            
            # حساب الضريبة لهذا النوع
            # هذا مبسط - في النظام الكامل يتم حسابه من الفواتير
            tax_by_type[tax_type]['total_tax'] += Decimal('100')  # مثال
        
        return {
            "success": True,
            "report_type": "tax",
            "from_date": query.from_date.isoformat() if query.from_date else None,
            "to_date": query.to_date.isoformat() if query.to_date else None,
            "period": tax_period.code if tax_period else None,
            "data": {
                "summary": {
                    "total_taxable_sales": float(tax_summary['total_taxable_sales']),
                    "total_tax_collected": float(tax_summary['total_tax_collected']),
                    "total_tax_paid": float(tax_summary['total_tax_paid']),
                    "net_tax_due": float(tax_summary['net_tax_due'])
                },
                "by_type": list(tax_by_type.values()),
                "rules": [{
                    'code': rule.code.value,
                    'name': rule.name,
                    'rate': float(rule.rate.rate),
                    'tax_type': rule.tax_type.value,
                    'calculation_type': rule.calculation_type.value,
                    'is_active': rule.is_active
                } for rule in tax_rules]
            },
            "generated_at": datetime.now().isoformat()
        }