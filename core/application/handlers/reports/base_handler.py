# core/application/handlers/reports/base_handler.py
"""
Base Handler for Reports Module - فئة أساسية لمعالجات التقارير
"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.security.authorization import UserContext

TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')


class BaseReportHandler(ABC, Generic[TCommand, TResult]):
    """
    فئة أساسية لمعالجات التقارير
    
    توفر:
        1. إدارة الـ Unit of Work
        2. تكامل مع نظام الصلاحيات
        3. معالجة موحدة للأخطاء
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, command: TCommand, user_context: UserContext = None) -> TResult:
        """تنفيذ المعالج"""
        pass
    
    def _commit(self) -> None:
        """تنفيذ Commit للمعاملة"""
        self._uow.commit()
    
    def _rollback(self) -> None:
        """التراجع عن المعاملة"""
        self._uow.rollback()


class BaseReportQueryHandler(ABC, Generic[TCommand, TResult]):
    """
    فئة أساسية لمعالجات استعلامات التقارير (قراءة فقط)
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, query: TCommand) -> TResult:
        """تنفيذ الاستعلام"""
        pass
    
    def _format_report_response(self, data: Any, report_type: str) -> Dict[str, Any]:
        """تنسيق استجابة التقرير بشكل موحد"""
        return {
            "success": True,
            "report_type": report_type,
            "data": data,
            "generated_at": self._get_current_time()
        }
    
    def _get_current_time(self) -> str:
        """الحصول على الوقت الحالي"""
        from datetime import datetime
        return datetime.now().isoformat()