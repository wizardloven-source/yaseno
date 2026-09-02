# core/domain/accounting/reconciliation_service.py
"""
Reconciliation Service - خدمة التسوية البنكية
الإصدار: 1.0.0

الميزات:
    1. استيراد كشوف الحسابات البنكية (CSV, Excel, PDF)
    2. مطابقة تلقائية للحركات
    3. مطابقة يدوية
    4. إنشاء قيود تسوية
    5. تقارير التسوية
    6. دعم العملات المتعددة
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging
import csv
import io

from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.services import PostingEngine, LedgerEngine
from core.domain.accounting.interfaces import (
    ILedgerRepository,
    IJournalEntryRepository,
    IAuditRepository
)
from core.domain.accounting.exceptions import InvalidAccountError
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.shared.clock import get_clock

from .reconciliation import (
    BankStatement,
    BankStatementLine,
    Reconciliation,
    ReconciliationMatch,
    ReconciliationStatus,
    ReconciliationType,
    MatchingStatus
)

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """نتيجة عملية التسوية"""
    success: bool
    message: str
    reconciliation_id: Optional[str] = None
    matched_count: int = 0
    unmatched_count: int = 0
    journal_entry_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class ReconciliationService:
    """
    خدمة التسوية البنكية المتقدمة
    
    الميزات:
        1. استيراد كشوف الحسابات من تنسيقات متعددة
        2. مطابقة تلقائية (بنظام Fuzzy Matching)
        3. مطابقة يدوية
        4. إنشاء قيود تسوية
        5. تقارير التسوية
    """
    
    def __init__(
        self,
        ledger_repo: ILedgerRepository,
        journal_repo: IJournalEntryRepository,
        posting_engine: PostingEngine,
        ledger_engine: LedgerEngine,
        audit_repo: Optional[IAuditRepository] = None
    ):
        self._ledger_repo = ledger_repo
        self._journal_repo = journal_repo
        self._posting_engine = posting_engine
        self._ledger_engine = ledger_engine
        self._audit_repo = audit_repo
        self._clock = get_clock()
        self._reconciliations: Dict[str, Reconciliation] = {}
        self._bank_statements: Dict[str, BankStatement] = {}
    
    # =========================================================================
    # إدارة كشوف الحسابات البنكية
    # =========================================================================
    
    def import_bank_statement(
        self,
        account_code: AccountCode,
        bank_name: str,
        account_number: str,
        data: str,
        file_format: str = "csv",
        uploaded_by: str = "system"
    ) -> BankStatement:
        """
        استيراد كشف حساب بنكي من ملف
        
        يدعم التنسيقات:
            - CSV (مفصول بفواصل)
            - CSV (مفصول بفواصل منقوطة)
            - Excel (سيتم دعمه لاحقاً)
        """
        logger.info(f"Importing bank statement for {account_code} from {bank_name}")
        
        lines = []
        
        if file_format == "csv":
            lines = self._parse_csv(data)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # حساب الأرصدة
        if not lines:
            raise ValueError("No lines found in bank statement")
        
        # استخراج الرصيد الافتتاحي من أول حركة
        opening_balance = Money.zero()
        closing_balance = Money.zero()
        
        # إنشاء كشف الحساب
        statement = BankStatement(
            account_code=account_code,
            bank_name=bank_name,
            account_number=account_number,
            statement_date=self._clock.today(),
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            lines=lines,
            uploaded_by=uploaded_by
        )
        
        # تخزين الكشف
        self._bank_statements[statement.id] = statement
        
        logger.info(f"✅ Bank statement imported: {statement.id} ({len(lines)} lines)")
        
        return statement
    
    def _parse_csv(self, data: str) -> List[BankStatementLine]:
        """تحليل ملف CSV"""
        lines = []
        
        # محاولة اكتشاف المحدد
        try:
            # تجربة الفاصلة المنقوطة أولاً
            reader = csv.reader(io.StringIO(data), delimiter=';')
            sample = next(reader)
            if len(sample) < 3:
                raise StopIteration
        except (StopIteration, csv.Error):
            # تجربة الفاصلة العادية
            reader = csv.reader(io.StringIO(data), delimiter=',')
        
        # تخطي رأس الملف إذا وجد
        header = None
        for row in reader:
            if not row:
                continue
            
            # محاولة تحديد ما إذا كان هذا هو رأس الملف
            if any(keyword in ' '.join(row).lower() for keyword in ['date', 'description', 'amount', 'reference']):
                header = row
                continue
            
            # معالجة الصف
            try:
                line = self._parse_csv_row(row, header)
                if line:
                    lines.append(line)
            except Exception as e:
                logger.warning(f"Failed to parse row: {row} - {e}")
                continue
        
        return lines
    
    def _parse_csv_row(
        self,
        row: List[str],
        header: Optional[List[str]] = None
    ) -> Optional[BankStatementLine]:
        """تحليل صف CSV إلى سطر كشف حساب"""
        # محاولة تحديد الأعمدة
        if header:
            # استخدام رأس الملف لتحديد الأعمدة
            date_idx = self._find_column(header, ['date', 'transaction_date', 'date_time'])
            desc_idx = self._find_column(header, ['description', 'desc', 'transaction_description', 'details'])
            amount_idx = self._find_column(header, ['amount', 'transaction_amount', 'value'])
            ref_idx = self._find_column(header, ['reference', 'ref', 'check', 'cheque'])
        else:
            # افتراض ترتيب معين
            date_idx = 0
            desc_idx = 1
            amount_idx = 2
            ref_idx = 3 if len(row) > 3 else None
        
        # استخراج البيانات
        try:
            date_str = row[date_idx] if date_idx is not None and date_idx < len(row) else ""
            description = row[desc_idx] if desc_idx is not None and desc_idx < len(row) else ""
            amount_str = row[amount_idx] if amount_idx is not None and amount_idx < len(row) else "0"
            reference = row[ref_idx] if ref_idx is not None and ref_idx < len(row) else None
        except IndexError:
            return None
        
        # تنظيف المبلغ
        amount_str = amount_str.replace(',', '').replace(' ', '').strip()
        try:
            amount = Decimal(amount_str)
        except:
            return None
        
        # إنشاء السطر
        return BankStatementLine(
            transaction_date=self._parse_date(date_str),
            description=description.strip(),
            amount=Money(amount, "USD"),
            reference=reference
        )
    
    def _find_column(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """البحث عن عمود بناءً على الكلمات المفتاحية"""
        for i, col in enumerate(header):
            col_lower = col.lower().strip()
            for keyword in keywords:
                if keyword in col_lower:
                    return i
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """تحويل نص التاريخ إلى datetime"""
        from dateutil import parser
        try:
            return parser.parse(date_str)
        except:
            return self._clock.now()
    
    # =========================================================================
    # إنشاء وإدارة التسويات
    # =========================================================================
    
    def create_reconciliation(
        self,
        bank_statement_id: str,
        account_code: AccountCode,
        created_by: str = "system"
    ) -> Reconciliation:
        """إنشاء عملية تسوية جديدة"""
        logger.info(f"Creating reconciliation for account: {account_code}")
        
        # الحصول على كشف الحساب
        statement = self._bank_statements.get(bank_statement_id)
        if not statement:
            raise ValueError(f"Bank statement '{bank_statement_id}' not found")
        
        # الحصول على رصيد دفتر الأستاذ
        ledger_balance = self._ledger_engine.get_balance(
            account_code,
            statement.statement_date
        )
        
        # إنشاء التسوية
        reconciliation = Reconciliation(
            bank_statement_id=bank_statement_id,
            account_code=account_code,
            reconciliation_date=self._clock.now(),
            opening_balance=ledger_balance,
            closing_balance=ledger_balance,
            bank_opening_balance=statement.opening_balance,
            bank_closing_balance=statement.closing_balance,
            created_by=created_by,
            unmatched_bank_lines=[line.id for line in statement.lines],
            unmatched_ledger_entries=self._get_unmatched_ledger_entries(
                account_code,
                statement.statement_date
            )
        )
        
        # تخزين التسوية
        self._reconciliations[reconciliation.id] = reconciliation
        
        logger.info(f"✅ Reconciliation created: {reconciliation.id}")
        
        return reconciliation
    
    def _get_unmatched_ledger_entries(
        self,
        account_code: AccountCode,
        as_of_date: date
    ) -> List[str]:
        """الحصول على حركات دفتر الأستاذ غير المطابقة"""
        # جلب الحركات في الفترة
        entries = self._ledger_repo.get_entries_by_account(
            account_code,
            from_date=as_of_date - timedelta(days=365),
            to_date=as_of_date
        )
        
        # استبعاد الحركات المطابقة بالفعل
        # TODO: تنفيذ منطق تتبع المطابقات
        return [str(e.entry_id) for e in entries[:100]]  # حد مؤقت
    
    # =========================================================================
    # المطابقة التلقائية
    # =========================================================================
    
    def auto_match(
        self,
        reconciliation_id: str,
        matched_by: str = "system"
    ) -> ReconciliationResult:
        """
        المطابقة التلقائية للحركات البنكية مع دفتر الأستاذ
        
        تعتمد على:
            1. تطابق المبلغ
            2. تطابق التاريخ (ضمن نطاق +/- 3 أيام)
            3. تطابق المرجع (اختياري)
        """
        logger.info(f"Auto-matching reconciliation: {reconciliation_id}")
        
        reconciliation = self._reconciliations.get(reconciliation_id)
        if not reconciliation:
            return ReconciliationResult(
                success=False,
                message=f"Reconciliation '{reconciliation_id}' not found"
            )
        
        statement = self._bank_statements.get(reconciliation.bank_statement_id)
        if not statement:
            return ReconciliationResult(
                success=False,
                message=f"Bank statement not found"
            )
        
        # الحصول على حركات دفتر الأستاذ غير المطابقة
        ledger_entries = self._get_ledger_entries_for_matching(
            reconciliation.account_code,
            reconciliation.reconciliation_date
        )
        
        matched_count = 0
        unmatched_ledger = list(ledger_entries.keys())
        unmatched_bank = [line.id for line in statement.lines]
        
        # محاولة المطابقة
        for bank_line in statement.lines:
            if bank_line.id not in unmatched_bank:
                continue
            
            best_match = self._find_best_match(
                bank_line,
                ledger_entries,
                unmatched_ledger
            )
            
            if best_match:
                # إنشاء مطابقة
                match = reconciliation.add_match(
                    bank_line_id=bank_line.id,
                    ledger_entry_id=best_match,
                    amount=bank_line.amount,
                    matched_by=matched_by
                )
                matched_count += 1
                
                # إزالة من القوائم غير المطابقة
                if bank_line.id in unmatched_bank:
                    unmatched_bank.remove(bank_line.id)
                if best_match in unmatched_ledger:
                    unmatched_ledger.remove(best_match)
        
        reconciliation.unmatched_bank_lines = unmatched_bank
        reconciliation.unmatched_ledger_entries = unmatched_ledger
        
        # تحديث حالة التسوية
        if matched_count > 0:
            if len(unmatched_bank) == 0 and len(unmatched_ledger) == 0:
                reconciliation.status = ReconciliationStatus.RECONCILED
            else:
                reconciliation.status = ReconciliationStatus.PARTIAL
        
        logger.info(f"✅ Auto-match completed: {matched_count} matches found")
        
        return ReconciliationResult(
            success=True,
            message=f"Auto-match completed: {matched_count} matches found",
            reconciliation_id=reconciliation_id,
            matched_count=matched_count,
            unmatched_count=len(unmatched_bank) + len(unmatched_ledger)
        )
    
    def _find_best_match(
        self,
        bank_line: BankStatementLine,
        ledger_entries: Dict[str, Any],
        unmatched_ledger: List[str]
    ) -> Optional[str]:
        """البحث عن أفضل مطابقة لحركة بنكية"""
        best_match = None
        best_score = 0
        
        for ledger_id in unmatched_ledger:
            if ledger_id not in ledger_entries:
                continue
            
            ledger_entry = ledger_entries[ledger_id]
            score = self._calculate_match_score(bank_line, ledger_entry)
            
            if score > best_score:
                best_score = score
                best_match = ledger_id
        
        # قبول المطابقة إذا كانت النسبة > 80%
        if best_score >= 80:
            return best_match
        
        return None
    
    def _calculate_match_score(
        self,
        bank_line: BankStatementLine,
        ledger_entry: Any
    ) -> int:
        """
        حساب نسبة التطابق بين حركة بنكية وحركة محاسبية
        """
        score = 0
        
        # 1. تطابق المبلغ (50 نقطة)
        if abs(bank_line.amount.amount) == abs(ledger_entry.amount.amount):
            score += 50
        elif abs(abs(bank_line.amount.amount) - abs(ledger_entry.amount.amount)) < 1:
            score += 40
        
        # 2. تطابق التاريخ (30 نقطة)
        date_diff = abs(
            (bank_line.transaction_date - ledger_entry.date).days
        )
        if date_diff == 0:
            score += 30
        elif date_diff <= 3:
            score += 20
        elif date_diff <= 7:
            score += 10
        
        # 3. تطابق المرجع (20 نقطة)
        if bank_line.reference and ledger_entry.reference:
            if bank_line.reference == ledger_entry.reference:
                score += 20
            elif bank_line.reference in ledger_entry.reference:
                score += 10
        
        return score
    
    def _get_ledger_entries_for_matching(
        self,
        account_code: AccountCode,
        as_of_date: datetime
    ) -> Dict[str, Any]:
        """الحصول على حركات دفتر الأستاذ للمطابقة"""
        entries = self._ledger_repo.get_entries_by_account(
            account_code,
            from_date=as_of_date - timedelta(days=90),
            to_date=as_of_date
        )
        
        return {
            str(entry.entry_id): entry
            for entry in entries
        }
    
    # =========================================================================
    # المطابقة اليدوية
    # =========================================================================
    
    def manual_match(
        self,
        reconciliation_id: str,
        bank_line_id: str,
        ledger_entry_id: str,
        amount: Decimal,
        matched_by: str = "system",
        notes: Optional[str] = None
    ) -> ReconciliationResult:
        """
        مطابقة يدوية لحركة بنكية مع حركة محاسبية
        """
        logger.info(f"Manual matching in reconciliation: {reconciliation_id}")
        
        reconciliation = self._reconciliations.get(reconciliation_id)
        if not reconciliation:
            return ReconciliationResult(
                success=False,
                message=f"Reconciliation '{reconciliation_id}' not found"
            )
        
        try:
            match = reconciliation.add_match(
                bank_line_id=bank_line_id,
                ledger_entry_id=ledger_entry_id,
                amount=Money(amount, "USD"),
                matched_by=matched_by,
                notes=notes
            )
            
            logger.info(f"✅ Manual match added: {match.id}")
            
            return ReconciliationResult(
                success=True,
                message="Match added successfully",
                reconciliation_id=reconciliation_id,
                matched_count=len(reconciliation.matches)
            )
            
        except Exception as e:
            logger.error(f"❌ Manual match failed: {e}")
            return ReconciliationResult(
                success=False,
                message=f"Manual match failed: {str(e)}",
                errors=[str(e)]
            )
    
    # =========================================================================
    # إنشاء قيد التسوية
    # =========================================================================
    
    def create_reconciliation_entry(
        self,
        reconciliation_id: str,
        posted_by: str = "system"
    ) -> ReconciliationResult:
        """
        إنشاء قيد محاسبي لفروقات التسوية
        
        يتم إنشاء قيد تلقائي للفروقات بين رصيد البنك ودفتر الأستاذ
        """
        logger.info(f"Creating reconciliation entry for: {reconciliation_id}")
        
        reconciliation = self._reconciliations.get(reconciliation_id)
        if not reconciliation:
            return ReconciliationResult(
                success=False,
                message=f"Reconciliation '{reconciliation_id}' not found"
            )
        
        if reconciliation.status != ReconciliationStatus.PARTIAL:
            return ReconciliationResult(
                success=False,
                message=f"Cannot create entry for status: {reconciliation.status.value}"
            )
        
        # حساب الفروقات
        difference = reconciliation.difference
        
        if difference == 0:
            return ReconciliationResult(
                success=False,
                message="No difference found, no entry needed"
            )
        
        # إنشاء القيد
        lines = []
        
        if reconciliation.closing_balance.amount > reconciliation.bank_closing_balance.amount:
            # رصيد دفتر الأستاذ > رصيد البنك = يجب تعديل دفتر الأستاذ (زيادة الخصوم أو نقص الأصول)
            lines.append(JournalLine(
                account_code=reconciliation.account_code,
                debit=Money.zero("USD"),
                credit=Money(difference, "USD")
            ))
            lines.append(JournalLine(
                account_code=AccountCode("5900"),  # حساب فروقات التسوية
                debit=Money(difference, "USD"),
                credit=Money.zero("USD")
            ))
        else:
            # رصيد البنك > رصيد دفتر الأستاذ
            lines.append(JournalLine(
                account_code=reconciliation.account_code,
                debit=Money(difference, "USD"),
                credit=Money.zero("USD")
            ))
            lines.append(JournalLine(
                account_code=AccountCode("5900"),
                debit=Money.zero("USD"),
                credit=Money(difference, "USD")
            ))
        
        # إنشاء القيد
        entry = JournalEntry(
            date=self._clock.now(),
            description=f"تسوية بنكية - حساب {reconciliation.account_code} - {reconciliation.reconciliation_date}",
            lines=lines
        )
        
        # ترحيل القيد
        post_result = self._posting_engine.post(entry, posted_by, skip_save=False)
        
        if post_result.success:
            reconciliation.journal_entry_id = str(entry.id)
            logger.info(f"✅ Reconciliation entry created: {entry.id}")
            
            return ReconciliationResult(
                success=True,
                message="Reconciliation entry created successfully",
                reconciliation_id=reconciliation_id,
                journal_entry_id=str(entry.id)
            )
        else:
            return ReconciliationResult(
                success=False,
                message=f"Failed to post entry: {post_result.message}",
                errors=post_result.errors
            )
    
    # =========================================================================
    # تقارير التسوية
    # =========================================================================
    
    def get_reconciliation_report(
        self,
        reconciliation_id: str
    ) -> Dict[str, Any]:
        """الحصول على تقرير التسوية"""
        reconciliation = self._reconciliations.get(reconciliation_id)
        if not reconciliation:
            return {"error": f"Reconciliation '{reconciliation_id}' not found"}
        
        statement = self._bank_statements.get(reconciliation.bank_statement_id)
        
        return {
            "reconciliation": {
                "id": reconciliation.id,
                "account_code": str(reconciliation.account_code),
                "status": reconciliation.status.value,
                "created_by": reconciliation.created_by,
                "created_at": reconciliation.created_at.isoformat(),
                "completed_by": reconciliation.completed_by,
                "completed_at": reconciliation.completed_at.isoformat() if reconciliation.completed_at else None
            },
            "balances": {
                "opening_balance": float(reconciliation.opening_balance.amount),
                "closing_balance": float(reconciliation.closing_balance.amount),
                "bank_opening_balance": float(reconciliation.bank_opening_balance.amount),
                "bank_closing_balance": float(reconciliation.bank_closing_balance.amount),
                "difference": float(reconciliation.difference),
                "match_percentage": reconciliation.match_percentage
            },
            "matches": [
                {
                    "id": m.id,
                    "bank_line_id": m.bank_line_id,
                    "ledger_entry_id": m.ledger_entry_id,
                    "amount": float(m.amount.amount),
                    "status": m.status.value,
                    "matched_at": m.matched_at.isoformat()
                }
                for m in reconciliation.matches
            ],
            "unmatched_bank_lines": reconciliation.unmatched_bank_lines,
            "unmatched_ledger_entries": reconciliation.unmatched_ledger_entries,
            "journal_entry_id": reconciliation.journal_entry_id,
            "notes": reconciliation.notes
        }