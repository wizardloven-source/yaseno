# core/application/handlers/centers/post_allocation_handler.py
"""
Post Allocation Handler - معالج ترحيل توزيع مصروفات
"""

import logging

from core.domain.centers.services import CenterService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import PostAllocationCommand
from core.application.centers.dtos import AllocationDTO
from core.application.centers.converters import allocation_to_dto

logger = logging.getLogger(__name__)


class PostAllocationHandler(BaseHandler[PostAllocationCommand, AllocationDTO]):
    """
    معالج ترحيل توزيع مصروفات
    
    يقوم بترحيل التوزيع وإنشاء القيد المحاسبي المرتبط به.
    """
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @property
    def _service(self):
        return CenterService(
            center_repo=self._uow.centers,
            allocation_repo=self._uow.center_allocations,
            rule_repo=self._uow.center_allocation_rules
        )

    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: PostAllocationCommand, 
user_context: UserContext) -> AllocationDTO:
        """
        تنفيذ ترحيل التوزيع
        
        Args:
            command: أمر ترحيل التوزيع
            user_context: سياق المستخدم
        
        Returns:
            AllocationDTO: بيانات التوزيع بعد الترحيل
        """
        logger.info(f"Posting allocation: {command.allocation_id}")

        with self._uow:
            # الحصول على التوزيع
            allocation_repo = self._uow.center_allocations
            allocation = allocation_repo.get_by_id(command.allocation_id)

            if not allocation:
                raise ValueError(f"Allocation not found: {command.allocation_id}")

            if allocation.is_posted:
                raise ValueError(f"Allocation already posted: {command.allocation_id}")

            # التحقق من التوازن
            if not allocation.is_balanced:
                raise ValueError(
                    f"Allocation is not balanced: "
                    f"total={allocation.total_amount}, allocated={allocation.total_allocated}"
                )

            # إنشاء القيد المحاسبي
            journal_entry_id = self._create_journal_entry(allocation, user_context)

            # ترحيل التوزيع
            allocation = self._service.post_allocation(
                allocation_id=command.allocation_id,
                posted_by=user_context.user_id,
                journal_entry_id=journal_entry_id
            )

            self._commit()

        logger.info(f"Allocation posted: {allocation.id} (Journal: {journal_entry_id})")

        return allocation_to_dto(allocation)

    def _create_journal_entry(self, allocation, user_context: UserContext) -> str:
        """
        إنشاء القيد المحاسبي للتوزيع
        
        يتم إنشاء قيد محاسبي بنظام القيد المزدوج:
        - مدين: حساب كل مركز مستهدف
        - دائن: حساب المصدر
        """
        from core.domain.accounting.entities import JournalEntry, JournalLine
        from core.domain.shared.value_objects import AccountCode, Money
        from core.domain.accounting.value_objects import JournalEntryId
        from decimal import Decimal
        from datetime import datetime, timezone

        # إنشاء أسطر القيد
        lines = []

        # أسطر المدين (المراكز المستهدفة)
        for center_code, amount in allocation.allocations.items():
            if amount > 0:
                # الحصول على حساب المركز (يجب أن يكون معرفاً مسبقاً)
                account_code = self._get_center_account(center_code)
                lines.append(JournalLine(
                    account_code=AccountCode(account_code),
                    debit=Money(amount, "USD"),
                    credit=Money(Decimal('0'), "USD")
                ))

        # سطر الدائن (المركز المصدر)
        source_account = self._get_center_account(allocation.source_center_code)
        lines.append(JournalLine(
            account_code=AccountCode(source_account),
            debit=Money(Decimal('0'), "USD"),
            credit=Money(allocation.total_amount, "USD")
        ))

        # إنشاء القيد
        entry = JournalEntry(
            date=datetime.now(timezone.utc),
            description=f"توزيع مصروفات من {allocation.source_center_code} - {allocation.description or ''}",
            lines=lines
        )

        # حفظ القيد
        self._uow.journal_entries.save(entry)
        self._uow.flush()

        return str(entry.id)

    def _get_center_account(self, center_code: str) -> str:
        """
        الحصول على حساب الأستاذ المرتبط بالمركز
        
        TODO: يجب ربط المراكز بالحسابات في نظام شجرة الحسابات
        """
        # مؤقتاً: استخدام حساب افتراضي
        # في النظام الكامل، يجب ربط كل مركز بحساب محدد
        return "5060"  # حساب المصروفات الإدارية