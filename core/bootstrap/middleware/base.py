# core/bootstrap/middleware/base.py
"""
الفئة الأساسية للـ Middleware
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, List, TypeVar, Generic
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class Middleware(ABC, Generic[T, R]):
    """
    الفئة الأساسية للـ Middleware
    
    كل Middleware يقوم بتنفيذ منطق قبل وبعد معالجة الأمر/الاستعلام.
    """
    
    @abstractmethod
    def before(self, command: T, context: dict) -> dict:
        """
        يتم تنفيذها قبل معالجة الأمر
        
        Args:
            command: الأمر المراد معالجته
            context: سياق التنفيذ (يمكن تعديله)
        
        Returns:
            dict: السياق المحدث
        """
        return context
    
    @abstractmethod
    def after(self, command: T, result: R, context: dict) -> R:
        """
        يتم تنفيذها بعد معالجة الأمر
        
        Args:
            command: الأمر المراد معالجته
            result: نتيجة المعالجة
            context: سياق التنفيذ
        
        Returns:
            R: النتيجة (يمكن تعديلها)
        """
        return result
    
    def handle_error(self, command: T, error: Exception, context: dict) -> Optional[R]:
        """
        يتم تنفيذها عند حدوث خطأ
        
        Args:
            command: الأمر المراد معالجته
            error: الاستثناء الذي حدث
            context: سياق التنفيذ
        
        Returns:
            Optional[R]: نتيجة بديلة أو None لإعادة رفع الاستثناء
        """
        return None
    
    @property
    def name(self) -> str:
        """اسم الـ Middleware"""
        return self.__class__.__name__
    
    @property
    def priority(self) -> int:
        """
        أولوية التنفيذ (كلما كان الرقم أصغر، ينفذ أولاً)
        
        يتم تنفيذ الـ Middleware بالترتيب التالي:
        1. before() من الأقل أولوية إلى الأعلى
        2. after() من الأعلى أولوية إلى الأقل
        """
        return 100


class MiddlewareChain:
    """
    سلسلة الـ Middleware - تدير تنفيذ الـ Middleware بالترتيب الصحيح
    """
    
    def __init__(self):
        self._middleware: List[Middleware] = []
    
    def add(self, middleware: Middleware) -> 'MiddlewareChain':
        """إضافة Middleware إلى السلسلة"""
        self._middleware.append(middleware)
        self._middleware.sort(key=lambda m: m.priority)
        return self
    
    def remove(self, middleware_name: str) -> bool:
        """إزالة Middleware من السلسلة"""
        for i, m in enumerate(self._middleware):
            if m.name == middleware_name:
                self._middleware.pop(i)
                return True
        return False
    
    def clear(self) -> None:
        """مسح جميع الـ Middleware"""
        self._middleware.clear()
    
    def execute_before(self, command: T, context: dict) -> dict:
        """تنفيذ before() لجميع الـ Middleware"""
        current_context = context.copy()
        for middleware in self._middleware:
            try:
                current_context = middleware.before(command, current_context)
            except Exception as e:
                logger.error(f"Error in {middleware.name}.before: {e}")
                raise
        return current_context
    
    def execute_after(self, command: T, result: R, context: dict) -> R:
        """تنفيذ after() لجميع الـ Middleware (بترتيب عكسي)"""
        current_result = result
        for middleware in reversed(self._middleware):
            try:
                current_result = middleware.after(command, current_result, context)
            except Exception as e:
                logger.error(f"Error in {middleware.name}.after: {e}")
                raise
        return current_result
    
    def execute_error(self, command: T, error: Exception, context: dict) -> Optional[R]:
        """تنفيذ handle_error() لجميع الـ Middleware"""
        for middleware in reversed(self._middleware):
            try:
                result = middleware.handle_error(command, error, context)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"Error in {middleware.name}.handle_error: {e}")
                continue
        return None
    
    @property
    def count(self) -> int:
        """عدد الـ Middleware في السلسلة"""
        return len(self._middleware)
    
    def get_middleware_names(self) -> List[str]:
        """الحصول على أسماء الـ Middleware"""
        return [m.name for m in self._middleware]