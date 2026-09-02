# core/application/handlers/customer_branch/base_handler.py
"""
Base Handler for Customer Branch - فئة أساسية للمعالجات
"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.security.authorization import UserContext, require_permission, Permission

TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')


class BaseBranchHandler(ABC, Generic[TCommand, TResult]):
    """
    فئة أساسية لمعالجات فروع العملاء
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, command: TCommand, user_context: UserContext) -> TResult:
        """تنفيذ المعالج"""
        pass
    
    def _commit(self) -> None:
        self._uow.commit()
    
    def _rollback(self) -> None:
        self._uow.rollback()


class BaseBranchQueryHandler(ABC, Generic[TCommand, TResult]):
    """
    فئة أساسية لمعالجات الاستعلامات (قراءة فقط)
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, query: TCommand) -> TResult:
        """تنفيذ الاستعلام"""
        pass