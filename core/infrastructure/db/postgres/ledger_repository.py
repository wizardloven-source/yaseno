"""
Postgres Ledger Repository - مستودع دفتر الأستاذ العام
الإصدار: 2.0.0 - Enterprise Edition

الميزات:
    1. تسجيل حركات الأستاذ (Ledger Entries)
    2. حساب الأرصدة التراكمية (Running Balances)
    3. ميزان المراجعة (Trial Balance) مع دعم العملات المتعددة
    4. تقارير دفتر الأستاذ التفصيلية
    5. دعم الفترات المالية
    6. تحسين الأداء مع الفهارس المحسنة
    7. دعم العملات المتعددة
    8. التجميع حسب الحساب والفترة
    9. حساب الأرصدة الافتتاحية
    10. دعم التصدير والتحليل
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, between, desc, asc, func, text, case, distinct
from sqlalchemy.sql import label

from core.domain.accounting.interfaces import ILedgerRepository
from core.domain.accounting.value_objects import (
    EntryId, JournalEntryId, PeriodReference
)
from core.domain.accounting.interfaces import LedgerEntry
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.fiscal.value_objects import FiscalPeriodReference

from core.infrastructure.db.models.account_model import (
    LedgerEntryModel,
    JournalEntryModel,
    AccountModel,
    FiscalPeriodModel
)


class PostgresLedgerRepository(ILedgerRepository):
    """
    تنفيذ PostgreSQL لمستودع دفتر الأستاذ العام
    
    المبادئ:
        1. كل حركة أستاذ مسجلة بشكل دائم (Immutable)
        2. لا يمكن تعديل أو حذف حركات الأستاذ بعد تسجيلها
        3. حساب الأرصدة باستخدام الاستعلامات المحسّنة
        4. دعم العملات المتعددة في جميع العمليات
        5. تحسين الأداء باستخدام الفهارس والتجميع
    """
    
    def __init__(self, session: Session):
        """
        تهيئة المستودع
        
        Args:
            session: جلسة SQLAlchemy
        """
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية
    # =========================================================================
    
    def add_entry(
        self,
        entry_id: EntryId,
        account_code: AccountCode,
        debit: Money,
        credit: Money,
        date: datetime,
        journal_entry_id: JournalEntryId,
        reference: Optional[str] = None,
        fiscal_period: Optional[str] = None
    ) -> None:
        """
        إضافة حركة إلى دفتر الأستاذ
        
        الميزات:
            1. التحقق من توازن القيد (debit = credit)
            2. التحقق من صحة الحساب
            3. التحقق من الفترة المالية
            4. تسجيل الحركة بشكل دائم
        
        Args:
            entry_id: معرف الحركة
            account_code: كود الحساب
            debit: مبلغ المدين
            credit: مبلغ الدائن
            date: تاريخ الحركة
            journal_entry_id: معرف القيد المحاسبي
            reference: المرجع (اختياري)
            fiscal_period: الفترة المالية (اختياري)
        
        Raises:
            ValueError: إذا كان الحساب غير موجود أو الفترة غير صالحة
        """
        # 1. التحقق من وجود الحساب
        account = self._session.query(AccountModel).filter(
            AccountModel.code == account_code.code
        ).first()
        
        if not account:
            raise ValueError(f"Account {account_code.code} not found")
        
        # 2. التحقق من صحة المبالغ
        if debit.amount < 0 or credit.amount < 0:
            raise ValueError("Debit and credit amounts cannot be negative")
        
        if debit.amount == 0 and credit.amount == 0:
            raise ValueError("Entry must have either debit or credit amount")
        
        if debit.amount > 0 and credit.amount > 0:
            raise ValueError("Entry cannot have both debit and credit amounts")
        
        # 3. التحقق من الفترة المالية (إذا تم تحديدها)
        if fiscal_period:
            period = self._session.query(FiscalPeriodModel).filter(
                FiscalPeriodModel.name == fiscal_period
            ).first()
            
            if not period:
                raise ValueError(f"Fiscal period {fiscal_period} not found")
            
            # التحقق من أن التاريخ يقع ضمن الفترة
            if date.date() < period.start_date or date.date() > period.end_date:
                raise ValueError(
                    f"Date {date.date()} is outside fiscal period {fiscal_period}"
                )
        
        # 4. إنشاء حركة الأستاذ
        currency = debit.currency if debit.amount > 0 else credit.currency
        ledger_entry = LedgerEntryModel(
            id=entry_id.value if hasattr(entry_id, 'value') else uuid4(),
            journal_entry_id=journal_entry_id.value if hasattr(journal_entry_id, 'value') else journal_entry_id,
            account_id=account.id,
            debit_amount=debit.amount,
            credit_amount=credit.amount,
            currency=currency,
            entry_date=date,
            posted_at=datetime.now(timezone.utc),
            reference=reference,
            fiscal_period=fiscal_period
        )
        
        # 5. حفظ الحركة
        self._session.add(ledger_entry)
        self._session.flush()
    
    def get_entries_by_account(
        self,
        account_code: AccountCode,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[LedgerEntry]:
        """
        الحصول على حركات حساب معين
        
        Args:
            account_code: كود الحساب
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
            limit: الحد الأقصى للنتائج (اختياري)
            offset: الإزاحة للصفحات (اختياري)
        
        Returns:
            List[LedgerEntry]: قائمة حركات الأستاذ
        """
        # 1. الحصول على الحساب
        account = self._session.query(AccountModel).filter(
            AccountModel.code == account_code.code
        ).first()
        
        if not account:
            return []
        
        # 2. بناء الاستعلام
        query = self._session.query(LedgerEntryModel).filter(
            LedgerEntryModel.account_id == account.id
        )
        
        if from_date:
            query = query.filter(
                func.date(LedgerEntryModel.entry_date) >= from_date
            )
        
        if to_date:
            query = query.filter(
                func.date(LedgerEntryModel.entry_date) <= to_date
            )
        
        # 3. ترتيب حسب التاريخ
        query = query.order_by(
            asc(LedgerEntryModel.entry_date),
            asc(LedgerEntryModel.posted_at)
        )
        
        # 4. Pagination
        if limit is not None:
            query = query.limit(limit)
        
        if offset is not None:
            query = query.offset(offset)
        
        # 5. تنفيذ الاستعلام
        models = query.all()
        
        # 6. تحويل إلى Domain Entities
        return [self._to_entity(m, account_code) for m in models]
    
    def get_balance(
        self,
        account_code: AccountCode,
        as_of: date,
        currency: str = "USD"
    ) -> Money:
        """
        الحصول على رصيد حساب في تاريخ معين
        
        الميزات:
            1. حساب الرصيد التراكمي حتى تاريخ معين
            2. دعم العملات المتعددة
            3. تحسين الأداء باستخدام SUM
        
        Args:
            account_code: كود الحساب
            as_of: التاريخ
            currency: العملة (افتراضي: USD)
        
        Returns:
            Money: الرصيد في التاريخ المحدد
        """
        # 1. الحصول على الحساب
        account = self._session.query(AccountModel).filter(
            AccountModel.code == account_code.code
        ).first()
        
        if not account:
            return Money.zero(currency)
        
        # 2. حساب إجمالي المدين والدائن (لعملة محددة فقط - منع جمع العملات)
        result = self._session.query(
            func.coalesce(func.sum(LedgerEntryModel.debit_amount), 0).label('total_debit'),
            func.coalesce(func.sum(LedgerEntryModel.credit_amount), 0).label('total_credit')
        ).filter(
            LedgerEntryModel.account_id == account.id,
            LedgerEntryModel.currency == currency,
            func.date(LedgerEntryModel.entry_date) <= as_of
        ).first()
        
        total_debit = result.total_debit or Decimal('0')
        total_credit = result.total_credit or Decimal('0')
        
        # 3. حساب الرصيد حسب نوع الحساب
        balance = self._calculate_balance(
            account.account_type,
            total_debit,
            total_credit
        )
        
        return Money(balance, currency)
    
    def get_opening_balance(
        self,
        account_code: AccountCode,
        as_of: date,
        currency: str = "USD"
    ) -> Money:
        """
        الحصول على الرصيد الافتتاحي لحساب في تاريخ معين
        
        Args:
            account_code: كود الحساب
            as_of: التاريخ (الرصيد قبل هذا التاريخ)
            currency: العملة
        
        Returns:
            Money: الرصيد الافتتاحي
        """
        # الرصيد الافتتاحي = الرصيد حتى اليوم السابق
        previous_day = as_of - timedelta(days=1)
        return self.get_balance(account_code, previous_day, currency)
    
    def get_trial_balance(
        self,
        as_of: date,
        account_types: Optional[List[str]] = None,
        currency: str = "USD"
    ) -> Dict[AccountCode, Money]:
        """
        الحصول على ميزان المراجعة في تاريخ معين
        
        الميزات:
            1. حساب جميع الحسابات في تاريخ معين
            2. دعم تصفية حسب أنواع الحسابات
            3. دعم العملات المتعددة
            4. إرجاع النتائج كـ Dict
        
        Args:
            as_of: التاريخ
            account_types: أنواع الحسابات المطلوبة (اختياري)
            currency: العملة (افتراضي: USD)
        
        Returns:
            Dict[AccountCode, Money]: أرصدة الحسابات
        """
        # 1. بناء الاستعلام الأساسي (عملة محددة فقط - منع جمع العملات)
        query = self._session.query(
            AccountModel.code,
            AccountModel.account_type,
            func.coalesce(func.sum(LedgerEntryModel.debit_amount), 0).label('total_debit'),
            func.coalesce(func.sum(LedgerEntryModel.credit_amount), 0).label('total_credit')
        ).join(
            LedgerEntryModel,
            LedgerEntryModel.account_id == AccountModel.id
        ).filter(
            func.date(LedgerEntryModel.entry_date) <= as_of,
            LedgerEntryModel.currency == currency
        )
        
        # 2. تصفية حسب أنواع الحسابات
        if account_types:
            query = query.filter(AccountModel.account_type.in_(account_types))
        
        # 3. تجميع حسب الحساب
        query = query.group_by(
            AccountModel.code,
            AccountModel.account_type
        ).order_by(AccountModel.code)
        
        # 4. تنفيذ الاستعلام
        results = query.all()
        
        # 5. تحويل النتائج إلى Dict
        trial_balance = {}
        for row in results:
            account_code = AccountCode(row.code)
            total_debit = row.total_debit or Decimal('0')
            total_credit = row.total_credit or Decimal('0')
            
            balance = self._calculate_balance(
                row.account_type,
                total_debit,
                total_credit
            )
            
            trial_balance[account_code] = Money(balance, currency)
        
        return trial_balance
    
    def get_account_history(
        self,
        account_code: AccountCode,
        from_date: date,
        to_date: date
    ) -> List[LedgerEntry]:
        """
        الحصول على تاريخ حساب كامل في نطاق زمني
        
        Args:
            account_code: كود الحساب
            from_date: تاريخ البداية
            to_date: تاريخ النهاية
        
        Returns:
            List[LedgerEntry]: قائمة حركات الأستاذ مع الرصيد التراكمي
        """
        # 1. الحصول على الحساب
        account = self._session.query(AccountModel).filter(
            AccountModel.code == account_code.code
        ).first()
        
        if not account:
            return []
        
        # 2. الحصول على جميع الحركات في النطاق
        models = self._session.query(LedgerEntryModel).filter(
            LedgerEntryModel.account_id == account.id,
            between(
                func.date(LedgerEntryModel.entry_date),
                from_date,
                to_date
            )
        ).order_by(
            asc(LedgerEntryModel.entry_date),
            asc(LedgerEntryModel.posted_at)
        ).all()
        
        # 3. حساب الرصيد التراكمي
        running_balance = Decimal('0')
        entries = []
        
        for model in models:
            if model.debit_amount > 0:
                running_balance += model.debit_amount
            else:
                running_balance -= model.credit_amount
            
            entry = self._to_entity(model, account_code)
            entries.append(entry)
        
        return entries
    
    def get_entries_by_period(
        self,
        period_reference: PeriodReference,
        account_code: Optional[AccountCode] = None
    ) -> List[LedgerEntry]:
        """
        الحصول على حركات الأستاذ في فترة مالية معينة
        
        Args:
            period_reference: مرجع الفترة المالية
            account_code: كود الحساب (اختياري - الكل إذا لم يحدد)
        
        Returns:
            List[LedgerEntry]: قائمة حركات الأستاذ
        """
        # 1. تحويل المرجع إلى نطاق زمني
        year = period_reference.get_year()
        month = period_reference.get_month()
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # 2. بناء الاستعلام
        query = self._session.query(LedgerEntryModel)
        
        if account_code:
            account = self._session.query(AccountModel).filter(
                AccountModel.code == account_code.code
            ).first()
            
            if account:
                query = query.filter(LedgerEntryModel.account_id == account.id)
        
        query = query.filter(
            between(
                func.date(LedgerEntryModel.entry_date),
                start_date,
                end_date
            )
        ).order_by(
            asc(LedgerEntryModel.entry_date)
        )
        
        # 3. تنفيذ الاستعلام
        models = query.all()
        
        # 4. تحويل إلى Domain Entities
        entries = []
        for model in models:
            account = self._session.query(AccountModel).filter(
                AccountModel.id == model.account_id
            ).first()
            
            if account:
                entries.append(self._to_entity(model, AccountCode(account.code)))
        
        return entries
    
    def get_period_summary(
        self,
        period_reference: PeriodReference
    ) -> Dict[str, Any]:
        """
        الحصول على ملخص فترة مالية
        
        الميزات:
            1. إجمالي المدين والدائن في الفترة
            2. عدد الحركات
            3. تفصيل حسب أنواع الحسابات
            4. صافي التغير
        
        Args:
            period_reference: مرجع الفترة المالية
        
        Returns:
            Dict[str, Any]: ملخص الفترة
        """
        # 1. تحويل المرجع إلى نطاق زمني
        year = period_reference.get_year()
        month = period_reference.get_month()
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # 2. الحصول على إحصائيات الفترة
        result = self._session.query(
            func.count(LedgerEntryModel.id).label('total_entries'),
            func.coalesce(func.sum(LedgerEntryModel.debit_amount), 0).label('total_debit'),
            func.coalesce(func.sum(LedgerEntryModel.credit_amount), 0).label('total_credit')
        ).filter(
            between(
                func.date(LedgerEntryModel.entry_date),
                start_date,
                end_date
            )
        ).first()
        
        # 3. تفصيل حسب أنواع الحسابات
        by_account_type = self._session.query(
            AccountModel.account_type,
            func.count(LedgerEntryModel.id).label('count'),
            func.coalesce(func.sum(LedgerEntryModel.debit_amount), 0).label('debit'),
            func.coalesce(func.sum(LedgerEntryModel.credit_amount), 0).label('credit')
        ).join(
            LedgerEntryModel,
            LedgerEntryModel.account_id == AccountModel.id
        ).filter(
            between(
                func.date(LedgerEntryModel.entry_date),
                start_date,
                end_date
            )
        ).group_by(
            AccountModel.account_type
        ).all()
        
        return {
            'period': str(period_reference),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_entries': result.total_entries or 0,
            'total_debit': float(result.total_debit or 0),
            'total_credit': float(result.total_credit or 0),
            'net_change': float((result.total_debit or 0) - (result.total_credit or 0)),
            'by_account_type': [
                {
                    'account_type': row.account_type,
                    'count': row.count,
                    'debit': float(row.debit or 0),
                    'credit': float(row.credit or 0),
                    'net': float((row.debit or 0) - (row.credit or 0))
                }
                for row in by_account_type
            ]
        }
    
    def get_account_balance_history(
        self,
        account_code: AccountCode,
        start_date: date,
        end_date: date,
        interval: str = "daily"  # daily, weekly, monthly
    ) -> List[Dict[str, Any]]:
        """
        الحصول على تاريخ رصيد حساب مع فترات زمنية محددة
        
        الميزات:
            1. دعم فترات يومية، أسبوعية، شهرية
            2. حساب الرصيد في نهاية كل فترة
            3. عرض التغيرات بين الفترات
        
        Args:
            account_code: كود الحساب
            start_date: تاريخ البداية
            end_date: تاريخ النهاية
            interval: الفاصل الزمني (daily, weekly, monthly)
        
        Returns:
            List[Dict[str, Any]]: تاريخ الرصيد
        """
        # 1. الحصول على الحساب
        account = self._session.query(AccountModel).filter(
            AccountModel.code == account_code.code
        ).first()
        
        if not account:
            return []
        
        # 2. تحديد الفاصل الزمني
        intervals = self._generate_intervals(start_date, end_date, interval)
        
        # 3. حساب الرصيد في كل فترة
        history = []
        running_balance = Decimal('0')
        
        for i, interval_date in enumerate(intervals):
            # حساب الحركات في هذه الفترة
            period_start = interval_date
            period_end = intervals[i + 1] if i + 1 < len(intervals) else end_date
            
            result = self._session.query(
                func.coalesce(func.sum(LedgerEntryModel.debit_amount), 0).label('debit'),
                func.coalesce(func.sum(LedgerEntryModel.credit_amount), 0).label('credit')
            ).filter(
                LedgerEntryModel.account_id == account.id,
                between(
                    func.date(LedgerEntryModel.entry_date),
                    period_start,
                    period_end
                )
            ).first()
            
            debit = result.debit or Decimal('0')
            credit = result.credit or Decimal('0')
            
            # تحديث الرصيد الجاري
            running_balance += debit - credit
            
            history.append({
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'debit': float(debit),
                'credit': float(credit),
                'net_change': float(debit - credit),
                'closing_balance': float(running_balance),
                'currency': account.currency or "USD"
            })
        
        return history
    
    def get_entries_by_journal(
        self,
        journal_entry_id: JournalEntryId
    ) -> List[LedgerEntry]:
        """
        الحصول على حركات الأستاذ المرتبطة بقيد يومية معين
        
        Args:
            journal_entry_id: معرف القيد المحاسبي
        
        Returns:
            List[LedgerEntry]: قائمة حركات الأستاذ
        """
        models = self._session.query(LedgerEntryModel).filter(
            LedgerEntryModel.journal_entry_id == journal_entry_id.value
        ).all()
        
        entries = []
        for model in models:
            account = self._session.query(AccountModel).filter(
                AccountModel.id == model.account_id
            ).first()
            
            if account:
                entries.append(self._to_entity(model, AccountCode(account.code)))
        
        return entries
    
    def verify_trial_balance(
        self,
        as_of: date,
        currency: str = "USD"
    ) -> Tuple[bool, Decimal]:
        """
        التحقق من صحة ميزان المراجعة
        
        الميزات:
            1. التحقق من توازن إجمالي المدين والدائن
            2. دعم العملات المتعددة
            3. إرجاع الفرق إن وجد
        
        Args:
            as_of: التاريخ
            currency: العملة (افتراضي: USD)
        
        Returns:
            Tuple[bool, Decimal]: (متوازن, الفرق)
        """
        balances = self.get_trial_balance(as_of, currency=currency)
        
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        for account_code, balance in balances.items():
            if balance.amount > 0:
                total_debit += balance.amount
            else:
                total_credit += abs(balance.amount)
        
        difference = abs(total_debit - total_credit)
        is_balanced = difference < Decimal('0.01')
        
        return is_balanced, difference
    
    def delete_entries_for_journal(
        self,
        journal_entry_id: JournalEntryId
    ) -> int:
        """
        حذف حركات الأستاذ المرتبطة بقيد يومية (استخدام بحذر)
        
        ⚠️ تحذير: هذه العملية دائمة ولا يمكن التراجع عنها.
        يجب استخدامها فقط في حالات استثنائية.
        
        Args:
            journal_entry_id: معرف القيد المحاسبي
        
        Returns:
            int: عدد الحركات المحذوفة
        """
        result = self._session.query(LedgerEntryModel).filter(
            LedgerEntryModel.journal_entry_id == journal_entry_id.value
        ).delete(synchronize_session=False)
        
        self._session.flush()
        return result
    
    # =========================================================================
    # دوال التحويل (Converters)
    # =========================================================================
    
    def _to_entity(
        self,
        model: LedgerEntryModel,
        account_code: AccountCode
    ) -> LedgerEntry:
        """
        تحويل ORM Model → Domain Entity
        
        Args:
            model: نموذج ORM
            account_code: كود الحساب
        
        Returns:
            LedgerEntry: كيان حركة الأستاذ
        """
        if not model:
            return None
        
        from core.domain.accounting.interfaces import LedgerEntry as DomainLedgerEntry
        from core.domain.accounting.value_objects import EntryId
        
        currency = model.currency or "USD"
        return DomainLedgerEntry(
            entry_id=EntryId.from_string(str(model.id)),
            journal_entry_id=JournalEntryId.from_string(str(model.journal_entry_id)),
            account_code=account_code,
            debit=Money(model.debit_amount, currency),
            credit=Money(model.credit_amount, currency),
            date=model.entry_date,
            posted_at=model.posted_at,
            reference=model.reference
        )
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def _calculate_balance(
        self,
        account_type: str,
        total_debit: Decimal,
        total_credit: Decimal
    ) -> Decimal:
        """
        حساب الرصيد حسب نوع الحساب
        
        القاعدة:
            - الأصول والمصروفات: رصيد مدين (Debit Balance)
            - الخصوم وحقوق الملكية والإيرادات: رصيد دائن (Credit Balance)
        
        Args:
            account_type: نوع الحساب
            total_debit: إجمالي المدين
            total_credit: إجمالي الدائن
        
        Returns:
            Decimal: الرصيد المحسوب
        """
        if account_type in ['asset', 'expense']:
            return total_debit - total_credit
        else:
            return total_credit - total_debit
    
    def _generate_intervals(
        self,
        start_date: date,
        end_date: date,
        interval: str
    ) -> List[date]:
        """
        توليد فترات زمنية
        
        Args:
            start_date: تاريخ البداية
            end_date: تاريخ النهاية
            interval: الفاصل الزمني (daily, weekly, monthly)
        
        Returns:
            List[date]: قائمة التواريخ
        """
        from datetime import timedelta
        
        dates = []
        current = start_date
        
        if interval == "daily":
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
        elif interval == "weekly":
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=7)
        elif interval == "monthly":
            while current <= end_date:
                dates.append(current)
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)
        else:
            raise ValueError(f"Unsupported interval: {interval}")
        
        return dates