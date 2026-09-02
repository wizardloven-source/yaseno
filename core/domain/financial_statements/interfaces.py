# core/domain/financial_statements/interfaces.py
"""
Financial Statements Repository Interfaces
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from .entities import FinancialStatement, IncomeStatement, BalanceSheet, CashFlowStatement
from .value_objects import StatementId, StatementType, StatementPeriodInfo


class IFinancialStatementRepository(ABC):
    """واجهة مستودع القوائم المالية"""
    
    @abstractmethod
    def save(self, statement: FinancialStatement) -> None:
        """حفظ القائمة المالية"""
        pass
    
    @abstractmethod
    def get_by_id(self, statement_id: StatementId) -> Optional[FinancialStatement]:
        """الحصول على قائمة مالية بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_type_and_period(
        self,
        statement_type: StatementType,
        period_info: StatementPeriodInfo
    ) -> Optional[FinancialStatement]:
        """الحصول على قائمة مالية حسب النوع والفترة"""
        pass
    
    @abstractmethod
    def list_by_type(
        self,
        statement_type: StatementType,
        limit: int = 100,
        offset: int = 0
    ) -> List[FinancialStatement]:
        """قائمة القوائم المالية حسب النوع"""
        pass
    
    @abstractmethod
    def list_by_period(
        self,
        start_date: date,
        end_date: date,
        limit: int = 100
    ) -> List[FinancialStatement]:
        """قائمة القوائم المالية في نطاق زمني"""
        pass
    
    @abstractmethod
    def delete(self, statement_id: StatementId) -> bool:
        """حذف قائمة مالية"""
        pass