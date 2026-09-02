"""
Postgres Journal Entry Repository - مستودع قيود اليومية
الإصدار: 2.0.0 - Enterprise Edition

الميزات:
    1. دعم كامل لـ CQRS (Command/Query Separation)
    2. Optimistic Locking مع التحقق من الإصدار
    3. Pagination المتقدم مع Count التلقائي
    4. فلاتر مرنة (التاريخ، الحالة، النوع، المستخدم)
    5. البحث عن القيود العكسية (Reversal)
    6. تحويل تلقائي بين Domain و ORM
    7. معالجة الأحداث (Domain Events)
    8. دعم المعاملات (Transactions)
    9. تجنب N+1 Queries
    10. دعم العملات المتعددة
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, between, desc, asc, func, text
from sqlalchemy.exc import StaleDataError

from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import (
    JournalEntryId, TransactionType, PeriodReference
)
from core.domain.accounting.interfaces import IJournalEntryRepository
from core.domain.accounting.exceptions import (
    EntryNotFoundError, ConcurrentModificationError
)
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.fiscal.value_objects import FiscalPeriodReference

from core.infrastructure.db.models.account_model import (
    JournalEntryModel,
    JournalLineModel,
    AccountModel
)


class PostgresJournalEntryRepository(IJournalEntryRepository):
    """
    تنفيذ PostgreSQL لمستودع قيود اليومية
    
    المبادئ:
        1. كل عملية حفظ تتحقق من الإصدار (Optimistic Locking)
        2. تستخدم الـ Session لإدارة دورة الحياة
        3. تحويل تلقائي بين Domain و ORM
        4. معالجة الأحداث (Domain Events) عند الحفظ
        5. دعم التحميل الكسول (Lazy Loading) للعلاقات
    """
    
    def __init__(self, session: Session):
        """
        تهيئة المستودع
        
        Args:
            session: جلسة SQLAlchemy
        """
        self._session = session
        self._event_bus = None  # سيتم حقنه لاحقاً
    
    def set_event_bus(self, event_bus):
        """حقن ناقل الأحداث"""
        self._event_bus = event_bus
    
    # =========================================================================
    # العمليات الأساسية (CRUD)
    # =========================================================================
    
    def save(self, entry: JournalEntry) -> None:
        """
        حفظ قيد يومية (جديد أو محدث)
        
        الميزات:
            1. تحويل Domain → ORM
            2. التحقق من الإصدار (Optimistic Locking)
            3. بث الأحداث (Domain Events)
            4. حفظ الأسطر المرتبطة
        
        Args:
            entry: كيان القيد من Domain Layer
        
        Raises:
            ConcurrentModificationError: إذا تم تعديل القيد بواسطة مستخدم آخر
        """
        # 1. التحقق من وجود القيد في قاعدة البيانات
        existing = self._session.query(JournalEntryModel).filter(
            JournalEntryModel.id == entry.id.value
        ).first()
        
        if existing:
            # 2. التحقق من الإصدار (Optimistic Locking)
            if existing.version != entry.version:
                raise ConcurrentModificationError(
                    aggregate_type="JournalEntry",
                    aggregate_id=str(entry.id),
                    expected_version=entry.version,
                    actual_version=existing.version
                )
            
            # 3. تحديث القيد الموجود
            self._update_existing(existing, entry)
        else:
            # 4. إنشاء قيد جديد
            self._create_new(entry)
        
        # 5. حفظ التغييرات
        self._session.flush()
        
        # 6. بث الأحداث (Domain Events)
        events = entry.pull_events()
        if events and self._event_bus:
            self._event_bus.dispatch_many(events)
    
    def get_by_id(self, entry_id: JournalEntryId) -> Optional[JournalEntry]:
        """
        الحصول على قيد بواسطة المعرف
        
        Args:
            entry_id: معرف القيد
        
        Returns:
            Optional[JournalEntry]: كيان القيد أو None
        """
        # تحميل مع العلاقات لتجنب N+1
        model = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines).selectinload(JournalLineModel.account)
        ).filter(
            JournalEntryModel.id == entry_id.value
        ).first()
        
        return self._to_entity(model) if model else None
    
    def get_by_id_or_fail(self, entry_id: JournalEntryId) -> JournalEntry:
        """
        الحصول على قيد أو رفع استثناء
        
        Args:
            entry_id: معرف القيد
        
        Returns:
            JournalEntry: كيان القيد
        
        Raises:
            EntryNotFoundError: إذا لم يتم العثور على القيد
        """
        entry = self.get_by_id(entry_id)
        if not entry:
            raise EntryNotFoundError(str(entry_id))
        return entry
    
    def get_by_reference(self, reference_number: str) -> Optional[JournalEntry]:
        """
        الحصول على قيد بواسطة رقم المرجع
        
        Args:
            reference_number: رقم المرجع (مثل رقم الفاتورة)
        
        Returns:
            Optional[JournalEntry]: كيان القيد أو None
        """
        model = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            JournalEntryModel.reference == reference_number
        ).first()
        
        return self._to_entity(model) if model else None
    
    # =========================================================================
    # استعلامات القيود المرحلة والمسودة
    # =========================================================================
    
    def get_posted_entries(
        self,
        from_date: date,
        to_date: date,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JournalEntry]:
        """
        الحصول على القيود المرحلة في نطاق زمني
        
        Args:
            from_date: تاريخ البداية
            to_date: تاريخ النهاية
            transaction_type: نوع المعاملة (اختياري)
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[JournalEntry]: قائمة القيود المرحلة
        """
        query = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            JournalEntryModel.is_posted == True,
            between(
                func.date(JournalEntryModel.entry_date),
                from_date,
                to_date
            )
        )
        
        if transaction_type:
            query = query.filter(
                JournalEntryModel.transaction_type == transaction_type.name
            )
        
        # ترتيب تنازلي حسب التاريخ
        query = query.order_by(
            desc(JournalEntryModel.entry_date),
            desc(JournalEntryModel.created_at)
        )
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    def get_draft_entries(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JournalEntry]:
        """
        الحصول على القيود المسودة (غير المرحلة)
        
        Args:
            user_id: معرف المستخدم (اختياري - للتصفية)
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[JournalEntry]: قائمة القيود المسودة
        """
        query = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            JournalEntryModel.is_posted == False
        )
        
        if user_id:
            query = query.filter(
                JournalEntryModel.created_by == user_id
            )
        
        # ترتيب تنازلي حسب تاريخ الإنشاء
        query = query.order_by(
            desc(JournalEntryModel.created_at)
        )
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    def get_unposted_entries_in_period(self, period) -> List[JournalEntry]:
        """
        الحصول على القيود غير المرحلة في فترة مالية
        
        Args:
            period: كائن FiscalPeriod
        
        Returns:
            List[JournalEntry]: قائمة القيود غير المرحلة
        """
        start_date = period.start_date
        end_date = period.end_date
        
        models = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            JournalEntryModel.is_posted == False,
            between(
                func.date(JournalEntryModel.entry_date),
                start_date,
                end_date
            )
        ).order_by(
            asc(JournalEntryModel.entry_date)
        ).all()
        
        return [self._to_entity(m) for m in models]
    
    def count_unposted_in_period(self, period) -> int:
        """
        حساب عدد القيود غير المرحلة في فترة مالية
        
        Args:
            period: كائن FiscalPeriod
        
        Returns:
            int: عدد القيود غير المرحلة
        """
        start_date = period.start_date
        end_date = period.end_date
        
        return self._session.query(JournalEntryModel).filter(
            JournalEntryModel.is_posted == False,
            between(
                func.date(JournalEntryModel.entry_date),
                start_date,
                end_date
            )
        ).count()
    
    # =========================================================================
    # استعلامات القيود العكسية (Reversal)
    # =========================================================================
    
    def exists_reversal(self, original_entry_id: JournalEntryId) -> bool:
        """
        التحقق من وجود قيد عكسي للقيد الأصلي
        
        Args:
            original_entry_id: معرف القيد الأصلي
        
        Returns:
            bool: True إذا كان هناك قيد عكسي
        """
        return self._session.query(JournalEntryModel).filter(
            JournalEntryModel.reverses_entry_id == original_entry_id.value
        ).count() > 0
    
    def get_reversal_for(self, original_entry_id: JournalEntryId) -> Optional[JournalEntry]:
        """
        الحصول على القيد العكسي لقيد أصلي
        
        Args:
            original_entry_id: معرف القيد الأصلي
        
        Returns:
            Optional[JournalEntry]: القيد العكسي أو None
        """
        model = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            JournalEntryModel.reverses_entry_id == original_entry_id.value
        ).first()
        
        return self._to_entity(model) if model else None
    
    def get_entries_by_reference(self, reference: str) -> List[JournalEntry]:
        """
        الحصول على القيود المرتبطة بمرجع معين
        
        Args:
            reference: رقم المرجع
        
        Returns:
            List[JournalEntry]: قائمة القيود
        """
        models = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            JournalEntryModel.reference == reference
        ).order_by(
            asc(JournalEntryModel.entry_date)
        ).all()
        
        return [self._to_entity(m) for m in models]
    
    # =========================================================================
    # استعلامات متقدمة
    # =========================================================================
    
    def get_entries_in_date_range(
        self,
        start_date: date,
        end_date: date,
        include_unposted: bool = True
    ) -> List[JournalEntry]:
        """
        الحصول على القيود في نطاق زمني
        
        Args:
            start_date: تاريخ البداية
            end_date: تاريخ النهاية
            include_unposted: تضمين القيود غير المرحلة
        
        Returns:
            List[JournalEntry]: قائمة القيود
        """
        query = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            between(
                func.date(JournalEntryModel.entry_date),
                start_date,
                end_date
            )
        )
        
        if not include_unposted:
            query = query.filter(JournalEntryModel.is_posted == True)
        
        models = query.order_by(
            asc(JournalEntryModel.entry_date)
        ).all()
        
        return [self._to_entity(m) for m in models]
    
    def count_by_period(self, period: PeriodReference) -> int:
        """
        حساب عدد القيود في فترة مالية
        
        Args:
            period: مرجع الفترة المالية
        
        Returns:
            int: عدد القيود
        """
        # تحويل المرجع إلى تواريخ
        year = period.get_year()
        month = period.get_month()
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        return self._session.query(JournalEntryModel).filter(
            between(
                func.date(JournalEntryModel.entry_date),
                start_date,
                end_date
            )
        ).count()
    
    def get_by_account(
        self,
        account_code: AccountCode,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JournalEntry]:
        """
        الحصول على القيود التي تحتوي على حساب معين
        
        Args:
            account_code: كود الحساب
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[JournalEntry]: قائمة القيود
        """
        # الحصول على الحساب من قاعدة البيانات
        account = self._session.query(AccountModel).filter(
            AccountModel.code == account_code.code
        ).first()
        
        if not account:
            return []
        
        # بناء الاستعلام
        query = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).join(
            JournalLineModel,
            JournalLineModel.journal_entry_id == JournalEntryModel.id
        ).filter(
            JournalLineModel.account_id == account.id
        )
        
        if from_date:
            query = query.filter(
                func.date(JournalEntryModel.entry_date) >= from_date
            )
        
        if to_date:
            query = query.filter(
                func.date(JournalEntryModel.entry_date) <= to_date
            )
        
        # ترتيب تنازلي حسب التاريخ
        query = query.order_by(
            desc(JournalEntryModel.entry_date)
        ).distinct()
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    def search(
        self,
        search_text: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JournalEntry]:
        """
        البحث في القيود بالنص الحر
        
        Args:
            search_text: النص المطلوب البحث عنه
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[JournalEntry]: قائمة القيود المطابقة
        """
        search = f"%{search_text}%"
        
        query = self._session.query(JournalEntryModel).options(
            selectinload(JournalEntryModel.lines)
        ).filter(
            or_(
                JournalEntryModel.description.ilike(search),
                JournalEntryModel.reference.ilike(search),
                JournalEntryModel.transaction_type.ilike(search)
            )
        )
        
        if from_date:
            query = query.filter(
                func.date(JournalEntryModel.entry_date) >= from_date
            )
        
        if to_date:
            query = query.filter(
                func.date(JournalEntryModel.entry_date) <= to_date
            )
        
        # ترتيب تنازلي حسب التاريخ
        query = query.order_by(
            desc(JournalEntryModel.entry_date)
        )
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    # =========================================================================
    # العمليات الإدارية
    # =========================================================================
    
    def delete_draft(self, entry_id: JournalEntryId) -> bool:
        """
        حذف قيد مسودة (غير مرحل)
        
        Args:
            entry_id: معرف القيد
        
        Returns:
            bool: نجاح العملية
        """
        model = self._session.query(JournalEntryModel).filter(
            JournalEntryModel.id == entry_id.value,
            JournalEntryModel.is_posted == False
        ).first()
        
        if not model:
            return False
        
        # حذف الأسطر المرتبطة (Cascade سيقوم بذلك)
        self._session.delete(model)
        self._session.flush()
        return True
    
    def batch_save(self, entries: List[JournalEntry]) -> int:
        """
        حفظ مجموعة قيود دفعة واحدة
        
        Args:
            entries: قائمة القيود
        
        Returns:
            int: عدد القيود المحفوظة
        """
        saved_count = 0
        for entry in entries:
            self.save(entry)
            saved_count += 1
        return saved_count
    
    # =========================================================================
    # إحصائيات وتقارير
    # =========================================================================
    
    def get_statistics(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        الحصول على إحصائيات القيود
        
        Args:
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
        
        Returns:
            Dict[str, Any]: إحصائيات القيود
        """
        query = self._session.query(JournalEntryModel)
        
        if from_date:
            query = query.filter(
                func.date(JournalEntryModel.entry_date) >= from_date
            )
        
        if to_date:
            query = query.filter(
                func.date(JournalEntryModel.entry_date) <= to_date
            )
        
        total = query.count()
        posted = query.filter(JournalEntryModel.is_posted == True).count()
        draft = total - posted
        
        # إجمالي المبالغ (باستخدام الـ Subquery)
        total_debit = self._session.query(
            func.sum(JournalLineModel.debit_amount)
        ).join(
            JournalEntryModel,
            JournalLineModel.journal_entry_id == JournalEntryModel.id
        ).filter(
            JournalEntryModel.is_posted == True
        ).scalar() or Decimal('0')
        
        total_credit = self._session.query(
            func.sum(JournalLineModel.credit_amount)
        ).join(
            JournalEntryModel,
            JournalLineModel.journal_entry_id == JournalEntryModel.id
        ).filter(
            JournalEntryModel.is_posted == True
        ).scalar() or Decimal('0')
        
        return {
            'total_entries': total,
            'posted_entries': posted,
            'draft_entries': draft,
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'difference': float(abs(total_debit - total_credit)),
            'is_balanced': abs(total_debit - total_credit) < Decimal('0.01')
        }
    
    # =========================================================================
    # دوال التحويل (Converters)
    # =========================================================================
    
    def _to_model(self, entity: JournalEntry) -> JournalEntryModel:
        """
        تحويل Domain Entity → ORM Model
        
        Args:
            entity: كيان القيد من Domain Layer
        
        Returns:
            JournalEntryModel: نموذج ORM
        """
        # إنشاء نموذج القيد
        model = JournalEntryModel(
            id=entity.id.value,
            entry_date=entity.date,
            description=entity.description,
            is_posted=entity.is_posted,
            posted_at=entity.posted_at,
            posted_by=entity.posted_by,
            reversed_entry_id=entity.reversed_entry_id.value if entity.reversed_entry_id else None,
            reverses_entry_id=entity.reverses_entry_id.value if entity.reverses_entry_id else None,
            created_at=entity.created_at,
            created_by=entity.created_by,
            version=entity.version
        )
        
        # إضافة الأسطر
        model.lines = []
        for line in entity.lines:
            # الحصول على الحساب من قاعدة البيانات
            account = self._session.query(AccountModel).filter(
                AccountModel.code == line.account_code.code
            ).first()
            
            if not account:
                raise ValueError(f"Account {line.account_code.code} not found")
            
            line_model = JournalLineModel(
                id=line.line_id,
                account_id=account.id,
                debit_amount=line.debit.amount,
                credit_amount=line.credit.amount,
                currency=line.currency,
                description=f"Line {len(model.lines) + 1}",
                line_order=len(model.lines)
            )
            model.lines.append(line_model)
        
        return model
    
    def _to_entity(self, model: JournalEntryModel) -> JournalEntry:
        """
        تحويل ORM Model → Domain Entity
        
        Args:
            model: نموذج ORM
        
        Returns:
            JournalEntry: كيان القيد من Domain Layer
        """
        if not model:
            return None
        
        # تحويل الأسطر
        lines = []
        for line_model in sorted(model.lines, key=lambda l: l.line_order):
            account = line_model.account
            line_currency = line_model.currency or (account.currency if account else "USD")
            lines.append(JournalLine(
                account_code=AccountCode(account.code),
                debit=Money(
                    line_model.debit_amount,
                    line_currency
                ),
                credit=Money(
                    line_model.credit_amount,
                    line_currency
                ),
                line_id=line_model.id
            ))
        
        # إنشاء كيان القيد
        return JournalEntry(
            id=JournalEntryId.from_string(str(model.id)),
            date=model.entry_date,
            description=model.description,
            lines=lines,
            is_posted=model.is_posted,
            posted_at=model.posted_at,
            posted_by=model.posted_by,
            reversed_entry_id=JournalEntryId.from_string(str(model.reversed_entry_id)) if model.reversed_entry_id else None,
            reverses_entry_id=JournalEntryId.from_string(str(model.reverses_entry_id)) if model.reverses_entry_id else None,
            created_at=model.created_at,
            created_by=model.created_by,
            version=model.version
        )
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def _update_existing(self, model: JournalEntryModel, entity: JournalEntry) -> None:
        """
        تحديث قيد موجود
        
        Args:
            model: نموذج ORM الحالي
            entity: كيان القيد الجديد
        """
        # تحديث الحقول الأساسية
        model.entry_date = entity.date
        model.description = entity.description
        model.is_posted = entity.is_posted
        model.posted_at = entity.posted_at
        model.posted_by = entity.posted_by
        model.reversed_entry_id = entity.reversed_entry_id.value if entity.reversed_entry_id else None
        model.reverses_entry_id = entity.reverses_entry_id.value if entity.reverses_entry_id else None
        model.version = entity.version
        
        # تحديث الأسطر
        # حذف الأسطر القديمة
        for line in model.lines:
            self._session.delete(line)
        model.lines.clear()
        
        # إضافة الأسطر الجديدة
        for line in entity.lines:
            account = self._session.query(AccountModel).filter(
                AccountModel.code == line.account_code.code
            ).first()
            
            if not account:
                raise ValueError(f"Account {line.account_code.code} not found")
            
            line_model = JournalLineModel(
                id=line.line_id,
                account_id=account.id,
                debit_amount=line.debit.amount,
                credit_amount=line.credit.amount,
                currency=line.currency,
                description=f"Line {len(model.lines) + 1}",
                line_order=len(model.lines)
            )
            model.lines.append(line_model)
    
    def _create_new(self, entity: JournalEntry) -> None:
        """
        إنشاء قيد جديد
        
        Args:
            entity: كيان القيد الجديد
        """
        model = self._to_model(entity)
        self._session.add(model)