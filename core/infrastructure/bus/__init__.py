# core/infrastructure/bus/__init__.py
"""Message Bus Infrastructure"""

from .in_memory_event_bus import InMemoryEventBus

__all__ = ["InMemoryEventBus"]