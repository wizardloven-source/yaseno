# core/application/handlers/currency/base_handler.py
"""
Base Handler for Currency Module - فئة أساسية لمعالجات العملات
"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.security.authorization import UserContext, require_permission, Permission

TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')


class BaseCurrencyHandler(ABC, Generic[TCommand, TResult]):
    """
    فئة أساسية لمعالجات العملات
    
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


class BaseCurrencyQueryHandler(ABC, Generic[TCommand, TResult]):
    """
    فئة أساسية لمعالجات الاستعلامات (قراءة فقط)
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, query: TCommand) -> TResult:
        """تنفيذ الاستعلام"""
        pass