# core/domain/rules/interfaces.py
"""
Accounting Rules Interfaces - واجهات مستودع القواعد المحاسبية
"""
from datetime import datetime

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from .value_objects import RuleType, RulePriority
from .entities import PostingRule, RuleGroup, RuleExecutionLog


class IRuleRepository(ABC):
    """واجهة مستودع القواعد المحاسبية"""

    @abstractmethod
    def save(self, rule: PostingRule) -> None:
        """حفظ قاعدة"""
        pass

    @abstractmethod
    def get_by_id(self, rule_id: str) -> Optional[PostingRule]:
        """الحصول على قاعدة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[PostingRule]:
        """الحصول على قاعدة بواسطة الكود"""
        pass

    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[PostingRule]:
        """الحصول على جميع القواعد"""
        pass

    @abstractmethod
    def get_active_rules(self) -> List[PostingRule]:
        """الحصول على القواعد النشطة"""
        pass

    @abstractmethod
    def get_by_type(self, rule_type: RuleType) -> List[PostingRule]:
        """الحصول على القواعد حسب النوع"""
        pass

    @abstractmethod
    def get_by_priority(self, priority: RulePriority) -> List[PostingRule]:
        """الحصول على القواعد حسب الأولوية"""
        pass

    @abstractmethod
    def get_default_rule(self) -> Optional[PostingRule]:
        """الحصول على القاعدة الافتراضية"""
        pass

    @abstractmethod
    def delete(self, rule_id: str) -> bool:
        """حذف قاعدة"""
        pass

    @abstractmethod
    def count_active(self) -> int:
        """حساب عدد القواعد النشطة"""
        pass


class IRuleGroupRepository(ABC):
    """واجهة مستودع مجموعات القواعد"""

    @abstractmethod
    def save(self, group: RuleGroup) -> None:
        """حفظ مجموعة قواعد"""
        pass

    @abstractmethod
    def get_by_id(self, group_id: str) -> Optional[RuleGroup]:
        """الحصول على مجموعة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[RuleGroup]:
        """الحصول على مجموعة بواسطة الكود"""
        pass

    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[RuleGroup]:
        """الحصول على جميع المجموعات"""
        pass

    @abstractmethod
    def get_default_group(self) -> Optional[RuleGroup]:
        """الحصول على المجموعة الافتراضية"""
        pass

    @abstractmethod
    def delete(self, group_id: str) -> bool:
        """حذف مجموعة قواعد"""
        pass


class IRuleExecutionLogRepository(ABC):
    """واجهة مستودع سجل تنفيذ القواعد"""

    @abstractmethod
    def save(self, log: RuleExecutionLog) -> None:
        """حفظ سجل تنفيذ"""
        pass

    @abstractmethod
    def get_by_id(self, log_id: str) -> Optional[RuleExecutionLog]:
        """الحصول على سجل بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_rule(self, rule_id: str, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على سجلات قاعدة معينة"""
        pass

    @abstractmethod
    def get_by_entity_type(self, entity_type: str, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على سجلات نوع كيان معين"""
        pass

    @abstractmethod
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> List[RuleExecutionLog]:
        """الحصول على سجلات في نطاق زمني"""
        pass

    @abstractmethod
    def get_recent(self, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على أحدث السجلات"""
        pass

    @abstractmethod
    def count_by_rule(self, rule_id: str) -> int:
        """حساب عدد مرات تنفيذ قاعدة معينة"""
        pass

    @abstractmethod
    def delete_old_logs(self, days: int) -> int:
        """حذف السجلات القديمة"""
        pass