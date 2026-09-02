# core/application/handlers/reports/get_profitability_report_handler.py
"""
Get Profitability Report Handler - معالج تقرير الربحية
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetProfitabilityReportHandler(BaseQueryHandler):
    """
    معالج تقرير الربحية
    
    يقوم بتوليد تقرير الربحية حسب المنتج، العميل، أو الفئة
    """
    
    def __init__(self, ledger_engine, invoice_repo, purchase_order_repo):
        self._ledger_engine = ledger_engine
        self._invoice_repo = invoice_repo
        self._purchase_order_repo = purchase_order_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير الربحية
        
        Args:
            query: GetProfitabilityReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير الربحية
        """
        logger.info(f"Generating profitability report by: {query.group_by}")
        
        # جلب الفواتير في الفترة
        invoices = self._invoice_repo.list_by_date_range(
            from_date=query.from_date,
            to_date=query.to_date,
            limit=10000
        )
        
        # حساب الإيرادات والتكاليف
        total_revenue = Decimal('0')
        total_cost = Decimal('0')
        
        profitability_data = []
        
        # تجميع حسب المجموعة المطلوبة
        groups = {}
        
        for invoice in invoices:
            total_revenue += invoice.total.amount
            
            # حساب التكلفة (مبسط)
            # في النظام الكامل، يتم حساب التكلفة من حركات المخزون
            cost = invoice.total.amount * Decimal('0.7')  # افتراض هامش ربح 30%
            total_cost += cost
            
            key = 'all'
            if query.group_by == 'customer':
                key = invoice.customer_id
            elif query.group_by == 'product':
                for line in invoice.lines:
                    key = line.product_code
                    if key not in groups:
                        groups[key] = {
                            'id': key,
                            'name': line.product_name,
                            'revenue': Decimal('0'),
                            'cost': Decimal('0')
                        }
                    groups[key]['revenue'] += line.total.amount
                    groups[key]['cost'] += line.total.amount * Decimal('0.7')
                continue
            
            if key not in groups:
                groups[key] = {
                    'id': key,
                    'name': invoice.customer_name if query.group_by == 'customer' else 'Total',
                    'revenue': Decimal('0'),
                    'cost': Decimal('0')
                }
            groups[key]['revenue'] += invoice.total.amount
            groups[key]['cost'] += invoice.total.amount * Decimal('0.7')
        
        # حساب الربحية لكل مجموعة
        for key, data in groups.items():
            revenue = data['revenue']
            cost = data['cost']
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            profitability_data.append({
                'id': data['id'],
                'name': data['name'],
                'revenue': float(revenue),
                'cost': float(cost),
                'profit': float(profit),
                'margin': float(margin)
            })
        
        # ترتيب حسب الربح
        profitability_data.sort(key=lambda x: x['profit'], reverse=True)
        
        total_profit = total_revenue - total_cost
        total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "success": True,
            "report_type": "profitability",
            "from_date": query.from_date.isoformat(),
            "to_date": query.to_date.isoformat(),
            "group_by": query.group_by,
            "currency": query.currency,
            "summary": {
                "total_revenue": float(total_revenue),
                "total_cost": float(total_cost),
                "total_profit": float(total_profit),
                "total_margin": float(total_margin)
            },
            "data": profitability_data,
            "generated_at": datetime.now().isoformat()
        }