# core/application/projects/utils.py (ملف جديد)
"""Projects Application Utils - أدوات مساعدة للمعالجات"""

from datetime import datetime
from decimal import Decimal
from typing import Optional


def parse_datetime(value):
    """تحويل قيمة تاريخ/نص إلى datetime aware"""
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            from datetime import timezone
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            from dateutil import parser as date_parser
            return date_parser.parse(value)
    return None


def to_decimal(value) -> Optional[Decimal]:
    """تحويل قيمة إلى Decimal بأمان"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal('1') if value else Decimal('0')
    return Decimal(str(value))