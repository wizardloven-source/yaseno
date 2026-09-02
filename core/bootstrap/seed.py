# core/bootstrap/seed.py
"""
إدخال البيانات الافتراضية - مستخرجة من bootstrap.py
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SeedData:
    """
    إدخال البيانات الافتراضية للنظام
    
    الميزات:
        1. إدخال الصلاحيات (Permissions)
        2. إدخال الأدوار (Roles)
        3. إدخال مستخدم Admin
        4. إدخال الحسابات المحاسبية الافتراضية
        5. إدخال السنة المالية
        6. إدخال قواعد الضرائب
        7. إدخال العملات
    """
    
    def __init__(self):
        self._seeded = False
    
    def seed_all(self, uow) -> None:
        """إدخال جميع البيانات الافتراضية"""
        if self._seeded:
            logger.info("Data already seeded, skipping")
            return
        
        logger.info("🌱 Starting data seeding...")
        
        self._seed_permissions(uow)
        self._seed_roles(uow)
        self._seed_admin_user(uow)
        self._seed_accounts(uow)
        self._seed_fiscal_year(uow)
        self._seed_tax_rules(uow)
        self._seed_currencies(uow)
        
        self._seeded = True
        logger.info("✅ Data seeding completed")
    
    # =========================================================================
    # الصلاحيات (Permissions)
    # =========================================================================
    
    def _seed_permissions(self, uow) -> None:
        """إدخال الصلاحيات"""
        from core.domain.auth.entities import Permission
        from core.domain.auth.value_objects import PermissionId
        
        permission_repo = uow.permissions
        
        default_permissions = [
            # Accounting
            ("accounting.view_entry", "عرض القيد المحاسبي", "accounting"),
            ("accounting.create_entry", "إنشاء قيد محاسبي", "accounting"),
            ("accounting.post_entry", "ترحيل قيد محاسبي", "accounting"),
            ("accounting.reverse_entry", "عكس قيد محاسبي", "accounting"),
            ("accounting.view_trial_balance", "عرض ميزان المراجعة", "accounting"),
            ("accounting.view_account_balance", "عرض رصيد الحساب", "accounting"),
            ("accounting.close_period", "إغلاق الفترة المالية", "accounting"),
            ("accounting.open_period", "فتح الفترة المالية", "accounting"),
            ("accounting.view_audit_log", "عرض سجل التدقيق", "accounting"),
            
            # Invoicing
            ("invoicing.view_invoice", "عرض الفاتورة", "invoicing"),
            ("invoicing.create_invoice", "إنشاء فاتورة", "invoicing"),
            ("invoicing.post_invoice", "ترحيل فاتورة", "invoicing"),
            ("invoicing.cancel_invoice", "إلغاء فاتورة", "invoicing"),
            
            # Products
            ("products.view_product", "عرض المنتج", "products"),
            ("products.create_product", "إنشاء منتج", "products"),
            ("products.update_product", "تحديث منتج", "products"),
            ("products.delete_product", "حذف منتج", "products"),
            ("products.update_stock", "تحديث المخزون", "products"),
            
            # Customers
            ("customers.view_customer", "عرض العميل", "customers"),
            ("customers.create_customer", "إنشاء عميل", "customers"),
            ("customers.update_customer", "تحديث عميل", "customers"),
            ("customers.delete_customer", "حذف عميل", "customers"),
            
            # Suppliers
            ("suppliers.view_supplier", "عرض المورد", "suppliers"),
            ("suppliers.create_supplier", "إنشاء مورد", "suppliers"),
            ("suppliers.update_supplier", "تحديث مورد", "suppliers"),
            ("suppliers.delete_supplier", "حذف مورد", "suppliers"),
            
            # Funds
            ("funds.view_fund", "عرض الصندوق", "funds"),
            ("funds.create_fund", "إنشاء صندوق", "funds"),
            ("funds.update_fund", "تحديث صندوق", "funds"),
            ("funds.delete_fund", "حذف صندوق", "funds"),
            ("funds.deposit", "إيداع في الصندوق", "funds"),
            ("funds.withdraw", "سحب من الصندوق", "funds"),
            ("funds.transfer", "تحويل بين الصناديق", "funds"),
            
            # Settings
            ("settings.view_settings", "عرض الإعدادات", "settings"),
            ("settings.update_settings", "تحديث الإعدادات", "settings"),
            ("settings.manage_users", "إدارة المستخدمين", "settings"),
            ("settings.manage_roles", "إدارة الأدوار", "settings"),
            
            # Financial Statements
            ("financial_statements.view_income_statement", "عرض قائمة الدخل", "financial"),
            ("financial_statements.view_balance_sheet", "عرض الميزانية العمومية", "financial"),
            ("financial_statements.view_cash_flow", "عرض قائمة التدفقات النقدية", "financial"),
            ("financial_statements.generate_reports", "توليد التقارير المالية", "financial"),
            
            # Purchasing
            ("purchasing.view_order", "عرض أمر الشراء", "purchasing"),
            ("purchasing.create_order", "إنشاء أمر شراء", "purchasing"),
            ("purchasing.post_order", "ترحيل أمر شراء", "purchasing"),
            ("purchasing.receive_order", "استلام أمر شراء", "purchasing"),
            
            # Payments
            ("payments.view_payment", "عرض الدفعة", "payments"),
            ("payments.create_payment", "إنشاء دفعة", "payments"),
            ("payments.complete_payment", "إكمال دفعة", "payments"),
            ("payments.approve_payment", "اعتماد دفعة", "payments"),
            
            # Reports
            ("reports.view_reports", "عرض التقارير", "reports"),
            ("reports.export_reports", "تصدير التقارير", "reports"),
        ]
        
        for code, name, category in default_permissions:
            existing = permission_repo.get_by_code(code)
            if not existing:
                permission = Permission(
                    id=PermissionId.generate(),
                    code=code,
                    name=name,
                    category=category,
                    is_active=True,
                    created_by="system"
                )
                permission_repo.save(permission)
        
        logger.info(f"   ✅ Seeded {len(default_permissions)} permissions")
    
    # =========================================================================
    # الأدوار (Roles)
    # =========================================================================
    
    def _seed_roles(self, uow) -> None:
        """إدخال الأدوار"""
        from core.domain.auth.entities import Role
        from core.domain.auth.value_objects import RoleId
        
        role_repo = uow.roles
        permission_repo = uow.permissions
        
        # 1. Admin Role
        admin_role = role_repo.get_by_name("admin")
        if not admin_role:
            admin_role = Role(
                id=RoleId.generate(),
                name="admin",
                display_name="مدير النظام",
                description="صلاحيات كاملة على النظام",
                is_admin=True,
                is_active=True,
                created_by="system"
            )
            all_permissions = permission_repo.list_all()
            for perm in all_permissions:
                admin_role.permissions.append(perm)
            role_repo.save(admin_role)
            logger.info("   ✅ Admin role created")
        
        # 2. Accountant Role
        accountant_role = role_repo.get_by_name("accountant")
        if not accountant_role:
            accountant_role = Role(
                id=RoleId.generate(),
                name="accountant",
                display_name="محاسب",
                description="صلاحيات المحاسبة",
                is_admin=False,
                is_active=True,
                created_by="system"
            )
            perm_codes = [
                "accounting.view_entry", "accounting.create_entry", "accounting.post_entry",
                "accounting.view_trial_balance", "accounting.view_account_balance",
                "invoicing.view_invoice", "invoicing.create_invoice", "invoicing.post_invoice",
                "products.view_product", "customers.view_customer", "suppliers.view_supplier",
                "funds.view_fund", "funds.deposit", "funds.withdraw",
                "financial_statements.view_income_statement",
                "financial_statements.view_balance_sheet",
                "financial_statements.view_cash_flow",
                "purchasing.view_order", "purchasing.create_order", "purchasing.post_order",
                "payments.view_payment", "payments.create_payment",
            ]
            for code in perm_codes:
                perm = permission_repo.get_by_code(code)
                if perm:
                    accountant_role.permissions.append(perm)
            role_repo.save(accountant_role)
            logger.info("   ✅ Accountant role created")
        
        # 3. Auditor Role
        auditor_role = role_repo.get_by_name("auditor")
        if not auditor_role:
            auditor_role = Role(
                id=RoleId.generate(),
                name="auditor",
                display_name="مدقق",
                description="صلاحيات القراءة فقط",
                is_admin=False,
                is_active=True,
                created_by="system"
            )
            perm_codes = [
                "accounting.view_entry", "accounting.view_trial_balance",
                "accounting.view_account_balance", "accounting.view_audit_log",
                "invoicing.view_invoice", "products.view_product",
                "customers.view_customer", "suppliers.view_supplier",
                "funds.view_fund", "settings.view_settings",
                "financial_statements.view_income_statement",
                "financial_statements.view_balance_sheet",
                "financial_statements.view_cash_flow",
                "reports.view_reports",
            ]
            for code in perm_codes:
                perm = permission_repo.get_by_code(code)
                if perm:
                    auditor_role.permissions.append(perm)
            role_repo.save(auditor_role)
            logger.info("   ✅ Auditor role created")
        
        # 4. Financial Analyst Role
        analyst_role = role_repo.get_by_name("financial_analyst")
        if not analyst_role:
            analyst_role = Role(
                id=RoleId.generate(),
                name="financial_analyst",
                display_name="محلل مالي",
                description="صلاحيات التقارير المالية",
                is_admin=False,
                is_active=True,
                created_by="system"
            )
            perm_codes = [
                "accounting.view_entry", "accounting.view_trial_balance",
                "accounting.view_account_balance",
                "financial_statements.view_income_statement",
                "financial_statements.view_balance_sheet",
                "financial_statements.view_cash_flow",
                "financial_statements.generate_reports",
                "reports.view_reports", "reports.export_reports",
                "products.view_product", "customers.view_customer",
                "suppliers.view_supplier", "funds.view_fund",
            ]
            for code in perm_codes:
                perm = permission_repo.get_by_code(code)
                if perm:
                    analyst_role.permissions.append(perm)
            role_repo.save(analyst_role)
            logger.info("   ✅ Financial Analyst role created")
    
    # =========================================================================
    # مستخدم Admin
    # =========================================================================
    
    def _seed_admin_user(self, uow) -> None:
        """إدخال مستخدم Admin"""
        from core.domain.auth.entities import User
        from core.domain.auth.value_objects import UserId
        from core.application.security.password_hasher import PasswordHasher
        
        user_repo = uow.users
        role_repo = uow.roles
        
        existing = user_repo.get_by_username("admin")
        if existing:
            logger.info("   ℹ️ Admin user already exists")
            return
        
        admin_role = role_repo.get_by_name("admin")
        if not admin_role:
            logger.warning("   ⚠️ Admin role not found, skipping admin user")
            return
        
        import os
        admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@123')
        
        user = User(
            id=UserId.generate(),
            username="admin",
            email="admin@yaseen-erp.com",
            full_name="مدير النظام",
            password_hash=PasswordHasher.hash(admin_password),
            is_active=True,
            is_super_admin=True,
            created_by="system"
        )
        user.roles.append(admin_role)
        user_repo.save(user)
        logger.info(f"   ✅ Admin user created (username: admin)")
    
    # =========================================================================
    # الحسابات المحاسبية
    # =========================================================================
    
    def _seed_accounts(self, uow) -> None:
        """إدخال الحسابات المحاسبية الافتراضية"""
        from core.domain.accounting.interfaces import Account
        from core.domain.shared.value_objects import AccountCode
        
        account_repo = uow.accounts
        
        default_accounts = [
            ("1010", "الصندوق", "asset", "USD", "حساب الصندوق النقدي الرئيسي"),
            ("1011", "الصندوق الفرعي", "asset", "USD", "حساب الصندوق الفرعي"),
            ("1020", "المدينون", "asset", "USD", "حساب العملاء والمدينون"),
            ("1030", "المخزون", "asset", "USD", "حساب المخزون"),
            ("1040", "البنك", "asset", "USD", "الحساب البنكي"),
            ("1050", "الأصول الثابتة", "asset", "USD", "الأصول الثابتة"),
            ("1060", "الإهلاك المتراكم", "asset", "USD", "الإهلاك المتراكم للأصول"),
            ("2010", "الدائنون", "liability", "USD", "حساب الموردين والدائنون"),
            ("2020", "الضرائب المستحقة", "liability", "USD", "الضرائب المستحقة الدفع"),
            ("2030", "رواتب مستحقة", "liability", "USD", "الرواتب المستحقة الدفع"),
            ("3010", "رأس المال", "equity", "USD", "رأس المال المدفوع"),
            ("3020", "الأرباح المحتجزة", "equity", "USD", "الأرباح المحتجزة"),
            ("3990", "ملخص الدخل", "equity", "USD", "حساب ملخص الدخل للإقفال"),
            ("4010", "إيرادات المبيعات", "revenue", "USD", "إيرادات المبيعات"),
            ("4020", "إيرادات أخرى", "revenue", "USD", "إيرادات أخرى"),
            ("5010", "تكلفة البضاعة المباعة", "expense", "USD", "تكلفة البضاعة المباعة"),
            ("5020", "مصروفات الرواتب", "expense", "USD", "مصروفات الرواتب والأجور"),
            ("5030", "مصروفات الإيجار", "expense", "USD", "مصروفات الإيجار"),
            ("5040", "مصروفات الكهرباء", "expense", "USD", "مصروفات الكهرباء والمياه"),
            ("5050", "مصروفات التسويق", "expense", "USD", "مصروفات التسويق والإعلان"),
            ("5060", "مصروفات إدارية", "expense", "USD", "مصروفات إدارية وعمومية"),
            ("5070", "الإهلاك", "expense", "USD", "مصروفات الإهلاك"),
            ("5100", "مصروفات متنوعة", "expense", "USD", "مصروفات متنوعة"),
            ("2100", "ضريبة القيمة المضافة", "liability", "USD", "ضريبة القيمة المضافة المستحقة"),
        ]
        
        for code, name, acc_type, currency, desc in default_accounts:
            existing = account_repo.get_by_code(AccountCode(code))
            if not existing:
                account = Account(
                    code=AccountCode(code),
                    name=name,
                    account_type=acc_type,
                    currency=currency,
                    description=desc,
                    is_active=True
                )
                account_repo.save(account)
        
        logger.info(f"   ✅ Seeded {len(default_accounts)} accounts")
    
    # =========================================================================
    # ✅ السنة المالية - الإصدار المُصلح بالكامل
    # =========================================================================
    
    def _seed_fiscal_year(self, uow) -> None:
        """
        إدخال السنة المالية مع فتراتها
        
        ✅ تم الإصلاح: تعيين اسم لكل فترة مالية لحل مشكلة NOT NULL
        """
        from core.domain.fiscal.entities import FiscalYear
        from core.domain.fiscal.value_objects import FiscalPeriodType
        from core.domain.shared.clock import get_clock
        
        fiscal_repo = uow.fiscal_years
        
        # التحقق من وجود سنة مالية بالفعل
        existing = fiscal_repo.get_current()
        if existing:
            logger.info(f"   ℹ️ Fiscal year already exists: {existing.code}")
            return
        
        clock = get_clock()
        current_year = clock.today().year
        
        # إنشاء السنة المالية
        fiscal_year = FiscalYear.create(
            code=f"FY{current_year}",
            name=f"السنة المالية {current_year}",
            start_date=date(current_year, 1, 1),
            end_date=date(current_year, 12, 31),
            periods_per_year=12,
            period_type=FiscalPeriodType.MONTH,
            created_by="system"
        )
        
        # ✅ ✅ ✅ الإصلاح الأساسي: تعيين اسم لكل فترة مالية
        # هذا يحل مشكلة NOT NULL في عمود name بجدول fiscal_periods
        months_ar = [
            "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
        ]
        
        for i, period in enumerate(fiscal_year.periods):
            month_name = months_ar[i] if i < len(months_ar) else f"شهر {i+1}"
            period_name = f"{month_name} {current_year}"
            
            # تعيين name للفترة بطرق متعددة لضمان النجاح
            if hasattr(period, 'name'):
                period.name = period_name
            elif hasattr(period, '__dict__'):
                period.__dict__['name'] = period_name
            else:
                try:
                    setattr(period, 'name', period_name)
                except AttributeError:
                    logger.warning(f"   ⚠️ Could not set name for period {i+1}")
        
        # فتح السنة المالية
        fiscal_year.open("system")
        
        # حفظ السنة المالية (سيتم حفظ الفترات تلقائياً)
        fiscal_repo.save(fiscal_year)
        
        logger.info(f"   ✅ Fiscal year created: {fiscal_year.code} with {len(fiscal_year.periods)} periods")
    
    # =========================================================================
    # قواعد الضرائب
    # =========================================================================
    
    def _seed_tax_rules(self, uow) -> None:
        """إدخال قواعد الضرائب"""
        from core.domain.tax.entities import TaxRule
        from core.domain.tax.value_objects import TaxType, TaxCalculationType, TaxJurisdiction
        
        tax_repo = uow.taxes
        
        existing = tax_repo.get_all()
        if existing:
            logger.info("   ℹ️ Tax rules already exist")
            return
        
        default_rules = [
            {
                "code": "VAT-15",
                "name": "ضريبة القيمة المضافة 15%",
                "tax_type": TaxType.VAT,
                "calculation_type": TaxCalculationType.EXCLUSIVE,
                "rate": 15.0,
                "jurisdiction": TaxJurisdiction.FEDERAL,
                "description": "ضريبة القيمة المضافة بنسبة 15%",
                "is_default": True,
            },
            {
                "code": "VAT-0",
                "name": "ضريبة القيمة المضافة 0%",
                "tax_type": TaxType.VAT,
                "calculation_type": TaxCalculationType.ZERO_RATED,
                "rate": 0.0,
                "jurisdiction": TaxJurisdiction.FEDERAL,
                "description": "معفى من ضريبة القيمة المضافة",
                "is_default": False,
            },
            {
                "code": "SALES-8",
                "name": "ضريبة المبيعات 8%",
                "tax_type": TaxType.SALES_TAX,
                "calculation_type": TaxCalculationType.EXCLUSIVE,
                "rate": 8.0,
                "jurisdiction": TaxJurisdiction.STATE,
                "description": "ضريبة المبيعات بنسبة 8%",
                "is_default": False,
            },
        ]
        
        for data in default_rules:
            rule = TaxRule.create(
                code=data["code"],
                name=data["name"],
                rate=Decimal(str(data["rate"])),
                tax_type=data["tax_type"],
                calculation_type=data["calculation_type"],
                jurisdiction=data["jurisdiction"],
                description=data["description"],
                is_default=data["is_default"],
                created_by="system"
            )
            tax_repo.save(rule)
        
        logger.info(f"   ✅ Seeded {len(default_rules)} tax rules")
    
    # =========================================================================
    # العملات
    # =========================================================================
    
    def _seed_currencies(self, uow) -> None:
        """إدخال العملات"""
        from core.domain.currency.entities import Currency
        from core.domain.currency.value_objects import CurrencyCode
        
        currency_repo = uow.currencies
        
        default_currencies = [
            {"code": "USD", "name": "دولار أمريكي", "symbol": "$", "is_base": True},
            {"code": "EUR", "name": "يورو", "symbol": "€", "is_base": False},
            {"code": "LBP", "name": "ليرة لبنانية", "symbol": "ل.ل", "is_base": False},
            {"code": "GBP", "name": "جنيه إسترليني", "symbol": "£", "is_base": False},
        ]
        
        for data in default_currencies:
            existing = currency_repo.get_by_code(CurrencyCode(data["code"]))
            if not existing:
                currency = Currency.create(
                    code=data["code"],
                    name=data["name"],
                    symbol=data["symbol"],
                    is_base=data["is_base"],
                    created_by="system"
                )
                currency_repo.save(currency)
        
        logger.info(f"   ✅ Seeded {len(default_currencies)} currencies")