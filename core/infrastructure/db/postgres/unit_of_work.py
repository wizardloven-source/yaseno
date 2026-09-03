# core/infrastructure/db/postgres/unit_of_work.py
"""
POSTGRESQL UNIT OF WORK IMPLEMENTATION - PROFESSIONAL EDITION
وحدة العمل المتكاملة - الإصدار الاحترافي
✅ مصحح: إضافة extend_existing=True في create_tables_safe()
✅ مصحح: تجاهل أخطاء الفهارس الموجودة مسبقاً
✅ مصحح: إنشاء الجداول بترتيب آمن
✅ مصحح: إضافة مستودع مراكز التكلفة (centers)
"""

from typing import Optional, Callable, List, Any, Dict, Set
from datetime import datetime, timezone
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from core.domain.accounting.interfaces import (
    IUnitOfWork, IJournalEntryRepository, ILedgerRepository,
    IAccountRepository, IFiscalPeriodRepository, IAuditRepository,
    IInvoiceRepository, IPurchaseOrderRepository
)
from core.domain.customers.interfaces import ICustomerRepository
from core.domain.suppliers.interfaces import ISupplierRepository
from core.domain.settings.interfaces import ISettingsRepository
from core.domain.sites.interfaces import ISiteRepository
from core.domain.shared.value_objects import BaseDomainEvent

import uuid as _uuid
from decimal import Decimal as _Decimal


def _json_safe(obj: Any) -> Any:
    """Convert a domain object graph to JSON-serializable primitives."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, _Decimal):
        return str(obj)
    if isinstance(obj, (_uuid.UUID, datetime)):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(v) for v in obj]
    # Fallback: use __str__ for any other object (e.g. value objects / Money)
    try:
        return str(obj)
    except Exception:
        return None


from .repositories import (
    PostgresJournalEntryRepository, PostgresLedgerRepository,
    PostgresAccountRepository, PostgresFiscalPeriodRepository as PostgresAccountingPeriodRepo,
    PostgresAuditRepository
)
from .repositories_invoice import PostgresInvoiceRepository
from .repositories_product import PostgresProductRepository
from .repositories_purchase_order import PostgresPurchaseOrderRepository
from .customers_repository import PostgresCustomerRepository
from .supplier_repository import PostgresSupplierRepository
from .settings_repository import PostgresSettingsRepository
from .currency_repository import PostgresCurrencyRepository
from .funds_repository import PostgresFundRepository, PostgresFundMovementRepository
from .site_repository import PostgresSiteRepository
from .repositories_payment import PostgresPaymentRepository
from .financial_statement_repository import PostgresFinancialStatementRepository
from .customer_branch_repository import PostgresCustomerBranchRepository

# مستودعات المخزون
from .repositories_inventory import (
    PostgresStockMovementRepository,
    PostgresStockBatchRepository,
    PostgresStockTransferRepository
)

# مستودعات سير العمل
from .workflow_repository import (
    PostgresWorkflowRepository,
    PostgresApprovalRequestRepository
)

# مستودعات الأمان (Authentication & Authorization)
from .auth_repository import (
    PostgresUserRepository,
    PostgresRoleRepository,
    PostgresPermissionRepository
)

# مستودعات السنة المالية
from .fiscal_repository import (
    PostgresFiscalYearRepository,
    PostgresFiscalPeriodRepository as PostgresFiscalPeriodRepo
)

# ✅ مستودعات الضرائب (Tax)
from .tax_repository import (
    PostgresTaxRepository,
    PostgresTaxGroupRepository,
    PostgresTaxExemptionRepository,
    PostgresTaxPeriodRepository
)

# ✅ مستودعات مراكز التكلفة (Centers)
from .center_repository import (
    PostgresCenterRepository,
    PostgresAllocationRepository,
    PostgresAllocationRuleRepository
)

# مستودعات الأصول الثابتة
from .fixed_asset_repository import PostgresFixedAssetRepository

# استيراد جميع النماذج لضمان تسجيلها في Base.metadata
from ..models.account_model import Base
from ..models.account_model import FiscalYearModel, FiscalPeriodModel
from ..models.auth_models import UserModel, RoleModel, PermissionModel
from ..models.invoice_model import InvoiceModel, InvoiceLineModel
from ..models.product_model import ProductModel
from ..models.customer_model import CustomerModel
from ..models.supplier_model import SupplierModel
from ..models.purchase_order_model import PurchaseOrderModel, PurchaseOrderLineModel
from ..models.fund_model import FundModel, FundMovementModel, FundTransferModel
from ..models.fund_advanced_models import FundAdvancedModel, ProjectModel
from ..models.site_model import SiteModel
from ..models.payment_model import PaymentModel, PaymentLineModel
from ..models.settings_model import SettingsModel
from ..models.currency_model import CurrencyModel
from ..models.center_model import CenterModel, CenterAllocationModel, CenterAllocationRuleModel
from ..models.workflow_model import WorkflowModel, ApprovalRequestModel
from ..models.rule_model import PostingRuleModel, RuleGroupModel, RuleExecutionLogModel
from ..models.tax_model import TaxRuleModel, TaxGroupModel, TaxExemptionModel, TaxPeriodModel
from ..models.financial_statement_model import FinancialStatementModel, FinancialStatementLineModel
from ..models.notification_model import NotificationModel, NotificationPreferenceModel, NotificationTemplateModel, FundsNotificationModel

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime"""
    return datetime.now(timezone.utc)


class SessionFactory:
    """Factory responsible for managing SQLAlchemy engine lifecycles"""
    
    def __init__(
        self,
        connection_string: str,
        echo: bool = False,
        pool_size: int = 15,
        max_overflow: int = 25,
        pool_timeout: int = 30
    ):
        self._engine = create_engine(
            connection_string,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,
            pool_recycle=1800
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )
    
    def create_session(self) -> Session:
        """إنشاء جلسة قاعدة بيانات جديدة"""
        return self._session_factory()
    
    # =========================================================================
    # ✅ الطريقة المحسنة: إنشاء الجداول مع التحقق الكامل
    # =========================================================================
    
    def create_tables_safe(self) -> dict:
        """
        إنشاء الجداول فقط إذا لم تكن موجودة، مع تفاصيل عن كل جدول وفهرس.
        
        ✅ مصحح: إضافة extend_existing=True للتعامل مع الجداول المعرفة مسبقاً
        ✅ مصحح: تجاهل أخطاء الفهارس الموجودة
        
        Returns:
            dict: إحصائيات عن الجداول والفهارس التي تم إنشاؤها أو تخطيها
        """
        if not self._engine:
            return {"success": False, "error": "No engine available"}
        
        inspector = inspect(self._engine)
        existing_tables: Set[str] = set(inspector.get_table_names())
        
        created_tables: List[str] = []
        skipped_tables: List[str] = []
        created_indexes: List[str] = []
        skipped_indexes: List[str] = []
        errors: List[str] = []
        
        try:
            # تعطيل التحقق من المفاتيح الخارجية مؤقتاً
            with self._engine.connect() as conn:
                conn.execute(text("SET session_replication_role = 'replica';"))
                conn.commit()
                
                # 1. إنشاء الجداول (مع تجاهل الأخطاء)
                for table in Base.metadata.tables.values():
                    table_name = table.name
                    
                    if table_name not in existing_tables:
                        try:
                            # ✅ استخدام checkfirst=True مع ignore
                            table.create(self._engine, checkfirst=True)
                            created_tables.append(table_name)
                            logger.info(f"✅ Table created: {table_name}")
                        except Exception as e:
                            error_msg = f"Failed to create table {table_name}: {e}"
                            # ✅ تجاهل أخطاء الجدول الموجود مسبقاً
                            if "already exists" in str(e).lower():
                                skipped_tables.append(table_name)
                                logger.debug(f"⏭️ Table already exists: {table_name}")
                            else:
                                errors.append(error_msg)
                                logger.error(f"❌ {error_msg}")
                    else:
                        skipped_tables.append(table_name)
                        logger.debug(f"⏭️ Table already exists: {table_name}")
                
                # ✅ ترقية المخطط للأعمدة الجديدة (مثل العملة) قبل إنشاء الفهارس
                try:
                    upgrades = self.ensure_schema_upgrades()
                    if upgrades:
                        logger.info(f"✅ Schema upgrades applied: {upgrades}")
                except Exception as e:
                    logger.error(f"❌ Schema upgrades failed: {e}")
                
                # 2. إنشاء الفهارس (مع تجاهل الأخطاء)
                for table in Base.metadata.tables.values():
                    table_name = table.name
                    
                    # الحصول على الفهارس الموجودة للجدول
                    try:
                        existing_indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
                    except Exception:
                        existing_indexes = set()
                    
                    for index in table.indexes:
                        index_name = index.name
                        if index_name and index_name not in existing_indexes:
                            try:
                                # ✅ استخدام checkfirst=True
                                index.create(self._engine, checkfirst=True)
                                created_indexes.append(index_name)
                                logger.info(f"✅ Index created: {index_name} on {table_name}")
                            except Exception as e:
                                # ✅ تجاهل أخطاء الفهرس الموجود مسبقاً
                                if "already exists" in str(e).lower():
                                    skipped_indexes.append(index_name)
                                    logger.debug(f"⏭️ Index already exists: {index_name}")
                                else:
                                    error_msg = f"Failed to create index {index_name}: {e}"
                                    errors.append(error_msg)
                                    logger.error(f"❌ {error_msg}")
                        elif index_name:
                            skipped_indexes.append(index_name)
                            logger.debug(f"⏭️ Index already exists: {index_name}")
                
                # إعادة تفعيل التحقق من المفاتيح الخارجية
                conn.execute(text("SET session_replication_role = 'origin';"))
                conn.commit()
            
            # 3. إرجاع التقرير
            return {
                "success": len(errors) == 0,
                "tables_created": created_tables,
                "tables_skipped": skipped_tables,
                "indexes_created": created_indexes,
                "indexes_skipped": skipped_indexes,
                "errors": errors,
                "total_tables": len(Base.metadata.tables),
                "existing_tables": len(existing_tables)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return {
                "success": False,
                "error": str(e),
                "tables_created": created_tables,
                "tables_skipped": skipped_tables,
                "indexes_created": created_indexes,
                "indexes_skipped": skipped_indexes,
                "errors": errors + [str(e)]
            }
    
    def create_tables(self, checkfirst: bool = True) -> None:
        """
        إنشاء جميع الجداول في قاعدة البيانات.
        
        Args:
            checkfirst: إذا كان True، لا يتم إنشاء الجداول الموجودة مسبقاً
        """
        if not self._engine:
            return
        
        logger.info("🗄️ Creating database tables...")
        
        try:
            # تعطيل التحقق من المفاتيح الخارجية مؤقتاً
            with self._engine.connect() as conn:
                conn.execute(text("SET session_replication_role = 'replica';"))
                conn.commit()
                
                # ✅ إنشاء جميع الجداول مع checkfirst=True
                Base.metadata.create_all(self._engine, checkfirst=checkfirst)
                
                # إعادة تفعيل التحقق من المفاتيح الخارجية
                conn.execute(text("SET session_replication_role = 'origin';"))
                conn.commit()
            
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            raise
    
    def drop_tables(self) -> None:
        """حذف جميع الجداول من قاعدة البيانات (استخدم بحذر)"""
        if not self._engine:
            return
        
        try:
            # تعطيل التحقق من المفاتيح الخارجية للحذف
            with self._engine.connect() as conn:
                conn.execute(text("SET session_replication_role = 'replica';"))
                conn.commit()
                
                Base.metadata.drop_all(self._engine)
                
                conn.execute(text("SET session_replication_role = 'origin';"))
                conn.commit()
            
            logger.warning("⚠️ Database tables dropped")
        except Exception as e:
            logger.error(f"❌ Failed to drop database tables: {e}")
            raise
    
    # =========================================================================
    # دوال مساعدة للتحقق من الفهارس
    # =========================================================================
    
    def index_exists(self, index_name: str, table_name: Optional[str] = None) -> bool:
        """
        التحقق من وجود فهرس في قاعدة البيانات.
        
        Args:
            index_name: اسم الفهرس
            table_name: اسم الجدول (اختياري)
        
        Returns:
            bool: True إذا كان الفهرس موجوداً
        """
        inspector = inspect(self._engine)
        
        if table_name:
            indexes = inspector.get_indexes(table_name)
            return any(idx['name'] == index_name for idx in indexes)
        else:
            for table in inspector.get_table_names():
                indexes = inspector.get_indexes(table)
                if any(idx['name'] == index_name for idx in indexes):
                    return True
            return False
    
    def create_index_if_not_exists(self, index_name: str, table_name: str, 
                                   columns: List[str], unique: bool = False) -> bool:
        """
        إنشاء فهرس فقط إذا لم يكن موجوداً.
        
        Args:
            index_name: اسم الفهرس
            table_name: اسم الجدول
            columns: قائمة الأعمدة
            unique: هل الفهرس فريد؟
        
        Returns:
            bool: True إذا تم إنشاء الفهرس، False إذا كان موجوداً
        """
        if self.index_exists(index_name, table_name):
            logger.info(f"⏭️ Index {index_name} already exists, skipping")
            return False
        
        unique_str = "UNIQUE " if unique else ""
        columns_str = ", ".join(columns)
        sql = f"CREATE {unique_str}INDEX {index_name} ON {table_name} ({columns_str})"
        
        try:
            with self._engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.info(f"✅ Index created: {index_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create index {index_name}: {e}")
            return False

    def ensure_schema_upgrades(self) -> List[str]:
        """
        ترقية مخطط قاعدة البيانات بطرق Idempotent آمنة للقواعد الموجودة.
        
        تضيف الأعمدة الجديدة (مثل العملة في القيود والأستاذ) بدون إتلاف
        البيانات الحالية. تُستدعى تلقائياً بعد إنشاء الجداول.
        
        Returns:
            List[str]: قائمة بالترقيات المطبقة
        """
        applied = []
        upgrades = [
            (
                "journal_lines",
                "currency",
                "VARCHAR(3) NOT NULL DEFAULT 'USD'"
            ),
            (
                "ledger_entries",
                "currency",
                "VARCHAR(3) NOT NULL DEFAULT 'USD'"
            ),
        ]
        # ترقية نوع أعمدة المبالغ إلى NUMERIC(18,3) لدعم 3 منازل عشرية
        # (لا يُطبَّق إلا على الجداول الموجودة مسبقاً بدقة 2 منزلة)
        amount_columns = [
            ("journal_lines", ["debit_amount", "credit_amount"]),
            ("ledger_entries", ["debit_amount", "credit_amount"]),
        ]
        try:
            with self._engine.connect() as conn:
                for table, column, definition in upgrades:
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "
                                f"{column} {definition}"
                            )
                        )
                        conn.commit()
                        applied.append(f"{table}.{column}")
                        logger.info(f"✅ Schema upgrade: {table}.{column}")
                    except Exception as e:
                        logger.warning(f"⏭️ Schema upgrade skipped {table}.{column}: {e}")
                
                # ترقية دقة المبالغ إلى NUMERIC(18,3) (Idempotent عبر التحقق من المقياس)
                for table, columns in amount_columns:
                    for col in columns:
                        try:
                            scale = conn.execute(
                                text(
                                    "SELECT numeric_scale FROM information_schema.columns "
                                    "WHERE table_name=:t AND column_name=:c"
                                ),
                                {'t': table, 'c': col}
                            ).scalar()
                            if scale is not None and int(scale) < 3:
                                conn.execute(
                                    text(
                                        f"ALTER TABLE {table} ALTER COLUMN {col} "
                                        "TYPE NUMERIC(18,3)"
                                    )
                                )
                                conn.commit()
                                applied.append(f"{table}.{col}->NUMERIC(18,3)")
                                logger.info(f"✅ Schema upgrade: {table}.{col} -> NUMERIC(18,3)")
                        except Exception as e:
                            logger.warning(f"⏭️ Amount precision upgrade skipped {table}.{col}: {e}")
        except Exception as e:
            logger.error(f"❌ Schema upgrade failed: {e}")
        return applied
    
    @property
    def engine(self):
        return self._engine


class PostgresUnitOfWork(IUnitOfWork):
    """
    PostgreSQL implementation of the Unit of Work pattern.
    
    يدير:
        1. جلسة قاعدة البيانات (Session)
        2. المعاملات (Transactions)
        3. المستودعات (Repositories)
        4. أحداث المجال (Domain Events)
    """
    
    def __init__(
        self,
        session_factory: SessionFactory,
        event_dispatcher: Optional[Callable[[List[BaseDomainEvent]], None]] = None
    ):
        self._session_factory = session_factory
        # ✅ جلسة واحدة موحّدة لكل نسخة UoW (تُنشأ فوراً) — هي نفسها جلسة النطاق
        # التي تستخدمها المستودعات المسجلة في الحاوية (خدمة "session").
        self._session: Optional[Session] = session_factory.create_session()
        self._event_dispatcher = event_dispatcher
        self._collected_events: List[BaseDomainEvent] = []
        self._state_before: Dict[str, Dict] = {}
        self._nest_depth: int = 0
        self._tx_started_by_us: bool = False
        
        # Repositories (Lazy Initialization)
        self._journal_entry_repo: Optional[PostgresJournalEntryRepository] = None
        self._ledger_repo: Optional[PostgresLedgerRepository] = None
        self._account_repo: Optional[PostgresAccountRepository] = None
        self._period_repo: Optional[PostgresAccountingPeriodRepo] = None
        self._audit_repo: Optional[PostgresAuditRepository] = None
        self._product_repo: Optional[PostgresProductRepository] = None
        self._invoice_repo: Optional[PostgresInvoiceRepository] = None
        self._purchase_order_repo: Optional[PostgresPurchaseOrderRepository] = None
        self._customer_repo: Optional[PostgresCustomerRepository] = None
        self._supplier_repo: Optional[PostgresSupplierRepository] = None
        self._settings_repo: Optional[PostgresSettingsRepository] = None
        self._currency_repo: Optional[PostgresCurrencyRepository] = None
        self._fund_repo: Optional[PostgresFundRepository] = None
        self._fund_movement_repo: Optional[PostgresFundMovementRepository] = None
        self._site_repo: Optional[PostgresSiteRepository] = None
        self._payment_repo: Optional[PostgresPaymentRepository] = None

        # مستودع القوائم المالية
        self._financial_statement_repo: Optional[PostgresFinancialStatementRepository] = None
        
        # مستودعات المخزون
        self._stock_movement_repo: Optional[PostgresStockMovementRepository] = None
        self._stock_batch_repo: Optional[PostgresStockBatchRepository] = None
        self._stock_transfer_repo: Optional[PostgresStockTransferRepository] = None
        
        # مستودعات سير العمل
        self._workflow_repo: Optional[PostgresWorkflowRepository] = None
        self._approval_request_repo: Optional[PostgresApprovalRequestRepository] = None
        
        # مستودعات الأمان
        self._user_repo: Optional[PostgresUserRepository] = None
        self._role_repo: Optional[PostgresRoleRepository] = None
        self._permission_repo: Optional[PostgresPermissionRepository] = None
        
        # مستودعات السنة المالية
        self._fiscal_year_repo: Optional[PostgresFiscalYearRepository] = None
        self._fiscal_period_repo: Optional[PostgresFiscalPeriodRepo] = None
        
        # ✅ مستودعات الضرائب
        self._tax_repo: Optional[PostgresTaxRepository] = None
        self._tax_group_repo: Optional[PostgresTaxGroupRepository] = None
        self._tax_exemption_repo: Optional[PostgresTaxExemptionRepository] = None
        self._tax_period_repo: Optional[PostgresTaxPeriodRepository] = None
        
        # ✅ مستودعات مراكز التكلفة (Centers)
        self._center_repo: Optional[PostgresCenterRepository] = None
        self._center_allocation_repo: Optional[PostgresAllocationRepository] = None
        self._center_allocation_rule_repo: Optional[PostgresAllocationRuleRepository] = None

        # مستودع فروع العملاء
        self._customer_branch_repo: Optional[PostgresCustomerBranchRepository] = None

        # مستودع الأصول الثابتة
        self._fixed_asset_repo: Optional[PostgresFixedAssetRepository] = None
    
    # =========================================================================
    # إدارة دورة الحياة
    # =========================================================================
    
    def __enter__(self) -> 'PostgresUnitOfWork':
        """بدء المعاملة (يدعم التداخل الآمن)"""
        if self._session is None or not self._session.is_active:
            # جلسة جديدة أو جلسة منتهية من معاملة سابقة → إعادة استخدامها
            if self._session is None:
                self._session = self._session_factory.create_session()
            self._nest_depth = 1
            self._reset_cached_repos()
            self._tx_started_by_us = True
            logger.debug("✅ UoW session started")
        else:
            self._nest_depth += 1
            self._tx_started_by_us = False
            logger.debug(f"UoW nested enter (depth={self._nest_depth})")
        return self

    def _reset_cached_repos(self) -> None:
        """إعادة تعيين المستودعات المخزنة مؤقتاً لترتبط بالجلسة الجديدة"""
        repo_attrs = [
            '_journal_entry_repo', '_ledger_repo', '_account_repo', '_period_repo',
            '_audit_repo', '_product_repo', '_invoice_repo', '_purchase_order_repo',
            '_customer_repo', '_supplier_repo', '_settings_repo', '_currency_repo',
            '_fund_repo', '_fund_movement_repo', '_site_repo', '_payment_repo',
            '_stock_movement_repo', '_stock_batch_repo', '_stock_transfer_repo',
            '_workflow_repo', '_approval_request_repo', '_user_repo', '_role_repo',
            '_permission_repo', '_fiscal_year_repo', '_fiscal_period_repo',
            '_tax_repo', '_tax_group_repo', '_tax_exemption_repo', '_tax_period_repo',
            '_center_repo', '_center_allocation_repo', '_center_allocation_rule_repo',
            '_reconciliation_repo', '_customer_branch_repo', '_report_repo',
            '_notification_repo', '_notification_pref_repo', '_fixed_asset_repo',
            '_financial_statement_repo', '_transfer_repo', '_branch_repo',
        ]
        for attr in repo_attrs:
            if hasattr(self, attr):
                setattr(self, attr, None)
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """إنهاء المعاملة (لا يُغلق الجلسة هنا — تُغلق عند انتهاء النطاق عبر dispose()).

        ✅ مُصلح: لا يتم الـ commit إلا في أعمق مستوى واحد (nest_depth == 0).
        كانت الجلسة تُـcommit عند كل مستوى تداخل، مما يسمح بترحيل قيود
        محاسبية لعمليات فشلت لاحقاً (فاتورة، دفعة، مخزون).

        ✅ مُصلح: الجلسة مشتركة مع مستودعات النطاق، لذا لا تُغلق عند الخروج
        حتى لا تُفسد المستودعات الحاملة لمرجعها؛ تُغلق تلقائياً عند انتهاء النطاق.
        """
        self._nest_depth = max(0, self._nest_depth - 1)
        try:
            if exc_type is not None:
                self.rollback()
            elif self._session and self._session.is_active and self._nest_depth == 0:
                self.commit()
        except Exception as e:
            logger.error(f"Error in UoW cleanup: {e}")

    def dispose(self) -> None:
        """إغلاق الجلسة نهائياً (يستدعيها الحاوية عند انتهاء النطاق)."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing UoW session: {e}")
            finally:
                self._session = None
                logger.debug("✅ UoW session closed (dispose)")
    
    # =========================================================================
    # إدارة المعاملات
    # =========================================================================
    
    def commit(self) -> None:
        """تنفيذ المعاملة"""
        if not self._session:
            raise RuntimeError("No active database session.")
        
        try:
            # تسجيل أحداث التدقيق
            for event in self._collected_events:
                self._log_audit_for_event(event)
            
            # تنفيذ Commit
            self._session.commit()
            logger.debug(f"✅ UoW committed ({len(self._collected_events)} events)")
            
            # صرف الأحداث
            if self._event_dispatcher and self._collected_events:
                events_to_dispatch = self._collected_events.copy()
                self._collected_events.clear()
                self._state_before.clear()
                dispatcher = self._event_dispatcher
                if hasattr(dispatcher, 'dispatch_many'):
                    dispatcher.dispatch_many(events_to_dispatch)
                else:
                    dispatcher(events_to_dispatch)
                
        except SQLAlchemyError as e:
            self.rollback()
            logger.error(f"❌ UoW commit failed: {e}")
            raise
        except Exception as e:
            self.rollback()
            logger.error(f"❌ UoW commit failed: {e}")
            raise
    
    def rollback(self) -> None:
        """التراجع عن المعاملة"""
        if self._session and self._session.is_active:
            self._session.rollback()
            logger.debug("↩️ UoW rolled back")
        self._collected_events.clear()
        self._state_before.clear()
    
    # =========================================================================
    # أحداث المجال
    # =========================================================================
    
    def collect_event(self, event: BaseDomainEvent) -> None:
        """تجميع حدث Domain واحد"""
        self._collected_events.append(event)
    
    def collect_events(self, events: List[BaseDomainEvent]) -> None:
        """تجميع قائمة أحداث Domain"""
        self._collected_events.extend(events)
    
    def get_collected_events(self) -> List[BaseDomainEvent]:
        """الحصول على الأحداث المجمعة"""
        return self._collected_events.copy()
    
    def _log_audit_for_event(self, event: BaseDomainEvent) -> None:
        """تسجيل حدث في سجل التدقيق"""
        if not self.audit:
            return
        
        try:
            event_name = event.get_event_name()
            entity_type = event.__class__.__name__
            entity_id = str(getattr(event, 'entry_id', getattr(event, 'period_name', 'GLOBAL_SYSTEM')))
            performed_by = str(getattr(event, 'posted_by', getattr(event, 'closed_by', 'system_worker')))
            
            event_dict = event.to_dict() if hasattr(event, 'to_dict') else {}
            
            self.audit.log_operation(
                operation=event_name,
                entity_type=entity_type,
                entity_id=entity_id,
                performed_by=performed_by,
                changes=_json_safe(event_dict)
            )
        except Exception as e:
            logger.error(f"Failed to log audit for event: {e}")
    
    # =========================================================================
    # المستودعات (Repositories)
    # =========================================================================
    
    @property
    def session(self) -> Session:
        """الحصول على الجلسة الحالية"""
        if not self._session:
            raise RuntimeError("No active session. Use 'with uow:' context manager.")
        return self._session
    
    @property
    def journal_entries(self) -> IJournalEntryRepository:
        if not self._journal_entry_repo:
            self._journal_entry_repo = PostgresJournalEntryRepository(self.session)
        return self._journal_entry_repo
    
    @property
    def ledger(self) -> ILedgerRepository:
        if not self._ledger_repo:
            self._ledger_repo = PostgresLedgerRepository(self.session)
        return self._ledger_repo
    
    @property
    def accounts(self) -> IAccountRepository:
        if not self._account_repo:
            self._account_repo = PostgresAccountRepository(self.session)
        return self._account_repo
    
    @property
    def periods(self) -> IFiscalPeriodRepository:
        if not self._period_repo:
            self._period_repo = PostgresAccountingPeriodRepo(self.session)
        return self._period_repo
    
    @property
    def audit(self) -> IAuditRepository:
        if not self._audit_repo:
            self._audit_repo = PostgresAuditRepository(self.session)
        return self._audit_repo
    
    # =========================================================================
    # مستودعات السنة المالية (المضافة)
    # =========================================================================
    
    @property
    def fiscal_years(self) -> PostgresFiscalYearRepository:
        """مستودع السنوات المالية"""
        if not self._fiscal_year_repo:
            self._fiscal_year_repo = PostgresFiscalYearRepository(self.session)
        return self._fiscal_year_repo
    
    @property
    def fiscal_periods(self) -> PostgresFiscalPeriodRepo:
        """مستودع الفترات المالية"""
        if not self._fiscal_period_repo:
            self._fiscal_period_repo = PostgresFiscalPeriodRepo(self.session)
        return self._fiscal_period_repo
    
    # =========================================================================
    # مستودعات المنتجات والفواتير والمشتريات
    # =========================================================================
    
    @property
    def products(self) -> PostgresProductRepository:
        if not self._product_repo:
            self._product_repo = PostgresProductRepository(self.session)
        return self._product_repo
    
    @property
    def invoices(self) -> IInvoiceRepository:
        if not self._invoice_repo:
            self._invoice_repo = PostgresInvoiceRepository(self.session)
        return self._invoice_repo
    
    @property
    def purchase_orders(self) -> IPurchaseOrderRepository:
        if not self._purchase_order_repo:
            self._purchase_order_repo = PostgresPurchaseOrderRepository(self.session)
        return self._purchase_order_repo
    
    @property
    def customers(self) -> ICustomerRepository:
        if not self._customer_repo:
            self._customer_repo = PostgresCustomerRepository(self.session)
        return self._customer_repo
    
    @property
    def suppliers(self) -> ISupplierRepository:
        if not self._supplier_repo:
            self._supplier_repo = PostgresSupplierRepository(self.session)
        return self._supplier_repo
    
    @property
    def settings(self) -> ISettingsRepository:
        if not self._settings_repo:
            self._settings_repo = PostgresSettingsRepository(self.session)
        return self._settings_repo
    
    @property
    def currencies(self) -> PostgresCurrencyRepository:
        if not self._currency_repo:
            self._currency_repo = PostgresCurrencyRepository(self.session)
        return self._currency_repo
    
    @property
    def funds(self) -> PostgresFundRepository:
        if not self._fund_repo:
            self._fund_repo = PostgresFundRepository(self.session)
        return self._fund_repo
    
    @property
    def fund_movements(self) -> PostgresFundMovementRepository:
        if not self._fund_movement_repo:
            self._fund_movement_repo = PostgresFundMovementRepository(self.session)
        return self._fund_movement_repo
    
    @property
    def sites(self) -> ISiteRepository:
        if not self._site_repo:
            self._site_repo = PostgresSiteRepository(self.session)
        return self._site_repo

    @property
    def customer_branches(self) -> PostgresCustomerBranchRepository:
        """مستودع فروع العملاء"""
        if not self._customer_branch_repo:
            self._customer_branch_repo = PostgresCustomerBranchRepository(self.session)
        return self._customer_branch_repo
    
    @property
    def payments(self) -> PostgresPaymentRepository:
        if not self._payment_repo:
            self._payment_repo = PostgresPaymentRepository(self.session)
        return self._payment_repo

    @property
    def financial_statements(self) -> PostgresFinancialStatementRepository:
        """مستودع القوائم المالية"""
        if not self._financial_statement_repo:
            self._financial_statement_repo = PostgresFinancialStatementRepository(self.session)
        return self._financial_statement_repo
    
    # =========================================================================
    # مستودعات المخزون
    # =========================================================================
    
    @property
    def stock_movements(self) -> PostgresStockMovementRepository:
        """مستودع حركات المخزون"""
        if not self._stock_movement_repo:
            self._stock_movement_repo = PostgresStockMovementRepository(self.session)
        return self._stock_movement_repo
    
    @property
    def stock_batches(self) -> PostgresStockBatchRepository:
        """مستودع دفعات المخزون"""
        if not self._stock_batch_repo:
            self._stock_batch_repo = PostgresStockBatchRepository(self.session)
        return self._stock_batch_repo
    
    @property
    def stock_transfers(self) -> PostgresStockTransferRepository:
        """مستودع تحويلات المخزون"""
        if not self._stock_transfer_repo:
            self._stock_transfer_repo = PostgresStockTransferRepository(self.session)
        return self._stock_transfer_repo
    
    # =========================================================================
    # مستودعات سير العمل (Workflow)
    # =========================================================================
    
    @property
    def workflows(self) -> PostgresWorkflowRepository:
        """مستودع سير العمل"""
        if not self._workflow_repo:
            self._workflow_repo = PostgresWorkflowRepository(self.session)
        return self._workflow_repo
    
    @property
    def approval_requests(self) -> PostgresApprovalRequestRepository:
        """مستودع طلبات الموافقة"""
        if not self._approval_request_repo:
            self._approval_request_repo = PostgresApprovalRequestRepository(self.session)
        return self._approval_request_repo
    
    # =========================================================================
    # مستودعات الأمان (Authentication & Authorization)
    # =========================================================================
    
    @property
    def users(self) -> PostgresUserRepository:
        """مستودع المستخدمين"""
        if not self._user_repo:
            self._user_repo = PostgresUserRepository(self.session)
        return self._user_repo
    
    @property
    def roles(self) -> PostgresRoleRepository:
        """مستودع الأدوار"""
        if not self._role_repo:
            self._role_repo = PostgresRoleRepository(self.session)
        return self._role_repo
    
    @property
    def permissions(self) -> PostgresPermissionRepository:
        """مستودع الصلاحيات"""
        if not self._permission_repo:
            self._permission_repo = PostgresPermissionRepository(self.session)
        return self._permission_repo
    
    # =========================================================================
    # ✅ مستودعات الضرائب (Tax)
    # =========================================================================
    
    @property
    def taxes(self) -> PostgresTaxRepository:
        """مستودع القواعد الضريبية"""
        if self._tax_repo is None:
            self._tax_repo = PostgresTaxRepository(self.session)
        return self._tax_repo
    
    @property
    def tax_groups(self) -> PostgresTaxGroupRepository:
        """مستودع مجموعات الضرائب"""
        if self._tax_group_repo is None:
            self._tax_group_repo = PostgresTaxGroupRepository(self.session)
        return self._tax_group_repo
    
    @property
    def tax_exemptions(self) -> PostgresTaxExemptionRepository:
        """مستودع الإعفاءات الضريبية"""
        if self._tax_exemption_repo is None:
            self._tax_exemption_repo = PostgresTaxExemptionRepository(self.session)
        return self._tax_exemption_repo
    
    @property
    def tax_periods(self) -> PostgresTaxPeriodRepository:
        """مستودع الفترات الضريبية"""
        if self._tax_period_repo is None:
            self._tax_period_repo = PostgresTaxPeriodRepository(self.session)
        return self._tax_period_repo
    
    # =========================================================================
    # ✅ مستودعات مراكز التكلفة (Centers)
    # =========================================================================
    
    @property
    def centers(self) -> PostgresCenterRepository:
        """مستودع مراكز التكلفة والربح"""
        if self._center_repo is None:
            self._center_repo = PostgresCenterRepository(self.session)
        return self._center_repo
    
    @property
    def center_allocations(self) -> PostgresAllocationRepository:
        """مستودع توزيعات مراكز التكلفة"""
        if self._center_allocation_repo is None:
            self._center_allocation_repo = PostgresAllocationRepository(self.session)
        return self._center_allocation_repo
    
    @property
    def center_allocation_rules(self) -> PostgresAllocationRuleRepository:
        """مستودع قواعد توزيع مراكز التكلفة"""
        if self._center_allocation_rule_repo is None:
            self._center_allocation_rule_repo = PostgresAllocationRuleRepository(self.session)
        return self._center_allocation_rule_repo

    # =========================================================================
    # ✅ مستودعات الأصول الثابتة (Fixed Assets)
    # =========================================================================

    @property
    def assets(self) -> PostgresFixedAssetRepository:
        """مستودع الأصول الثابتة"""
        if self._fixed_asset_repo is None:
            self._fixed_asset_repo = PostgresFixedAssetRepository(self.session)
        return self._fixed_asset_repo

    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def flush(self) -> None:
        """تنفيذ عمليات SQL المعلقة دون Commit"""
        if self._session:
            self._session.flush()
    
    def refresh(self, obj: Any) -> None:
        """تحديث كائن من قاعدة البيانات"""
        if self._session:
            self._session.refresh(obj)
    
    @property
    def is_active(self) -> bool:
        """التحقق من وجود جلسة نشطة"""
        return self._session is not None and self._session.is_active


__all__ = ["SessionFactory", "PostgresUnitOfWork"]