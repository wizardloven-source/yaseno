# core/application/settings/accounting_settings_service.py
"""خدمة إعدادات الحسابات المحاسبية"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.infrastructure.db.models.settings_model import AccountingSettingsModel
from core.domain.shared.value_objects import AccountCode


class AccountingSettingsService:
    """خدمة لإدارة إعدادات الحسابات المحاسبية"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def get_settings(self) -> Dict[str, str]:
        """الحصول على الإعدادات الحالية"""
        settings = self._session.query(AccountingSettingsModel).first()
        
        if not settings:
            # إنشاء إعدادات افتراضية إذا لم توجد
            settings = AccountingSettingsModel()
            self._session.add(settings)
            self._session.flush()
        
        return {
            'sales_revenue_account': settings.sales_revenue_account,
            'cash_account': settings.cash_account,
            'receivables_account': settings.receivables_account,
            'inventory_account': settings.inventory_account,
            'payables_account': settings.payables_account,
            'income_summary_account': settings.income_summary_account,
            'retained_earnings_account': settings.retained_earnings_account,
            'cogs_account': settings.cogs_account,
            'tax_account': settings.tax_account,
        }
    
    def update_settings(self, updates: Dict[str, str]) -> bool:
        """تحديث الإعدادات"""
        settings = self._session.query(AccountingSettingsModel).first()
        
        if not settings:
            settings = AccountingSettingsModel()
            self._session.add(settings)
        
        for key, value in updates.items():
            if hasattr(settings, key) and value:
                setattr(settings, key, value)
        
        self._session.commit()
        return True
    
    def get_sales_revenue_account(self) -> AccountCode:
        """الحصول على حساب إيرادات المبيعات"""
        settings = self.get_settings()
        return AccountCode(settings['sales_revenue_account'])
    
    def get_cash_account(self) -> AccountCode:
        """الحصول على حساب الصندوق"""
        settings = self.get_settings()
        return AccountCode(settings['cash_account'])
    
    def get_receivables_account(self) -> AccountCode:
        """الحصول على حساب المدينين"""
        settings = self.get_settings()
        return AccountCode(settings['receivables_account'])
    
    def get_inventory_account(self) -> AccountCode:
        """الحصول على حساب المخزون"""
        settings = self.get_settings()
        return AccountCode(settings['inventory_account'])
    
    def get_payables_account(self) -> AccountCode:
        """الحصول على حساب الدائنون"""
        settings = self.get_settings()
        return AccountCode(settings['payables_account'])
    
    def get_income_summary_account(self) -> AccountCode:
        """الحصول على حساب ملخص الدخل"""
        settings = self.get_settings()
        return AccountCode(settings['income_summary_account'])
    
    def get_retained_earnings_account(self) -> AccountCode:
        """الحصول على حساب الأرباح المحتجزة"""
        settings = self.get_settings()
        return AccountCode(settings['retained_earnings_account'])
    
    def get_cogs_account(self) -> AccountCode:
        """الحصول على حساب تكلفة البضائع المباعة"""
        settings = self.get_settings()
        return AccountCode(settings['cogs_account'])
    
    def reset_to_defaults(self) -> bool:
        """إعادة تعيين الإعدادات إلى القيم الافتراضية"""
        settings = self._session.query(AccountingSettingsModel).first()
        
        if not settings:
            settings = AccountingSettingsModel()
            self._session.add(settings)
        
        settings.sales_revenue_account = "4010"
        settings.cash_account = "1010"
        settings.receivables_account = "1020"
        settings.inventory_account = "1030"
        settings.payables_account = "2010"
        settings.income_summary_account = "3990"
        settings.retained_earnings_account = "3010"
        settings.cogs_account = "5010"
        settings.tax_account = "2100"
        
        self._session.commit()
        return True