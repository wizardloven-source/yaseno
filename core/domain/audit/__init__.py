"""
Audit Trail Domain Models for YASeen ERP

Provides comprehensive audit logging for all critical operations.
"""

from core.domain.security.models import AuditEvent, AuditEventType

__all__ = ['AuditEvent', 'AuditEventType']
