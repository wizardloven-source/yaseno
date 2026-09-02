"""Fiscal Year Services"""
from typing import Optional, List
from datetime import date, datetime

from .value_objects import FiscalPeriodReference


def _as_date(value) -> date:
    """تحويل أي قيمة تاريخ إلى كائن date للمقارنة الموحدة."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


class FiscalYearService:
    """خدمة السنة المالية"""
    
    def __init__(self, repo):
        self._repo = repo
    
    def get_current_fiscal_year(self):
        """الحصول على السنة المالية الحالية"""
        return self._repo.get_current()
    
    def get_current_period(self):
        """الحصول على الفترة المالية الحالية"""
        year = self.get_current_fiscal_year()
        if not year:
            return None
        
        today = date.today()
        for period in year.periods:
            if _as_date(period.start_date) <= today <= _as_date(period.end_date):
                return period
        return None
    
    def validate_date_for_posting(self, dt: date) -> tuple:
        """التحقق من صحة تاريخ الترحيل (يسمح بأي فترة مفتوحة في السنة المفتوحة)"""
        year = self.get_current_fiscal_year()
        if not year:
            return False, "No active fiscal year found"
        
        if year.status.value != "open":
            return False, f"Fiscal year {year.code} is not open"
        
        # الفترات المفتوحة التي تحتوي التاريخ
        if year.get_open_periods_for_date(dt):
            return True, ""
        
        # الفترة موجودة لكنها مغلقة؟
        for period in year.periods:
            if _as_date(period.start_date) <= dt <= _as_date(period.end_date):
                return False, f"Period {period.reference} is closed"
        
        return False, f"Date {dt} is outside any fiscal period of {year.code}"
    
    def is_period_open(self, ref: FiscalPeriodReference) -> bool:
        """التحقق من أن الفترة مفتوحة (ضمن سنة مالية مفتوحة)"""
        year = self.get_current_fiscal_year()
        if not year:
            return False
        
        if year.status.value != "open":
            return False
        
        period = year.get_period(ref)
        if not period:
            return False
        
        return not period.is_closed