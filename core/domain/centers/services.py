# core/domain/centers/services.py
"""
Cost & Profit Centers Services - خدمات مراكز التكلفة والربح
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime

from .entities import Center, CenterAllocation
from .value_objects import (
    CenterId, CenterCode, CenterType, CenterStatus,
    CenterBudget, AllocationRule, AllocationMethod,
    AllocationFrequency, CenterHierarchy
)
from .interfaces import (
    ICenterRepository,
    IAllocationRepository,
    IAllocationRuleRepository
)


class CenterService:
    """
    خدمة مراكز التكلفة والربح - تحتوي على منطق الأعمال
    """

    def __init__(
        self,
        center_repo: ICenterRepository,
        allocation_repo: IAllocationRepository,
        rule_repo: IAllocationRuleRepository
    ):
        self._center_repo = center_repo
        self._allocation_repo = allocation_repo
        self._rule_repo = rule_repo

    # =========================================================================
    # إدارة المركز
    # =========================================================================

    def create_center(
        self,
        code: str,
        name: str,
        center_type: CenterType,
        parent_code: Optional[str] = None,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        department: Optional[str] = None,
        budget: Optional[CenterBudget] = None,
        description: Optional[str] = None,
        created_by: str = "system"
    ) -> Center:
        """إنشاء مركز جديد"""
        # التحقق من عدم وجود كود مكرر
        if self._center_repo.exists_by_code(CenterCode(code)):
            raise ValueError(f"Center code already exists: {code}")

        # التحقق من وجود المركز الأب
        if parent_code:
            parent = self._center_repo.get_by_code(CenterCode(parent_code))
            if not parent:
                raise ValueError(f"Parent center not found: {parent_code}")

        center = Center.create(
            code=code,
            name=name,
            center_type=center_type,
            parent_code=parent_code,
            manager_id=manager_id,
            manager_name=manager_name,
            department=department,
            budget=budget,
            description=description,
            created_by=created_by
        )

        self._center_repo.save(center)
        return center

    def update_center(
        self,
        center_id: str,
        name: Optional[str] = None,
        center_type: Optional[CenterType] = None,
        parent_code: Optional[str] = None,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        department: Optional[str] = None,
        budget: Optional[CenterBudget] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        updated_by: str = "system"
    ) -> Center:
        """تحديث مركز"""
        center = self._center_repo.get_by_id(CenterId(center_id))
        if not center:
            raise ValueError(f"Center not found: {center_id}")

        center.update(
            name=name,
            center_type=center_type,
            parent_code=parent_code,
            manager_id=manager_id,
            manager_name=manager_name,
            department=department,
            budget=budget,
            description=description,
            notes=notes,
            tags=tags,
            updated_by=updated_by
        )

        self._center_repo.save(center)
        return center

    def activate_center(self, center_id: str, activated_by: str) -> Center:
        """تفعيل مركز"""
        center = self._center_repo.get_by_id(CenterId(center_id))
        if not center:
            raise ValueError(f"Center not found: {center_id}")

        center.activate(activated_by)
        self._center_repo.save(center)
        return center

    def suspend_center(self, center_id: str, suspended_by: str, reason: Optional[str] = None) -> Center:
        """تعليق مركز"""
        center = self._center_repo.get_by_id(CenterId(center_id))
        if not center:
            raise ValueError(f"Center not found: {center_id}")

        center.suspend(suspended_by, reason)
        self._center_repo.save(center)
        return center

    def close_center(self, center_id: str, closed_by: str, reason: Optional[str] = None) -> Center:
        """إغلاق مركز"""
        center = self._center_repo.get_by_id(CenterId(center_id))
        if not center:
            raise ValueError(f"Center not found: {center_id}")

        center.close(closed_by, reason)
        self._center_repo.save(center)
        return center

    def archive_center(self, center_id: str, archived_by: str) -> Center:
        """أرشفة مركز"""
        center = self._center_repo.get_by_id(CenterId(center_id))
        if not center:
            raise ValueError(f"Center not found: {center_id}")

        center.archive(archived_by)
        self._center_repo.save(center)
        return center

    def get_center_tree(self, root_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """الحصول على الشجرة الهرمية للمراكز"""
        return self._center_repo.get_tree(root_code)

    def get_center_with_children(self, code: str) -> Dict[str, Any]:
        """الحصول على مركز مع جميع فروعه"""
        return self._center_repo.get_center_with_children(code)

    # =========================================================================
    # إدارة الميزانية
    # =========================================================================

    def update_budget_usage(self, center_code: str, amount: Decimal) -> None:
        """تحديث استخدام الميزانية"""
        center = self._center_repo.get_by_code(CenterCode(center_code))
        if not center:
            raise ValueError(f"Center not found: {center_code}")

        center.update_budget_usage(amount)
        self._center_repo.save(center)

        # التحقق من تجاوز الميزانية
        if center.is_over_budget:
            from .events import CenterBudgetExceededEvent
            center.add_event(CenterBudgetExceededEvent(
                center_id=center.id,
                center_code=center.code,
                center_name=center.name,
                budget_limit=center.budget.total_budget,
                actual_usage=center.budget.used_amount,
                exceeded_by=center.budget.used_amount - center.budget.total_budget
            ))

    def set_budget(self, center_code: str, total_budget: Decimal, currency: str) -> Center:
        """تعيين ميزانية جديدة"""
        center = self._center_repo.get_by_code(CenterCode(center_code))
        if not center:
            raise ValueError(f"Center not found: {center_code}")

        old_budget = center.budget.total_budget if center.budget else Decimal('0')
        center.set_budget(total_budget, currency)
        self._center_repo.save(center)

        from .events import CenterBudgetUpdatedEvent
        center.add_event(CenterBudgetUpdatedEvent(
            center_id=center.id,
            center_code=center.code,
            center_name=center.name,
            old_budget=old_budget,
            new_budget=total_budget,
            updated_by="system"
        ))

        return center

    # =========================================================================
    # إدارة التوزيع
    # =========================================================================

    def create_allocation(
        self,
        source_center_code: str,
        target_center_codes: List[str],
        amount: Decimal,
        period_start: date,
        period_end: date,
        method: AllocationMethod,
        description: Optional[str] = None,
        created_by: str = "system"
    ) -> CenterAllocation:
        """إنشاء توزيع مصروفات"""
        # التحقق من وجود المصدر
        source = self._center_repo.get_by_code(CenterCode(source_center_code))
        if not source:
            raise ValueError(f"Source center not found: {source_center_code}")

        # التحقق من وجود الأهداف
        targets = []
        for code in target_center_codes:
            center = self._center_repo.get_by_code(CenterCode(code))
            if not center:
                raise ValueError(f"Target center not found: {code}")
            targets.append(center)

        # حساب التوزيع
        allocations = {}
        if method == AllocationMethod.EQUAL:
            per_center = amount / len(targets)
            for center in targets:
                allocations[center.code.value] = per_center
        else:
            # طرق أخرى سيتم تنفيذها باستخدام AllocationRule
            pass

        allocation = CenterAllocation(
            source_center_code=source_center_code,
            period_start=period_start,
            period_end=period_end,
            total_amount=amount,
            allocations=allocations,
            description=description,
            created_by=created_by
        )

        self._allocation_repo.save(allocation)
        return allocation

    def post_allocation(self, allocation_id: str, posted_by: str, journal_entry_id: str) -> CenterAllocation:
        """ترحيل توزيع المصروفات"""
        allocation = self._allocation_repo.get_by_id(allocation_id)
        if not allocation:
            raise ValueError(f"Allocation not found: {allocation_id}")

        allocation.post(posted_by, journal_entry_id)
        self._allocation_repo.save(allocation)

        # تحديث استخدام الميزانية للمراكز المستهدفة
        for center_code, amount in allocation.allocations.items():
            self.update_budget_usage(center_code, amount)

        return allocation

    # =========================================================================
    # إدارة قواعد التوزيع
    # =========================================================================

    def create_allocation_rule(
        self,
        name: str,
        source_center_code: str,
        target_center_codes: List[str],
        method: AllocationMethod,
        percentage: Optional[Decimal] = None,
        fixed_amount: Optional[Decimal] = None,
        weights: Optional[Dict[str, Decimal]] = None,
        frequency: AllocationFrequency = AllocationFrequency.MONTHLY,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        description: Optional[str] = None
    ) -> AllocationRule:
        """إنشاء قاعدة توزيع"""
        rule = AllocationRule(
            id=str(uuid4()),
            name=name,
            source_center_code=source_center_code,
            target_center_codes=target_center_codes,
            method=method,
            percentage=percentage,
            fixed_amount=fixed_amount,
            weights=weights,
            frequency=frequency,
            valid_from=valid_from,
            valid_to=valid_to,
            description=description
        )

        self._rule_repo.save(rule)
        return rule

    def run_allocation_rule(self, rule_id: str, period_start: date, period_end: date) -> CenterAllocation:
        """تنفيذ قاعدة توزيع"""
        rule = self._rule_repo.get_by_id(rule_id)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        # الحصول على المصدر
        source = self._center_repo.get_by_code(CenterCode(rule.source_center_code))
        if not source:
            raise ValueError(f"Source center not found: {rule.source_center_code}")

        # حساب التوزيع
        total_amount = Decimal('0')  # يجب حسابه من المصدر في الفترة

        allocation = self.create_allocation(
            source_center_code=rule.source_center_code,
            target_center_codes=rule.target_center_codes,
            amount=total_amount,
            period_start=period_start,
            period_end=period_end,
            method=rule.method,
            description=f"Auto allocation: {rule.name}",
            created_by="system"
        )

        return allocation

    # =========================================================================
    # التقارير والإحصائيات
    # =========================================================================

    def get_center_summary(self, center_code: str, from_date: date, to_date: date) -> Dict[str, Any]:
        """الحصول على ملخص مركز في فترة"""
        center = self._center_repo.get_by_code(CenterCode(center_code))
        if not center:
            raise ValueError(f"Center not found: {center_code}")

        # جلب التوزيعات
        allocations = self._allocation_repo.list_by_center(
            center_code=center_code,
            from_date=from_date,
            to_date=to_date
        )

        total_allocated = sum(a.total_amount for a in allocations if a.is_posted)

        return {
            'center': center.to_dict(),
            'total_allocated': float(total_allocated),
            'allocations_count': len(allocations),
            'budget_utilization': float(center.budget_utilization) if center.budget_utilization else 0,
            'is_over_budget': center.is_over_budget
        }

    def get_centers_hierarchy(self) -> Dict[str, Any]:
        """الحصول على التسلسل الهرمي الكامل للمراكز"""
        return self._center_repo.get_tree()


# استيراد مفقود
from uuid import uuid4