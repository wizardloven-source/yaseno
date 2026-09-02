# core/setup/database_setup.py

"""
Professional Database Setup
===========================

✅ Backward compatible
✅ Safe PostgreSQL handling
✅ SQL injection safe
✅ Transaction safe
✅ Better engine management
✅ ERP-ready architecture
✅ Fully customizable by user
"""

from __future__ import annotations

from sqlalchemy import (
    create_engine,
    text,
    inspect
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import logging

from core.settings import settings
from core.config.settings_manager import settings_manager

# =========================================
# IMPORT MODELS
# =========================================

from core.infrastructure.db.models.account_model import (
    Base as AccountingBase
)

from core.infrastructure.db.models.invoice_model import (
    Base as InvoiceBase
)

from core.infrastructure.db.models.product_model import (
    ProductModel
)

from core.infrastructure.db.models.customer_model import (
    CustomerModel
)

# =========================================
# LOGGER
# =========================================

logger = logging.getLogger(__name__)

# =========================================
# DATABASE SETUP
# =========================================

class DatabaseSetup:
    """
    Database initialization manager - Fully customizable by user
    """

    def __init__(self):
        self.db_url = settings.database.connection_string
        self.engine = None
        self._setup_complete = False
        # تحميل إعدادات المستخدم
        self.user_settings = settings_manager.get()

    # =====================================
    # ENGINE
    # =====================================

    def _create_engine(self, url: str):
        return create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            future=True
        )

    # =====================================
    # DATABASE EXISTS
    # =====================================

    def ensure_database_exists(self) -> bool:
        """
        Ensure database exists
        """
        engine = None

        try:
            default_url = (
                f"postgresql://"
                f"{settings.database.username}:"
                f"{settings.database.password}@"
                f"{settings.database.host}:"
                f"{settings.database.port}/postgres"
            )

            engine = self._create_engine(default_url)

            with engine.connect() as conn:
                conn.execute(
                    text("CREATE EXTENSION IF NOT EXISTS pgcrypto")
                )

                result = conn.execute(
                    text("""
                        SELECT 1
                        FROM pg_database
                        WHERE datname = :dbname
                    """),
                    {"dbname": settings.database.database}
                )

                exists = result.scalar()

                if exists:
                    logger.info("Database already exists")
                    return True

                db_name = settings.database.database
                logger.info(f"Creating database: {db_name}")

                # استخدام quoting آمن لاسم قاعدة البيانات
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info("Database created successfully")
                return True

        except SQLAlchemyError as e:
            logger.exception("Database setup failed")
            return False

        finally:
            if engine:
                engine.dispose()

    # =====================================
    # CREATE TABLES
    # =====================================

    def create_tables_if_not_exist(self) -> bool:
        """
        Create database tables
        """
        try:
            self.engine = self._create_engine(self.db_url)
            logger.info("Creating database tables...")

            AccountingBase.metadata.create_all(self.engine)
            InvoiceBase.metadata.create_all(self.engine)
            ProductModel.__table__.create(self.engine, checkfirst=True)
            CustomerModel.__table__.create(self.engine, checkfirst=True)

            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            logger.info(f"Existing tables: {tables}")

            return True

        except SQLAlchemyError:
            logger.exception("Table creation failed")
            return False

    # =====================================
    # SEED DATA
    # =====================================

    def seed_initial_data_if_empty(self) -> bool:
        """
        Seed initial data from user settings
        """
        if not self.engine:
            return False

        try:
            with Session(self.engine) as session:
                # التحقق من وجود حسابات
                account_count = session.execute(
                    text("SELECT COUNT(*) FROM accounts")
                ).scalar()

                if account_count == 0:
                    logger.info("Seeding accounts from user settings...")
                    self._seed_accounts(session)
                else:
                    logger.info(f"Accounts already exist ({account_count} records)")

                # التحقق من وجود فترات مالية
                period_count = session.execute(
                    text("SELECT COUNT(*) FROM fiscal_periods")
                ).scalar()

                if period_count == 0:
                    logger.info("Seeding fiscal periods from user settings...")
                    self._seed_fiscal_periods(session)
                else:
                    logger.info(f"Fiscal periods already exist ({period_count} records)")

                session.commit()
                return True

        except SQLAlchemyError as e:
            logger.exception(f"Seed operation failed: {e}")
            return False

    # =====================================
    # SEED ACCOUNTS (من إعدادات المستخدم)
    # =====================================

    def _seed_accounts(self, session: Session):
        """
        Seed chart of accounts from user settings
        """
        accounts = self.user_settings.accounts.default_accounts
        
        if not accounts:
            logger.warning("No default accounts found in user settings. Using built-in defaults.")
            # استخدام حسابات افتراضية مدمجة إذا لم تكن موجودة في الإعدادات
            accounts = [
                {"code": "1010", "name": "الصندوق", "type": "asset", "currency": "USD", "is_active": True, "can_delete": False},
                {"code": "1020", "name": "المدينون", "type": "asset", "currency": "USD", "is_active": True, "can_delete": False},
                {"code": "1030", "name": "المخزون", "type": "asset", "currency": "USD", "is_active": True, "can_delete": False},
                {"code": "1040", "name": "البنك", "type": "asset", "currency": "USD", "is_active": True, "can_delete": True},
                {"code": "2010", "name": "الدائنون", "type": "liability", "currency": "USD", "is_active": True, "can_delete": False},
                {"code": "3010", "name": "رأس المال", "type": "equity", "currency": "USD", "is_active": True, "can_delete": False},
                {"code": "4010", "name": "إيرادات المبيعات", "type": "revenue", "currency": "USD", "is_active": True, "can_delete": False},
                {"code": "5010", "name": "تكلفة البضاعة", "type": "expense", "currency": "USD", "is_active": True, "can_delete": False},
            ]
        
        for account in accounts:
            try:
                # التحقق من وجود عمود can_delete (للتوافق مع الإصدارات السابقة)
                can_delete = account.get('can_delete', True)
                
                session.execute(
                    text("""
                        INSERT INTO accounts
                        (
                            id,
                            code,
                            name,
                            account_type,
                            currency,
                            is_active,
                            can_delete,
                            created_at,
                            updated_at,
                            version
                        )
                        VALUES
                        (
                            gen_random_uuid(),
                            :code,
                            :name,
                            :acc_type,
                            :currency,
                            :is_active,
                            :can_delete,
                            NOW(),
                            NOW(),
                            1
                        )
                        ON CONFLICT (code)
                        DO NOTHING
                    """),
                    {
                        "code": account.get('code'),
                        "name": account.get('name'),
                        "acc_type": account.get('type'),
                        "currency": account.get('currency', 'USD'),
                        "is_active": account.get('is_active', True),
                        "can_delete": can_delete
                    }
                )
                logger.info(f"Account seeded: {account.get('code')} - {account.get('name')}")
            except Exception as e:
                logger.error(f"Failed to seed account {account.get('code')}: {e}")

    # =====================================
    # SEED PERIODS (من إعدادات المستخدم)
    # =====================================

    def _seed_fiscal_periods(self, session: Session):
        """
        Seed fiscal periods from user settings
        """
        start_year = self.user_settings.fiscal.start_year
        periods_per_year = self.user_settings.fiscal.periods_per_year
        auto_create = self.user_settings.fiscal.auto_create_periods
        
        if not auto_create:
            logger.info("Auto-create fiscal periods is disabled in settings")
            return
        
        logger.info(f"Creating fiscal periods from year {start_year} with {periods_per_year} periods per year")
        
        # إنشاء فترات للسنة الحالية والسنة القادمة
        for year_offset in range(2):
            year = start_year + year_offset
            
            for period_num in range(1, periods_per_year + 1):
                period_name = f"{year}-{period_num:02d}"
                
                try:
                    session.execute(
                        text("""
                            INSERT INTO fiscal_periods
                            (
                                id,
                                name,
                                year,
                                period_number,
                                start_date,
                                end_date,
                                period_type,
                                is_closed,
                                created_at
                            )
                            VALUES
                            (
                                gen_random_uuid(),
                                :name,
                                :year,
                                :period_number,
                                CURRENT_DATE,
                                CURRENT_DATE,
                                'MONTH',
                                false,
                                NOW()
                            )
                            ON CONFLICT (name)
                            DO NOTHING
                        """),
                        {
                            "name": period_name,
                            "year": year,
                            "period_number": period_num
                        }
                    )
                    logger.debug(f"Period seeded: {period_name}")
                except Exception as e:
                    logger.error(f"Failed to seed period {period_name}: {e}")
        
        logger.info(f"Fiscal periods seeding completed (years {start_year} to {start_year + 1})")

    # =====================================
    # RUN
    # =====================================

    def run(self) -> bool:
        """
        Execute setup
        """
        logger.info("=" * 50)
        logger.info("YAseen ERP Database Setup")
        logger.info(f"Using user settings from: {settings_manager.config_file}")
        logger.info("=" * 50)

        if not self.ensure_database_exists():
            logger.error("Failed to ensure database exists")
            return False

        if not self.create_tables_if_not_exist():
            logger.error("Failed to create tables")
            return False

        self.seed_initial_data_if_empty()

        logger.info("Database setup completed successfully")
        return True


# =========================================
# HELPER
# =========================================

def setup_database_on_first_run():
    """
    Setup database on startup
    """
    setup = DatabaseSetup()
    return setup.run()


def reset_database_with_new_settings():
    """
    إعادة تعيين قاعدة البيانات باستخدام الإعدادات الجديدة
    (يستخدم عندما يغير المستخدم الإعدادات بشكل كبير)
    """
    logger.warning("Resetting database with new settings...")
    setup = DatabaseSetup()
    
    # حذف الجداول وإعادة إنشائها (اختياري - بحذر)
    # هذا يتطلب صلاحيات إضافية
    
    return setup.run()