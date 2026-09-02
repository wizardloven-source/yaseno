# core/application/handlers/base_handler.py (قاعدة موحدة للمعالجات)

"""
Base Handler - Unified base class for all application handlers
"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
from dataclasses import dataclass

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.security.authorization import UserContext, require_permission, Permission


TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')


class BaseHandler(ABC, Generic[TCommand, TResult]):
    """
    Base class for all command/query handlers
    
    Responsibilities:
        1. Handle transactions via Unit of Work
        2. Apply authorization rules
        3. Convert domain exceptions to DTOs
        4. Dispatch domain events
    
    Usage:
        class CreateInvoiceHandler(BaseHandler[CreateInvoiceCommand, InvoiceDTO]):
            def __init__(self, uow: IUnitOfWork):
                self._uow = uow
            
            def handle(self, command: CreateInvoiceCommand, user_context: UserContext) -> InvoiceDTO:
                with self._uow:
                    # Business logic here
                    self._uow.commit()
                return result
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, command: TCommand, user_context: UserContext) -> TResult:
        """Handle the command"""
        pass
    
    def _commit(self) -> None:
        """Commit the current transaction"""
        self._uow.commit()
    
    def _rollback(self) -> None:
        """Rollback the current transaction"""
        self._uow.rollback()


class BaseQueryHandler(ABC, Generic[TCommand, TResult]):
    """Base class for query handlers (read-only operations)"""
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @abstractmethod
    def handle(self, query: TCommand) -> TResult:
        """Handle the query"""
        pass