"""
بدء تشغيل التطبيق - Bootstrap الرئيسي
الإصدار المحسن - متوافق مع الحاوية الجديدة
✅ محدث: إضافة دعم FundsNotificationModel
✅ محدث: التحقق من جميع النماذج قبل إنشاء الجداول
"""

import logging
from typing import Optional, Dict, Any, Callable, Union
from datetime import datetime
import threading
import inspect
from contextlib import contextmanager

from .config import BootstrapConfig
from .container import DependencyContainer, ServiceLifetime
from .modules import register_all_modules
from .seed import SeedData

# استيراد الخدمات الأساسية
from core.infrastructure.bus.in_memory_event_bus import InMemoryEventBus
from core.infrastructure.messaging.command_bus import CommandBus
from core.infrastructure.messaging.query_bus import QueryBus
from core.infrastructure.db.postgres.unit_of_work import SessionFactory, PostgresUnitOfWork
from core.domain.shared.clock import SystemClock, set_clock

logger = logging.getLogger(__name__)


class Bootstrap:
    """
    Bootstrap الرئيسي - تهيئة وتجميع جميع مكونات النظام
    """
    
    def __init__(self, config: Union[BootstrapConfig, Dict[str, Any]]):
        """تهيئة Bootstrap"""
        if isinstance(config, dict):
            self._config = BootstrapConfig(**config)
        else:
            self._config = config
        
        self._container = DependencyContainer()
        self._session_factory: Optional[SessionFactory] = None
        self._seed_data = SeedData()
        self._user_context = None
        self._initialized = False
        
        # التخزين المؤقت
        self._permission_cache: Dict[str, set] = {}
        self._user_cache: Dict[str, Any] = {}
    
    # =========================================================================
    # التهيئة الرئيسية
    # =========================================================================
    
    def initialize(self) -> None:
        """تهيئة جميع مكونات النظام"""
        if self._initialized:
            logger.warning("Bootstrap already initialized")
            return
        
        logger.info(" Initializing Bootstrap...")
        
        # 1. تهيئة خدمة الوقت
        self._initialize_clock()
        
        # 2. تهيئة قاعدة البيانات
        self._initialize_database()
        
        # ✅ التأكد من استيراد جميع النماذج قبل إنشاء الجداول
        self._ensure_all_models_imported()
        
        # ✅ إنشاء الجداول باستخدام الطريقة الآمنة
        self.create_tables()
        
        # ✅ التأكد من وجود جدول الإشعارات (حل المشكلة)
        self._ensure_notification_table()
        
        logger.info("✅ Database tables created")
        
        # 3. تسجيل الخدمات الأساسية
        self._register_core_services()
        
        # 4. تسجيل جميع الوحدات
        register_all_modules(self._container, self._config.__dict__)
        
        # 5. تهيئة الأمان
        if self._config.enable_auth:
            self._initialize_security()
        
        # 6. تهيئة خدمة السنة المالية
        self._initialize_fiscal_service()
        
        # 7. إدخال البيانات الافتراضية (بعد إنشاء الجداول)
        if self._config.seed_data:
            self.seed_default_data()
        
        self._initialized = True
        logger.info("✅ Bootstrap initialized successfully")
    
    # =========================================================================
    # تهيئة خدمة الوقت
    # =========================================================================
    
    def _initialize_clock(self) -> None:
        """تهيئة خدمة الوقت"""
        logger.info("⏰ Initializing Clock Service...")
        
        if self._config.fixed_time:
            from core.domain.shared.clock import FixedClock
            clock = FixedClock(self._config.fixed_time)
            logger.info(f"   Fixed clock set to: {self._config.fixed_time}")
        else:
            clock = SystemClock()
            logger.info("   System clock initialized")
        
        set_clock(clock)
        self._container.register_instance("clock", clock)
    
    @property
    def clock(self):
        return self._container.resolve("clock")
    
    # =========================================================================
    # تهيئة قاعدة البيانات
    # =========================================================================
    
    def _initialize_database(self) -> None:
        """تهيئة قاعدة البيانات"""
        logger.info("🗄️ Initializing Database...")
        
        self._session_factory = SessionFactory(
            connection_string=self._config.database_url,
            echo=self._config.echo_sql,
            pool_size=self._config.pool_size,
            max_overflow=self._config.max_overflow
        )
        
        self._container.register_instance("session_factory", self._session_factory)
        
        # ✅ تسجيل Unit of Work كـ Scoped في الحاوية الجديدة
        self._container.register_scoped(
            "uow",
            PostgresUnitOfWork,
            dependencies=["session_factory", "event_bus"]
        )
        
        logger.info("   Database initialized")
    
    # =========================================================================
    # ✅ التأكد من استيراد جميع النماذج (محدث)
    # =========================================================================
    
    def _ensure_all_models_imported(self) -> None:
        """
        التأكد من استيراد جميع النماذج في Base.metadata قبل إنشاء الجداول.
        هذا يحل مشكلة الجداول المفقودة مثل notifications و funds_notifications.
        """
        try:
            # ✅ استيراد all_models لضمان تسجيل جميع النماذج في Base.metadata
            from core.infrastructure.db.models.all_models import Base as AllModelsBase
            
            # ✅ الحصول على الـ Base الأساسي
            from core.infrastructure.db.models.account_model import Base
            
            # =================================================================
            # 1. التحقق من وجود NotificationModel (جدول notifications)
            # =================================================================
            table = Base.metadata.tables.get("notifications")
            if table is None:
                logger.warning("⚠️ NotificationModel not found in Base.metadata, forcing import...")
                from core.infrastructure.db.models.notification_model import NotificationModel
                table = Base.metadata.tables.get("notifications")
                if table is not None:
                    logger.info("✅ NotificationModel successfully registered in Base.metadata")
                else:
                    logger.error("❌ Failed to register NotificationModel in Base.metadata")
            else:
                logger.debug("✅ NotificationModel already in Base.metadata")
            
            # =================================================================
            # 2. ✅ التحقق من وجود FundsNotificationModel (جدول funds_notifications)
            # =================================================================
            table_funds = Base.metadata.tables.get("funds_notifications")
            if table_funds is None:
                logger.warning("⚠️ FundsNotificationModel not found in Base.metadata, forcing import...")
                from core.infrastructure.db.models.notification_model import FundsNotificationModel
                table_funds = Base.metadata.tables.get("funds_notifications")
                if table_funds is not None:
                    logger.info("✅ FundsNotificationModel successfully registered in Base.metadata")
                else:
                    logger.error("❌ Failed to register FundsNotificationModel in Base.metadata")
            else:
                logger.debug("✅ FundsNotificationModel already in Base.metadata")
            
            # =================================================================
            # 3. ✅ التأكد من وجود جميع النماذج الأخرى المهمة
            # =================================================================
            # قائمة بالجداول التي يجب أن تكون موجودة
            required_tables = [
                "accounts",
                "journal_entries",
                "journal_lines",
                "ledger_entries",
                "fiscal_years",
                "fiscal_periods",
                "products",
                "customers",
                "suppliers",
                "invoices",
                "invoice_lines",
                "payments",
                "funds",
                "fund_movements",
                "fund_transfers",
                "stock_movements",
                "stock_batches",
                "stock_transfers",
                "tax_rules",
                "tax_exemptions",
                "tax_periods",
                "centers",
                "center_allocations",
                "sites",
                "users",
                "roles",
                "permissions",
                "audit_logs",
            ]
            
            missing_tables = []
            for table_name in required_tables:
                if Base.metadata.tables.get(table_name) is None:
                    missing_tables.append(table_name)
            
            if missing_tables:
                logger.warning(f"⚠️ Missing tables in Base.metadata: {', '.join(missing_tables)}")
                # محاولة استيراد النماذج الناقصة
                try:
                    # استيراد جميع النماذج من all_models
                    from core.infrastructure.db.models.all_models import Base as AllBase
                    # التحقق مرة أخرى
                    for table_name in missing_tables.copy():
                        if Base.metadata.tables.get(table_name) is not None:
                            missing_tables.remove(table_name)
                    if missing_tables:
                        logger.error(f"❌ Still missing tables: {', '.join(missing_tables)}")
                except Exception as e:
                    logger.error(f"❌ Failed to import all models: {e}")
            else:
                logger.debug("✅ All required tables are present in Base.metadata")
                    
        except Exception as e:
            logger.error(f"❌ Failed to ensure all models are imported: {e}")
    
    # =========================================================================
    # ✅ التأكد من وجود جدول الإشعارات (النسخة النهائية)
    # =========================================================================
    
    def _ensure_notification_table(self) -> None:
        """
        التأكد من وجود جدول الإشعارات وجميع الفهارس في قاعدة البيانات.
        يستخدم CREATE IF NOT EXISTS لتجنب أخطاء DuplicateTable.
        """
        from sqlalchemy import text
        
        if not self._session_factory:
            logger.warning("⚠️ Session factory not available")
            return
        
        try:
            with self._session_factory.engine.connect() as conn:
                # تعطيل التحقق من المفاتيح الخارجية مؤقتاً
                conn.execute(text("SET session_replication_role = 'replica';"))
                
                # ✅ إنشاء جدول notifications (إذا لم يكن موجوداً)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR(100) NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        message TEXT NOT NULL,
                        notification_type VARCHAR(50) NOT NULL DEFAULT 'system',
                        is_read BOOLEAN NOT NULL DEFAULT FALSE,
                        data JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        read_at TIMESTAMPTZ
                    )
                """))
                
                # ✅ إنشاء جدول funds_notifications (إذا لم يكن موجوداً)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS funds_notifications (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR(100) NOT NULL,
                        role VARCHAR(50),
                        title VARCHAR(200) NOT NULL,
                        message TEXT NOT NULL,
                        notification_type VARCHAR(50) NOT NULL DEFAULT 'system',
                        is_read BOOLEAN NOT NULL DEFAULT FALSE,
                        is_sent BOOLEAN NOT NULL DEFAULT FALSE,
                        data JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        read_at TIMESTAMPTZ,
                        sent_at TIMESTAMPTZ
                    )
                """))
                
                # ✅ إنشاء فهارس notifications
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications (is_read)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications (notification_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications (user_id, is_read)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications (created_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications (created_at)"))
                
                # ✅ إنشاء فهارس funds_notifications
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_funds_notifications_user_id ON funds_notifications (user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_funds_notifications_is_read ON funds_notifications (is_read)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_funds_notifications_notification_type ON funds_notifications (notification_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_funds_notifications_role ON funds_notifications (role)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_funds_notifications_created_at ON funds_notifications (created_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_funds_notifications_user_read ON funds_notifications (user_id, is_read)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_funds_notifications_created ON funds_notifications (created_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_funds_notifications_type_sent ON funds_notifications (notification_type, is_sent)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_funds_notifications_role ON funds_notifications (role, is_read)"))
                
                # إنشاء جدول audit_log
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        entity_type VARCHAR(100) NOT NULL,
                        entity_id VARCHAR(100),
                        action VARCHAR(50) NOT NULL,
                        performed_by VARCHAR(100),
                        old_values JSONB DEFAULT '{}'::jsonb,
                        new_values JSONB DEFAULT '{}'::jsonb,
                        ip_address VARCHAR(50),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log (entity_type, entity_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_log_performed_by ON audit_log (performed_by)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log (created_at)"))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS currencies (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        code VARCHAR(3) NOT NULL UNIQUE,
                        name VARCHAR(100) NOT NULL,
                        symbol VARCHAR(10) NOT NULL DEFAULT '',
                        decimal_places INT NOT NULL DEFAULT 2,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_base BOOLEAN NOT NULL DEFAULT FALSE,
                        exchange_rates JSONB DEFAULT '[]'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        created_by VARCHAR(100) NOT NULL DEFAULT 'system',
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_by VARCHAR(100) NOT NULL DEFAULT 'system',
                        version INT NOT NULL DEFAULT 1
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_currencies_code ON currencies (code)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_currencies_is_active ON currencies (is_active)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_currencies_is_base ON currencies (is_base)"))
                
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS exchange_rate_history (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        from_currency_code VARCHAR(3) NOT NULL,
                        to_currency_code VARCHAR(3) NOT NULL,
                        rate NUMERIC(18,8) NOT NULL,
                        changed_by VARCHAR(100) NOT NULL DEFAULT 'system',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_erh_from_to ON exchange_rate_history (from_currency, to_currency)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_erh_created ON exchange_rate_history (created_at)"))
                
                iqd_rates = '[{"from_currency":"IQD","to_currency":"USD","rate":0.00076},{"from_currency":"IQD","to_currency":"EUR","rate":0.00070}]'
                usd_rates = '[{"from_currency":"USD","to_currency":"IQD","rate":1310.00},{"from_currency":"USD","to_currency":"EUR","rate":0.92}]'
                eur_rates = '[{"from_currency":"EUR","to_currency":"USD","rate":1.09},{"from_currency":"EUR","to_currency":"IQD","rate":1430.00}]'

                conn.execute(text("""
                    INSERT INTO currencies (id, code, name, symbol, decimal_places, is_active, is_base, exchange_rates, created_at, created_by, updated_at, updated_by, version)
                    SELECT gen_random_uuid(), 'IQD', 'دينار عراقي', 'د.ع', 3, TRUE, TRUE,
                        CAST(:rates AS jsonb), NOW(), 'system', NOW(), 'system', 1
                    WHERE NOT EXISTS (SELECT 1 FROM currencies WHERE code = 'IQD')
                """), {"rates": iqd_rates})
                conn.execute(text("""
                    INSERT INTO currencies (id, code, name, symbol, decimal_places, is_active, is_base, exchange_rates, created_at, created_by, updated_at, updated_by, version)
                    SELECT gen_random_uuid(), 'USD', 'دولار أمريكي', '$', 2, FALSE, FALSE,
                        CAST(:rates AS jsonb), NOW(), 'system', NOW(), 'system', 1
                    WHERE NOT EXISTS (SELECT 1 FROM currencies WHERE code = 'USD')
                """), {"rates": usd_rates})
                conn.execute(text("""
                    INSERT INTO currencies (id, code, name, symbol, decimal_places, is_active, is_base, exchange_rates, created_at, created_by, updated_at, updated_by, version)
                    SELECT gen_random_uuid(), 'EUR', 'يورو', '€', 2, FALSE, FALSE,
                        CAST(:rates AS jsonb), NOW(), 'system', NOW(), 'system', 1
                    WHERE NOT EXISTS (SELECT 1 FROM currencies WHERE code = 'EUR')
                """), {"rates": eur_rates})
                
                # إعادة تفعيل التحقق من المفاتيح الخارجية
                conn.execute(text("SET session_replication_role = 'origin';"))
                conn.commit()
                
            logger.info("✅ Notifications, funds_notifications, and audit_log tables ensured")
            
        except Exception as e:
            # ✅ لا نرفع الاستثناء لمنع تعطل التطبيق
            logger.warning(f"⚠️ Failed to ensure notification tables: {e}")
            logger.warning("⚠️ Continuing despite notification table error")
    
    # =========================================================================
    # تسجيل الخدمات الأساسية
    # =========================================================================
    
    def _register_core_services(self) -> None:
        """تسجيل الخدمات الأساسية في الحاوية"""
        logger.info("🔧 Registering core services...")
        
        # Event Bus - Singleton
        event_bus = InMemoryEventBus()
        self._container.register_instance("event_bus", event_bus)
        
        # Command Bus - Singleton
        command_bus = CommandBus()
        self._container.register_instance("command_bus", command_bus)
        
        # Query Bus - Singleton
        query_bus = QueryBus()
        self._container.register_instance("query_bus", query_bus)
        
        # ✅ تثبيت حلّال المعالجات: يُنشئ نطاقاً جديداً (جلسة جديدة) لكل إرسال
        # وتبقى الجلسة مفتوحة طوال مدة تنفيذ المعالج.
        # هذا يمنع مشاركة جلسة قاعدة بيانات واحدة بين جميع الطلبات.
        # كما يحقن سياق المستخدم الحالي (من الـ API) في المعالج الذي يقبله.
        from core.application.security.authorization import get_current_user_context
        def bus_handler_resolver(handler_name: str):
            def execute(command):
                with self.scope() as scoped_container:
                    handler = scoped_container.resolve(handler_name)
                    handle = handler.handle
                    if "user_context" in inspect.signature(handle).parameters:
                        return handle(command, user_context=get_current_user_context())
                    return handle(command)
            return execute
        
        command_bus.set_handler_resolver(bus_handler_resolver)
        query_bus.set_handler_resolver(bus_handler_resolver)
        
        # Session Manager (للأمان) - Singleton
        from core.application.security.authentication import SessionManager
        session_manager = SessionManager(
            secret_key=self._config.secret_key,
            session_timeout=self._config.session_timeout
        )
        self._container.register_instance("session_manager", session_manager)
        
        # Login Tracker (للأمان) - Singleton
        from core.application.security.authentication import LoginAttemptTracker
        login_tracker = LoginAttemptTracker(
            max_attempts=self._config.max_login_attempts,
            lockout_minutes=self._config.lockout_minutes
        )
        self._container.register_instance("login_tracker", login_tracker)
        
        logger.info("   Core services registered")
    
    # =========================================================================
    # تهيئة الأمان
    # =========================================================================
    
    def _initialize_security(self) -> None:
        """تهيئة أنظمة الأمان"""
        logger.info("🔐 Initializing Security...")
        
        from core.application.security.authorization import PermissionManager
        
        # مزود الصلاحيات من قاعدة البيانات
        def get_permissions_provider(user_id: str) -> set:
            """جلب صلاحيات المستخدم من قاعدة البيانات"""
            if user_id in self._permission_cache:
                return self._permission_cache[user_id]
            
            try:
                from core.application.security.authorization import get_user_permissions_from_db
                # ✅ استخدام نطاق (scope) بدلاً من uow مباشرة
                with self.scope() as container:
                    uow = container.resolve("uow")
                    with uow:
                        permissions = get_user_permissions_from_db(user_id, uow)
                        self._permission_cache[user_id] = permissions
                        return permissions
            except Exception as e:
                logger.error(f"Error getting permissions for user {user_id}: {e}")
                return set()
        
        # تهيئة Permission Manager
        permission_manager = PermissionManager.instance()
        permission_manager.initialize(get_permissions_provider)
        self._container.register_instance("permission_manager", permission_manager)
        
        logger.info("   Security initialized")
    
    # =========================================================================
    # تهيئة خدمة السنة المالية
    # =========================================================================
    
    def _initialize_fiscal_service(self) -> None:
        """تهيئة خدمة السنة المالية"""
        logger.info("📅 Initializing Fiscal Year Service...")
        
        # ✅ fiscal_service مسجّلة كـ Scoped في وحدة fiscal.py (جلسة لكل طلب).
        # هنا فقط نتحقق من وجود سنة مالية نشطة في نطاق مؤقت.
        try:
            with self.scope() as container:
                uow = container.resolve("uow")
                with uow:
                    fiscal_service = container.resolve("fiscal_service")
                    
                    # التحقق من وجود سنة مالية
                    current_year = fiscal_service.get_current_fiscal_year()
                    if not current_year:
                        logger.warning("   ⚠️ No active fiscal year found. Creating and opening current year...")
                        from core.domain.fiscal.entities import FiscalYear
                        from core.domain.fiscal.value_objects import FiscalPeriodType
                        from core.domain.shared.clock import get_clock
                        from datetime import date as _date
                        
                        clock = get_clock()
                        fy = clock.today().year
                        new_year = FiscalYear.create(
                            code=f"FY{fy}",
                            name=f"السنة المالية {fy}",
                            start_date=_date(fy, 1, 1),
                            end_date=_date(fy, 12, 31),
                            periods_per_year=12,
                            period_type=FiscalPeriodType.MONTH,
                            created_by="system"
                        )
                        new_year.open("system")
                        uow.fiscal_years.save(new_year)
                        uow.commit()
                        logger.info(f"   ✅ Auto-created and opened fiscal year: {new_year.code}")
                        current_year = fiscal_service.get_current_fiscal_year()
                    
                    if current_year:
                        logger.info(f"   Current fiscal year: {current_year.code}")
                        logger.info(f"   Periods: {len(current_year.periods)}")
                        logger.info(f"   Open periods: {len(current_year.open_periods)}")
                        
        except Exception as e:
            logger.error(f"   ❌ Failed to initialize Fiscal Service: {e}")
    
    # =========================================================================
    # إدارة النطاقات (Scopes) - ✅ الجديد
    # =========================================================================
    
    @contextmanager
    def scope(self):
        """
        إنشاء نطاق جديد للخدمات الـ Scoped
        
        الاستخدام:
            with bootstrap.scope() as container:
                uow = container.resolve("uow")
                with uow:
                    # استخدام uow...
        """
        with self._container.scope() as container:
            yield container
    
    @contextmanager
    def uow(self):
        """
        إنشاء نطاق مع Unit of Work جاهز
        
        الاستخدام:
            with bootstrap.uow() as uow:
                # استخدام uow...
                uow.commit()
        """
        with self.scope() as container:
            uow = container.resolve("uow")
            with uow:
                yield uow
    
    # =========================================================================
    # إدارة المستخدم
    # =========================================================================
    
    def set_user_context(self, user_context) -> None:
        """تعيين سياق المستخدم الحالي"""
        self._user_context = user_context
        logger.debug(f"👤 User context set: {getattr(user_context, 'username', 'unknown')}")
    
    def get_user_context(self):
        """الحصول على سياق المستخدم الحالي"""
        return self._user_context
    
    def authenticate_user(self, username: str, password: str, ip_address: Optional[str] = None):
        """مصادقة المستخدم"""
        if not self._config.enable_auth:
            logger.warning("⚠️ Authentication is disabled")
            return None
        
        # التحقق من محاولات الدخول
        login_tracker = self._container.resolve("login_tracker")
        if login_tracker and ip_address:
            if login_tracker.is_locked_out(ip_address):
                logger.warning(f"🔒 IP {ip_address} is locked out")
                return None
        
        # مصادقة المستخدم
        auth_service = self._container.resolve("auth_service")
        user = auth_service.authenticate(username, password)
        
        if not user:
            if login_tracker and ip_address:
                login_tracker.record_failed_attempt(ip_address)
            return None
        
        # إنشاء سياق المستخدم
        from core.application.security.authorization import UserContext
        permission_manager = self._container.resolve("permission_manager")
        user_context = permission_manager.get_user_context(
            user_id=str(user.id.value),
            username=user.username,
            roles=[role.name for role in user.roles],
            is_super_admin=user.is_super_admin
        )
        
        # تسجيل الجلسة
        session_manager = self._container.resolve("session_manager")
        if session_manager:
            session_id = session_manager.create_session({
                'user_id': str(user.id.value),
                'username': user.username,
                'ip_address': ip_address,
            })
            user_context.session_id = session_id
        
        # تحديث آخر تسجيل دخول - ✅ استخدام uow()
        with self.uow() as uow:
            user_repo = uow.users
            user.last_login = self.clock.now()
            user_repo.save(user)
            uow.commit()
        
        # مسح محاولات الدخول الفاشلة
        if login_tracker and ip_address:
            login_tracker.reset_attempts(ip_address)
        
        logger.info(f"✅ User authenticated: {username}")
        return user_context
    
    def logout_user(self, user_context) -> None:
        """تسجيل خروج المستخدم"""
        session_manager = self._container.resolve("session_manager")
        if session_manager and user_context.session_id:
            session_manager.invalidate_session(user_context.session_id)
        
        if self._user_context and self._user_context.user_id == user_context.user_id:
            self._user_context = None
        
        logger.info(f"👋 User logged out: {user_context.username}")
    
    def validate_session(self, session_id: str):
        """التحقق من صحة الجلسة"""
        session_manager = self._container.resolve("session_manager")
        if not session_manager:
            return None
        
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return None
        
        user_id = session_data.get('user_id')
        if not user_id:
            return None
        
        # التحقق من الكاش
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        # جلب من قاعدة البيانات - ✅ استخدام uow()
        with self.uow() as uow:
            user_repo = uow.users
            user = user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                return None
        
        from core.application.security.authorization import UserContext
        permission_manager = self._container.resolve("permission_manager")
        user_context = permission_manager.get_user_context(
            user_id=str(user.id.value),
            username=user.username,
            roles=[role.name for role in user.roles],
            is_super_admin=user.is_super_admin
        )
        user_context.session_id = session_id
        
        self._user_cache[user_id] = user_context
        return user_context
    
    def clear_user_cache(self, user_id: Optional[str] = None) -> None:
        """مسح كاش المستخدم"""
        if user_id:
            self._permission_cache.pop(user_id, None)
            self._user_cache.pop(user_id, None)
        else:
            self._permission_cache.clear()
            self._user_cache.clear()
        
        permission_manager = self._container.resolve("permission_manager")
        if permission_manager:
            permission_manager.clear_cache(user_id)
    
    # =========================================================================
    # الوصول إلى الخدمات
    # =========================================================================
    
    @property
    def container(self) -> DependencyContainer:
        return self._container
    
    @property
    def command_bus(self) -> CommandBus:
        return self._container.resolve("command_bus")
    
    @property
    def query_bus(self) -> QueryBus:
        return self._container.resolve("query_bus")
    
    @property
    def event_bus(self) -> InMemoryEventBus:
        return self._container.resolve("event_bus")
    
    @property
    def session_factory(self) -> SessionFactory:
        return self._session_factory
    
    def get_service(self, name: str):
        return self._container.resolve(name)
    
    def register_service(self, name: str, service) -> None:
        self._container.register_instance(name, service)
    
    # =========================================================================
    # ✅ إدارة قاعدة البيانات - الجزء المُصلح
    # =========================================================================
    
    def create_tables(self, use_safe_method: bool = True) -> None:
        """
        إنشاء جداول قاعدة البيانات.
        
        Args:
            use_safe_method: إذا كان True، يستخدم الطريقة الآمنة التي تتحقق من وجود
                            الجداول والفهارس قبل إنشائها.
        """
        if not self._session_factory:
            logger.error("❌ Session factory not initialized")
            return
        
        try:
            if use_safe_method:
                # ✅ استخدام الطريقة الآمنة مع تقرير تفصيلي
                report = self._session_factory.create_tables_safe()
                
                # طباعة التقرير
                print("\n" + "=" * 60)
                print(" Database Tables Creation Report")
                print("=" * 60)
                
                print(f"\n[OK] Total tables: {report.get('total_tables', 0)}")
                print(f"   Existing tables: {report.get('existing_tables', 0)}")
                
                if report.get('tables_created'):
                    print(f"\n[CREATED] Tables created ({len(report['tables_created'])}):")
                    for table in report['tables_created'][:10]:
                        print(f"   - {table}")
                    if len(report['tables_created']) > 10:
                        print(f"   ... and {len(report['tables_created']) - 10} more")
                
                if report.get('tables_skipped'):
                    print(f"\n[SKIP] Tables skipped (already exist) ({len(report['tables_skipped'])}):")
                    for table in report['tables_skipped'][:5]:
                        print(f"   - {table}")
                    if len(report['tables_skipped']) > 5:
                        print(f"   ... and {len(report['tables_skipped']) - 5} more")
                
                if report.get('indexes_created'):
                    print(f"\n[CREATED] Indexes created ({len(report['indexes_created'])}):")
                    for idx in report['indexes_created'][:5]:
                        print(f"   - {idx}")
                    if len(report['indexes_created']) > 5:
                        print(f"   ... and {len(report['indexes_created']) - 5} more")
                
                if report.get('indexes_skipped'):
                    print(f"\n[SKIP] Indexes skipped (already exist) ({len(report['indexes_skipped'])}):")
                    for idx in report['indexes_skipped'][:5]:
                        print(f"   - {idx}")
                    if len(report['indexes_skipped']) > 5:
                        print(f"   ... and {len(report['indexes_skipped']) - 5} more")
                
                if report.get('errors'):
                    print(f"\n[ERROR] ({len(report['errors'])}):")
                    for error in report['errors'][:5]:
                        print(f"   - {error}")
                    if len(report['errors']) > 5:
                        print(f"   ... and {len(report['errors']) - 5} more")
                
                print("\n" + "=" * 60)
                
                if report.get('success', False):
                    logger.info("Database tables created successfully")
                else:
                    logger.warning("Database creation completed with errors")
                    
                # tarkiya al-makhut
                try:
                    upgrades = self._session_factory.ensure_schema_upgrades()
                    if upgrades:
                        print(f"\n[UPGRADED] Schema upgrades applied ({len(upgrades)}):")
                        for upgrade in upgrades:
                            print(f"   - {upgrade}")
                except Exception as e:
                    logger.error(f"Schema upgrades failed: {e}")
                    
            else:
                # الطريقة البسيطة
                self._session_factory.create_tables()
                logger.info("✅ Database tables created")
                
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            raise
    
    def drop_tables(self) -> None:
        """حذف جداول قاعدة البيانات"""
        if self._session_factory:
            self._session_factory.drop_tables()
            logger.warning("⚠️ Database tables dropped")
    
    def recreate_tables(self) -> None:
        """
        إعادة إنشاء جميع الجداول (حذف ثم إنشاء).
        ⚠️ استخدم هذا فقط في بيئة التطوير!
        """
        logger.warning("⚠️ Recreating all database tables! This will delete all data.")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        
        if confirm.lower() == 'yes':
            self.drop_tables()
            self.create_tables()
            logger.info("✅ Database tables recreated")
        else:
            logger.info("❌ Operation cancelled")
    
    def seed_default_data(self) -> None:
        """إدخال البيانات الافتراضية"""
        with self.uow() as uow:
            self._seed_data.seed_all(uow)
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def get_current_fiscal_period(self) -> Optional[str]:
        with self.scope() as container:
            fiscal_service = container.resolve("fiscal_service")
            if fiscal_service:
                period = fiscal_service.get_current_period()
                if period:
                    return str(period.reference)
        return None
    
    def get_fiscal_year_summary(self) -> Dict[str, Any]:
        with self.scope() as container:
            fiscal_service = container.resolve("fiscal_service")
            if not fiscal_service:
                return {"error": "Fiscal year service not available"}
            
            year = fiscal_service.get_current_fiscal_year()
            if not year:
                return {"error": "No active fiscal year found"}
            
            return fiscal_service.get_fiscal_year_summary(str(year.id))
    
    def get_periods_summary(self) -> Dict[str, Any]:
        with self.scope() as container:
            fiscal_service = container.resolve("fiscal_service")
            if not fiscal_service:
                return {"error": "Fiscal year service not available"}
            
            year = fiscal_service.get_current_fiscal_year()
            if not year:
                return {"error": "No active fiscal year found"}
            
            return {
                "total_periods": len(year.periods),
                "open_periods": len(year.open_periods),
                "closed_periods": len(year.closed_periods),
                "current_period": str(year.current_period.reference) if year.current_period else None,
                "completion_percentage": year.completion_percentage,
            }
    
    def is_period_open(self, period_reference: str) -> bool:
        with self.scope() as container:
            fiscal_service = container.resolve("fiscal_service")
            if not fiscal_service:
                return True
            
            from core.domain.fiscal.value_objects import FiscalPeriodReference
            ref = FiscalPeriodReference.from_string(period_reference)
            return fiscal_service.is_period_open(ref)
    
    def get_allowed_posting_date_range(self):
        with self.scope() as container:
            fiscal_service = container.resolve("fiscal_service")
            if not fiscal_service:
                return None, None
            
            period = fiscal_service.get_current_period()
            if not period:
                return None, None
            
            return period.start_date, period.end_date


# =========================================================================
# دوال مساعدة عالمية
# =========================================================================

_bootstrap_instance: Optional[Bootstrap] = None


def init_bootstrap(
    database_url: str,
    echo_sql: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    secret_key: str = "change-me-in-production",
    user_context: Any = None,
    seed_data: bool = False,
    fixed_time: Optional[datetime] = None,
    **kwargs
) -> Bootstrap:
    """تهيئة Bootstrap العالمية"""
    global _bootstrap_instance
    
    logger.info("🚀 Initializing global Bootstrap...")
    
    config = BootstrapConfig(
        database_url=database_url,
        echo_sql=echo_sql,
        pool_size=pool_size,
        max_overflow=max_overflow,
        secret_key=secret_key,
        seed_data=seed_data,
        fixed_time=fixed_time,
        **kwargs
    )
    
    _bootstrap_instance = Bootstrap(config)
    _bootstrap_instance.initialize()
    
    if user_context:
        _bootstrap_instance.set_user_context(user_context)
    
    logger.info("✅ Global Bootstrap initialized")
    return _bootstrap_instance


def get_bootstrap() -> Bootstrap:
    """الحصول على Bootstrap العالمي"""
    global _bootstrap_instance
    if _bootstrap_instance is None:
        raise RuntimeError("Bootstrap not initialized. Call init_bootstrap() first.")
    return _bootstrap_instance


def get_session_factory():
    return get_bootstrap().session_factory


def get_command_bus() -> CommandBus:
    return get_bootstrap().command_bus


def get_query_bus() -> QueryBus:
    return get_bootstrap().query_bus


def get_event_bus() -> InMemoryEventBus:
    return get_bootstrap().event_bus


def get_user_context():
    return get_bootstrap().get_user_context()


def get_clock_service():
    return get_bootstrap().clock


def get_fiscal_service():
    return get_bootstrap().get_service("fiscal_service")


def get_current_fiscal_period():
    return get_bootstrap().get_current_fiscal_period()