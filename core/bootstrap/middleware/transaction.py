# core/bootstrap/middleware/transaction.py
"""
Transaction Middleware - إدارة المعاملات (Unit of Work)
مستخرج من bootstrap.py و infrastructure/messaging/middleware.py
"""

from typing import Any, Dict, Optional, Callable
import logging

from .base import Middleware

logger = logging.getLogger(__name__)


class TransactionMiddleware(Middleware):
    """
    Middleware لإدارة المعاملات باستخدام Unit of Work
    
    الميزات:
        1. بدء المعاملة تلقائياً
        2. Commit عند النجاح
        3. Rollback عند الفشل
        4. دعم المعاملات المتداخلة
    """
    
    def __init__(self, uow_provider: Callable[[], Any]):
        """
        Args:
            uow_provider: دالة تعيد Unit of Work
        """
        self._uow_provider = uow_provider
        self._current_uow = None
    
    def before(self, command: Any, context: Dict) -> Dict:
        """بدء المعاملة"""
        if '_uow' in context and context['_uow'] is not None:
            # معاملة موجودة بالفعل (متعددة)
            return context
        
        uow = self._uow_provider()
        if uow:
            context['_uow'] = uow
            context['_is_new_transaction'] = True
            logger.debug(f"🔄 Transaction started for command: {self._get_command_name(command)}")
        
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """Commit المعاملة"""
        uow = context.get('_uow')
        is_new = context.get('_is_new_transaction', False)
        
        if uow and is_new:
            try:
                uow.commit()
                logger.debug(f"✅ Transaction committed for command: {self._get_command_name(command)}")
            except Exception as e:
                logger.error(f"❌ Transaction commit failed: {e}")
                uow.rollback()
                raise
            finally:
                # تنظيف السياق
                context.pop('_uow', None)
                context.pop('_is_new_transaction', None)
        
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """Rollback المعاملة عند الخطأ"""
        uow = context.get('_uow')
        is_new = context.get('_is_new_transaction', False)
        
        if uow and is_new:
            try:
                uow.rollback()
                logger.debug(f"↩️ Transaction rolled back for command: {self._get_command_name(command)}")
            except Exception as e:
                logger.error(f"❌ Transaction rollback failed: {e}")
            finally:
                context.pop('_uow', None)
                context.pop('_is_new_transaction', None)
        
        return None
    
    def _get_command_name(self, command: Any) -> str:
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    @property
    def priority(self) -> int:
        # ينفذ بعد الـ Logging والتوقيت
        return 30
    
    @property
    def name(self) -> str:
        return "transaction"