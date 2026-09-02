# core/infrastructure/bus/in_memory_event_bus.py

"""
IN-MEMORY EVENT BUS IMPLEMENTATION - YASEEN ERP ENTERPRISE EDITION

This component manages thread-safe routing and dispatching of domain events 
to their registered functional or infrastructure handlers locally.

DESIGN COMPLIANCE: Thread-Safe, Idempotent, High-Concurrency Optimized.
"""

from typing import List, Dict, Callable, Optional, Union
from collections import defaultdict
import logging
import threading

from core.domain.accounting.interfaces import IEventBus
from core.domain.shared.value_objects import BaseDomainEvent

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """
    Enterprise-grade, in-memory synchronous event bus.
    Enforces absolute thread safety using Reentrant Locks (RLock) to prevent race conditions.
    """
    
    def __init__(self):
        # ✅ دعم السلاسل النصية والكلاسات كمفاتيح
        self._handlers: Dict[Union[type, str], List[Callable]] = defaultdict(list)
        self._wildcard_handlers: List[Callable] = []
        self._lock = threading.RLock()
    
    def dispatch(self, event: BaseDomainEvent) -> None:
        """
        Dispatch a single domain event to all bound handlers safely.
        """
        if not event:
            return

        event_type = type(event)
        event_name = event.get_event_name()
        
        handlers_to_execute: List[Callable] = []
        wildcards_to_execute: List[Callable] = []
        
        with self._lock:
            # ✅ البحث بالكلاس أولاً
            if event_type in self._handlers:
                handlers_to_execute = self._handlers[event_type].copy()
            # ✅ البحث باسم الحدث ثانياً
            elif event_name in self._handlers:
                handlers_to_execute = self._handlers[event_name].copy()
            
            if self._wildcard_handlers:
                wildcards_to_execute = self._wildcard_handlers.copy()
        
        for handler in handlers_to_execute:
            self._safe_call_handler(handler, event)
        
        for handler in wildcards_to_execute:
            self._safe_call_handler(handler, event)
        
        logger.debug(f"Successfully routed event: {event_name} to execution targets.")
    
    def dispatch_many(self, events: List[BaseDomainEvent]) -> None:
        """
        Dispatch a collection of domain events sequentially.
        """
        if not events:
            return
        for event in events:
            self.dispatch(event)
    
    def add_handler(self, event_type: Union[type, str], handler: Callable) -> None:
        """
        Register a custom functional handler for a specific domain event type.
        
        Args:
            event_type: يمكن أن يكون كلاس الحدث أو اسم الحدث كسلسلة نصية
            handler: الدالة المعالجة
        """
        if not callable(handler):
            raise ValueError(f"Infrastructure Error: Target handler must be callable, received type: {type(handler)}")
        
        with self._lock:
            if handler in self._handlers[event_type]:
                # ✅ الحصول على اسم مناسب للعرض
                type_name = event_type if isinstance(event_type, str) else event_type.__name__
                logger.warning(
                    f"Idempotency Guard: Handler '{handler.__name__}' is already linked to "
                    f"'{type_name}'. Registration skipped."
                )
                return
                
            self._handlers[event_type].append(handler)
            
            # ✅ الحصول على اسم مناسب للعرض
            type_name = event_type if isinstance(event_type, str) else event_type.__name__
            logger.debug(f"Bound handler '{handler.__name__}' safely to event context: '{type_name}'")
    
    def remove_handler(self, event_type: Union[type, str], handler: Callable) -> None:
        """
        Remove an active handler from a specific event type registration array.
        """
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                    type_name = event_type if isinstance(event_type, str) else event_type.__name__
                    logger.info(f"Unbound handler '{handler.__name__}' from event: '{type_name}'")
                    
                    if not self._handlers[event_type]:
                        del self._handlers[event_type]
                except ValueError:
                    pass
    
    def add_wildcard_handler(self, handler: Callable) -> None:
        """
        Register an audit or global infrastructure handler that intercepts every single event.
        """
        if not callable(handler):
            raise ValueError(f"Infrastructure Error: Wildcard handler must be callable, received type: {type(handler)}")
        
        with self._lock:
            if handler in self._wildcard_handlers:
                logger.warning(f"Idempotency Guard: Wildcard handler '{handler.__name__}' already exists. Skipping.")
                return
            self._wildcard_handlers.append(handler)
            logger.debug(f"Global wildcard auditor handler '{handler.__name__}' mounted successfully.")
    
    def clear_handlers(self) -> None:
        """
        Purges all internal registration maps.
        """
        with self._lock:
            self._handlers.clear()
            self._wildcard_handlers.clear()
            logger.info("Internal event bus registration matrices purged successfully.")
    
    def _safe_call_handler(self, handler: Callable, event: BaseDomainEvent) -> None:
        """
        Safely invokes an isolated handler execution pipeline.
        """
        try:
            handler(event)
        except Exception as e:
            logger.error(
                f"CRITICAL COMPLIANCE ERROR: Exception caught inside handler '{handler.__name__}' "
                f"while processing domain event '{event.get_event_name()}'. details: {str(e)}",
                exc_info=True
            )


__all__ = ["InMemoryEventBus"]