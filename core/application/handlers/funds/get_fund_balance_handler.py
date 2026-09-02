# core/application/handlers/funds/get_fund_balance_handler.py

"""
Get Fund Balance Handler - معالج الحصول على رصيد الصندوق
"""

import logging

from core.domain.funds.value_objects import FundId
from core.domain.funds.interfaces import IFundRepository
from core.domain.funds.exceptions import FundNotFoundError
from core.application.handlers.base_handler import BaseHandler
from core.application.funds.commands import GetFundBalanceQuery

logger = logging.getLogger(__name__)


class GetFundBalanceHandler(BaseHandler[GetFundBalanceQuery, dict]):
    """
    معالج الحصول على رصيد الصندوق
    """
    
    def __init__(self, fund_repository: IFundRepository):
        self.fund_repository = fund_repository
    
    def handle(self, query: GetFundBalanceQuery) -> dict:
        """معالجة استعلام الحصول على الرصيد"""
        
        # ✅ أصبح الأمر أبسط بكثير، query.fund_id من النوع FundId
        fund_id = query.fund_id
        
        # التحقق من صحة النوع
        if not isinstance(fund_id, FundId):
            logger.error(f"Invalid fund_id type: {type(fund_id)}")
            return {
                "success": False,
                "message": f"معرف الصندوق غير صالح: {fund_id}",
            }
        
        fund = self.fund_repository.get_by_id(fund_id)
        
        if not fund:
            raise FundNotFoundError(str(fund_id))
        
        # الحصول على الرصيد (الحالي أو في تاريخ محدد)
        if query.as_of_date:
            balance = fund.get_balance_at(query.as_of_date)
        else:
            balance = fund.current_balance
        
        return {
            "success": True,
            "fund_id": str(fund.id.value),
            "fund_code": fund.code.value,
            "fund_name": fund.name,
            "currency": balance.currency,
            "balance": float(balance.amount),
            "status": fund.status.value,
            "is_active": fund.is_active,
            "as_of_date": query.as_of_date.isoformat() if query.as_of_date else None
        }