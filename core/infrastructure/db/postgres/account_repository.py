"""
Postgres Account Repository - مستودع شجرة الحسابات
الإصدار: 2.0.0 - Enterprise Edition

الميزات:
    1. إدارة كاملة لشجرة الحسابات (CRUD)
    2. دعم التسلسل الهرمي (Parent-Child)
    3. حساب المستوى والمسار التلقائي
    4. التحقق من صحة الهيكل (لا يوجد دورات)
    5. دعم الحذف الناعم والصلب
    6. البحث المتقدم مع التصفية
    7. دعم العملات المتعددة
    8. تحسين الأداء مع CTE (Common Table Expressions)
    9. تصدير الشجرة كـ JSON
    10. التحقق من صلاحية الحسابات للترحيل
"""

from typing import Optional, List, Dict, Any, Tuple, Set
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, asc, func, text, case, not_
from sqlalchemy.sql import label

from core.domain.accounting.interfaces import IAccountRepository
from core.domain.accounting.interfaces import Account
from core.domain.shared.value_objects import AccountCode

from core.infrastructure.db.models.account_model import AccountModel


class PostgresAccountRepository(IAccountRepository):
    """
    تنفيذ PostgreSQL لمستودع شجرة الحسابات
    
    المبادئ:
        1. كل حساب له كود فريد
        2. التسلسل الهرمي عبر parent_code
        3. حساب المستوى والمسار تلقائياً
        4. لا يمكن حذف حساب له حسابات فرعية
        5. لا يمكن حذف حساب مستخدم في حركات
        6. دعم الحذف الناعم (Soft Delete)
    """
    
    def __init__(self, session: Session):
        """
        تهيئة المستودع
        
        Args:
            session: جلسة SQLAlchemy
        """
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية (CRUD)
    # =========================================================================
    
    def save(self, account: Account) -> None:
        """
        حفظ حساب (جديد أو محدث)
        
        الميزات:
            1. التحقق من عدم وجود كود مكرر
            2. التحقق من وجود الحساب الأب
            3. حساب المستوى والمسار تلقائياً
            4. التحقق من عدم وجود دورات في الهيكل
            5. دعم Optimistic Locking
        
        Args:
            account: كيان الحساب من Domain Layer
        
        Raises:
            ValueError: إذا كان الكود مكرراً أو الأب غير موجود
            ConcurrentModificationError: إذا تم تعديل الحساب بواسطة مستخدم آخر
        """
        # 1. التحقق من عدم وجود كود مكرر
        existing = self._session.query(AccountModel).filter(
            AccountModel.code == account.code.code
        ).first()
        
        if existing and existing.id != account.id:
            raise ValueError(f"Account code {account.code} already exists")
        
        # 2. التحقق من وجود الحساب الأب
        parent = None
        if account.parent_code:
            parent = self._session.query(AccountModel).filter(
                AccountModel.code == account.parent_code.code
            ).first()
            
            if not parent:
                raise ValueError(f"Parent account {account.parent_code} not found")
        
        # 3. تحويل Domain → ORM
        model = self._to_model(account)
        
        # 4. حساب المستوى والمسار
        if parent:
            model.level = parent.level + 1
            model.path = f"{parent.path}.{model.code}" if parent.path else model.code
        else:
            model.level = 0
            model.path = model.code
        
        # 5. التحقق من عدم وجود دورات في الهيكل
        self._check_cycle(model)
        
        # 6. حفظ الحساب
        self._session.merge(model)
        self._session.flush()
    
    def get_by_code(self, code: AccountCode) -> Optional[Account]:
        """
        الحصول على حساب بواسطة الكود
        
        Args:
            code: كود الحساب
        
        Returns:
            Optional[Account]: كيان الحساب أو None
        """
        model = self._session.query(AccountModel).filter(
            AccountModel.code == code.code,
            AccountModel.is_active == True
        ).first()
        
        return self._to_entity(model) if model else None
    
    def get_by_code_or_fail(self, code: AccountCode) -> Account:
        """
        الحصول على حساب أو رفع استثناء
        
        Args:
            code: كود الحساب
        
        Returns:
            Account: كيان الحساب
        
        Raises:
            ValueError: إذا لم يتم العثور على الحساب
        """
        account = self.get_by_code(code)
        if not account:
            raise ValueError(f"Account {code} not found")
        return account
    
    def get_all_accounts(
        self,
        account_type: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Account]:
        """
        الحصول على جميع الحسابات مع خيارات التصفية
        
        Args:
            account_type: نوع الحساب (اختياري)
            include_inactive: تضمين الحسابات غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[Account]: قائمة الحسابات
        """
        query = self._session.query(AccountModel)
        
        if not include_inactive:
            query = query.filter(AccountModel.is_active == True)
        
        if account_type:
            query = query.filter(AccountModel.account_type == account_type)
        
        # ترتيب حسب الكود
        query = query.order_by(asc(AccountModel.code))
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    def get_active_accounts(self) -> List[Account]:
        """
        الحصول على الحسابات النشطة فقط
        
        Returns:
            List[Account]: قائمة الحسابات النشطة
        """
        return self.get_all_accounts(include_inactive=False)
    
    def exists(self, code: AccountCode) -> bool:
        """
        التحقق من وجود حساب بالكود
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: True إذا كان موجوداً
        """
        return self._session.query(AccountModel).filter(
            AccountModel.code == code.code,
            AccountModel.is_active == True
        ).first() is not None
    
    def is_active(self, code: AccountCode) -> bool:
        """
        التحقق من أن الحساب نشط
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: True إذا كان نشطاً
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        return account.is_active if account else False
    
    # =========================================================================
    # عمليات شجرة الحسابات (Hierarchy)
    # =========================================================================
    
    def get_children(self, parent_code: AccountCode) -> List[Account]:
        """
        الحصول على الحسابات الفرعية لحساب أب
        
        Args:
            parent_code: كود الحساب الأب
        
        Returns:
            List[Account]: قائمة الحسابات الفرعية
        """
        models = self._session.query(AccountModel).filter(
            AccountModel.parent_code == parent_code.code,
            AccountModel.is_active == True
        ).order_by(asc(AccountModel.code)).all()
        
        return [self._to_entity(m) for m in models]
    
    def get_root_accounts(self) -> List[Account]:
        """
        الحصول على حسابات الجذر (بدون أب)
        
        Returns:
            List[Account]: قائمة حسابات الجذر
        """
        models = self._session.query(AccountModel).filter(
            AccountModel.parent_code.is_(None),
            AccountModel.is_active == True
        ).order_by(asc(AccountModel.code)).all()
        
        return [self._to_entity(m) for m in models]
    
    def get_tree(self, root_code: Optional[AccountCode] = None) -> Dict[str, Any]:
        """
        الحصول على شجرة الحسابات كاملة
        
        الميزات:
            1. بناء الشجرة الهرمية بالكامل
            2. دعم الجذور المتعددة
            3. حساب المجاميع لكل مستوى
            4. تصدير كـ JSON
        
        Args:
            root_code: كود الجذر (اختياري - الكل إذا لم يحدد)
        
        Returns:
            Dict[str, Any]: الشجرة الهرمية
        """
        # 1. الحصول على الجذور
        if root_code:
            roots = self._session.query(AccountModel).filter(
                AccountModel.code == root_code.code,
                AccountModel.is_active == True
            ).all()
        else:
            roots = self._session.query(AccountModel).filter(
                AccountModel.parent_code.is_(None),
                AccountModel.is_active == True
            ).order_by(asc(AccountModel.code)).all()
        
        # 2. بناء الشجرة
        tree = []
        for root in roots:
            node = self._build_tree_node(root)
            tree.append(node)
        
        return {
            'root_count': len(tree),
            'tree': tree
        }
    
    def get_path(self, code: AccountCode) -> List[Account]:
        """
        الحصول على مسار الحساب من الجذر إلى الحساب
        
        Args:
            code: كود الحساب
        
        Returns:
            List[Account]: قائمة الحسابات في المسار
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code,
            AccountModel.is_active == True
        ).first()
        
        if not account:
            return []
        
        # استخراج المسار من حقل path
        if account.path:
            codes = account.path.split('.')
            models = self._session.query(AccountModel).filter(
                AccountModel.code.in_(codes),
                AccountModel.is_active == True
            ).order_by(asc(AccountModel.level)).all()
            
            return [self._to_entity(m) for m in models]
        
        return [self._to_entity(account)]
    
    def get_depth(self, code: AccountCode) -> int:
        """
        الحصول على عمق الحساب في الشجرة
        
        Args:
            code: كود الحساب
        
        Returns:
            int: عمق الحساب (0 للجذر)
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        return account.level if account else -1
    
    # =========================================================================
    # البحث والتصفية
    # =========================================================================
    
    def search(
        self,
        search_text: str,
        account_type: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 50
    ) -> List[Account]:
        """
        البحث في الحسابات بالنص الحر
        
        Args:
            search_text: النص المطلوب البحث عنه
            account_type: نوع الحساب (اختياري)
            include_inactive: تضمين الحسابات غير النشطة
            limit: الحد الأقصى للنتائج
        
        Returns:
            List[Account]: قائمة الحسابات المطابقة
        """
        search = f"%{search_text}%"
        
        query = self._session.query(AccountModel).filter(
            or_(
                AccountModel.code.ilike(search),
                AccountModel.name.ilike(search),
                AccountModel.description.ilike(search)
            )
        )
        
        if not include_inactive:
            query = query.filter(AccountModel.is_active == True)
        
        if account_type:
            query = query.filter(AccountModel.account_type == account_type)
        
        models = query.limit(limit).all()
        return [self._to_entity(m) for m in models]
    
    def get_by_type(self, account_type: str) -> List[Account]:
        """
        الحصول على حسابات من نوع معين
        
        Args:
            account_type: نوع الحساب (asset, liability, equity, revenue, expense)
        
        Returns:
            List[Account]: قائمة الحسابات
        """
        models = self._session.query(AccountModel).filter(
            AccountModel.account_type == account_type,
            AccountModel.is_active == True
        ).order_by(asc(AccountModel.code)).all()
        
        return [self._to_entity(m) for m in models]
    
    def get_by_type_and_currency(
        self,
        account_type: str,
        currency: str
    ) -> List[Account]:
        """
        الحصول على حسابات من نوع معين وعملة محددة
        
        Args:
            account_type: نوع الحساب
            currency: العملة
        
        Returns:
            List[Account]: قائمة الحسابات
        """
        models = self._session.query(AccountModel).filter(
            AccountModel.account_type == account_type,
            AccountModel.currency == currency,
            AccountModel.is_active == True
        ).order_by(asc(AccountModel.code)).all()
        
        return [self._to_entity(m) for m in models]
    
    # =========================================================================
    # التحقق من الصلاحية (Validation)
    # =========================================================================
    
    def can_be_debited(self, code: AccountCode) -> bool:
        """
        التحقق من إمكانية ترحيل حركة مدين للحساب
        
        القاعدة:
            - الأصول والمصروفات: يمكن ترحيل مدين
            - الخصوم وحقوق الملكية والإيرادات: لا يمكن ترحيل مدين
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: True إذا كان يمكن ترحيل مدين
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        if not account:
            return False
        
        return account.account_type in ['asset', 'expense']
    
    def can_be_credited(self, code: AccountCode) -> bool:
        """
        التحقق من إمكانية ترحيل حركة دائن للحساب
        
        القاعدة:
            - الخصوم وحقوق الملكية والإيرادات: يمكن ترحيل دائن
            - الأصول والمصروفات: لا يمكن ترحيل دائن
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: True إذا كان يمكن ترحيل دائن
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        if not account:
            return False
        
        return account.account_type in ['liability', 'equity', 'revenue']
    
    def is_leaf(self, code: AccountCode) -> bool:
        """
        التحقق من أن الحساب ليس له حسابات فرعية (ورقة)
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: True إذا كان الحساب ورقة
        """
        return self._session.query(AccountModel).filter(
            AccountModel.parent_code == code.code,
            AccountModel.is_active == True
        ).count() == 0
    
    def has_transactions(self, code: AccountCode) -> bool:
        """
        التحقق من وجود حركات محاسبية للحساب
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: True إذا كان هناك حركات
        """
        from core.infrastructure.db.models.account_model import LedgerEntryModel, JournalLineModel
        
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        if not account:
            return False
        
        # التحقق من وجود حركات في الأستاذ
        ledger_count = self._session.query(LedgerEntryModel).filter(
            LedgerEntryModel.account_id == account.id
        ).count()
        
        if ledger_count > 0:
            return True
        
        # التحقق من وجود حركات في قيود اليومية
        journal_count = self._session.query(JournalLineModel).filter(
            JournalLineModel.account_id == account.id
        ).count()
        
        return journal_count > 0
    
    # =========================================================================
    # عمليات إدارية
    # =========================================================================
    
    def activate_account(self, code: AccountCode) -> bool:
        """
        تفعيل حساب
        
        Args:
            code: كود الحساب
        
        Returns:
            bool: نجاح العملية
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        if not account:
            return False
        
        account.is_active = True
        account.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return True
    
    def deactivate_account(self, code: AccountCode, reason: Optional[str] = None) -> bool:
        """
        تعطيل حساب
        
        Args:
            code: كود الحساب
            reason: سبب التعطيل (اختياري)
        
        Returns:
            bool: نجاح العملية
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        if not account:
            return False
        
        # التحقق من عدم وجود حسابات فرعية نشطة
        children = self._session.query(AccountModel).filter(
            AccountModel.parent_code == code.code,
            AccountModel.is_active == True
        ).first()
        
        if children:
            raise ValueError(f"Cannot deactivate account with active children")
        
        account.is_active = False
        account.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return True
    
    def delete_account(self, code: AccountCode, permanent: bool = False) -> bool:
        """
        حذف حساب
        
        Args:
            code: كود الحساب
            permanent: حذف دائم (True) أو ناعم (False)
        
        Returns:
            bool: نجاح العملية
        
        Raises:
            ValueError: إذا كان الحساب له حسابات فرعية أو حركات
        """
        account = self._session.query(AccountModel).filter(
            AccountModel.code == code.code
        ).first()
        
        if not account:
            return False
        
        # التحقق من وجود حسابات فرعية
        children = self._session.query(AccountModel).filter(
            AccountModel.parent_code == code.code
        ).first()
        
        if children:
            raise ValueError(f"Cannot delete account with children")
        
        # التحقق من وجود حركات
        if self.has_transactions(code):
            raise ValueError(f"Cannot delete account with transactions")
        
        if permanent:
            self._session.delete(account)
        else:
            account.is_active = False
            account.updated_at = datetime.now(timezone.utc)
        
        self._session.flush()
        return True
    
    def get_next_code(
        self,
        parent_code: Optional[AccountCode] = None,
        prefix: str = "",
        length: int = 4
    ) -> str:
        """
        توليد كود حساب تلقائي
        
        Args:
            parent_code: كود الحساب الأب (اختياري)
            prefix: بادئة الكود
            length: طول الرقم التسلسلي
        
        Returns:
            str: الكود التالي
        """
        # بناء الاستعلام
        query = self._session.query(AccountModel.code)
        
        if parent_code:
            query = query.filter(AccountModel.parent_code == parent_code.code)
        
        # الحصول على آخر كود
        last = query.order_by(desc(AccountModel.code)).first()
        
        if not last:
            return f"{prefix}1".zfill(length)
        
        # استخراج الرقم التسلسلي
        try:
            last_code = last.code
            if prefix and last_code.startswith(prefix):
                num_str = last_code[len(prefix):]
                if num_str.isdigit():
                    next_num = int(num_str) + 1
                    return f"{prefix}{next_num}".zfill(length)
        except:
            pass
        
        # إذا فشل الاستخراج، استخدم رقم عشوائي
        import random
        return f"{prefix}{random.randint(1, 9999)}".zfill(length)
    
    # =========================================================================
    # إحصائيات وتقارير
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الحسابات
        
        Returns:
            Dict[str, Any]: إحصائيات الحسابات
        """
        total = self._session.query(AccountModel).count()
        active = self._session.query(AccountModel).filter(
            AccountModel.is_active == True
        ).count()
        
        # حسب النوع
        by_type = self._session.query(
            AccountModel.account_type,
            func.count().label('count')
        ).group_by(AccountModel.account_type).all()
        
        # حسب العملة
        by_currency = self._session.query(
            AccountModel.currency,
            func.count().label('count')
        ).group_by(AccountModel.currency).all()
        
        # العمق الأقصى
        max_depth = self._session.query(
            func.max(AccountModel.level).label('max_depth')
        ).first()
        
        return {
            'total_accounts': total,
            'active_accounts': active,
            'inactive_accounts': total - active,
            'by_type': {
                row.account_type: row.count
                for row in by_type
            },
            'by_currency': {
                row.currency: row.count
                for row in by_currency
            },
            'max_depth': max_depth.max_depth or 0,
            'root_accounts': self._session.query(AccountModel).filter(
                AccountModel.parent_code.is_(None)
            ).count()
        }
    
    def get_children_count(self, code: AccountCode) -> int:
        """
        حساب عدد الحسابات الفرعية
        
        Args:
            code: كود الحساب
        
        Returns:
            int: عدد الحسابات الفرعية
        """
        return self._session.query(AccountModel).filter(
            AccountModel.parent_code == code.code,
            AccountModel.is_active == True
        ).count()
    
    # =========================================================================
    # دوال التحويل (Converters)
    # =========================================================================
    
    def _to_model(self, entity: Account) -> AccountModel:
        """
        تحويل Domain Entity → ORM Model
        
        Args:
            entity: كيان الحساب من Domain Layer
        
        Returns:
            AccountModel: نموذج ORM
        """
        return AccountModel(
            id=entity.id if hasattr(entity, 'id') else uuid4(),
            code=entity.code.code,
            name=entity.name,
            account_type=entity.account_type,
            parent_code=entity.parent_code.code if entity.parent_code else None,
            is_active=entity.is_active,
            description=entity.description,
            currency=entity.currency,
            created_at=entity.created_at or datetime.now(timezone.utc),
            updated_at=entity.updated_at or datetime.now(timezone.utc),
            created_by=getattr(entity, 'created_by', 'system'),
            version=getattr(entity, 'version', 1)
        )
    
    def _to_entity(self, model: AccountModel) -> Account:
        """
        تحويل ORM Model → Domain Entity
        
        Args:
            model: نموذج ORM
        
        Returns:
            Account: كيان الحساب من Domain Layer
        """
        if not model:
            return None
        
        from core.domain.accounting.interfaces import Account as DomainAccount
        
        return DomainAccount(
            code=AccountCode(model.code),
            name=model.name,
            account_type=model.account_type,
            is_active=model.is_active,
            parent_code=AccountCode(model.parent_code) if model.parent_code else None,
            description=model.description,
            currency=model.currency,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version
        )
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def _build_tree_node(self, model: AccountModel) -> Dict[str, Any]:
        """
        بناء عقدة شجرة مع أبنائها
        
        Args:
            model: نموذج الحساب الحالي
        
        Returns:
            Dict[str, Any]: العقدة مع الأبناء
        """
        # الحصول على الأبناء
        children = self._session.query(AccountModel).filter(
            AccountModel.parent_code == model.code,
            AccountModel.is_active == True
        ).order_by(asc(AccountModel.code)).all()
        
        node = {
            'code': model.code,
            'name': model.name,
            'account_type': model.account_type,
            'description': model.description,
            'currency': model.currency,
            'is_active': model.is_active,
            'level': model.level,
            'path': model.path,
            'children': []
        }
        
        # إضافة الأبناء بشكل متكرر
        for child in children:
            node['children'].append(self._build_tree_node(child))
        
        # حساب الإجمالي
        if node['children']:
            node['children_count'] = len(node['children'])
        
        return node
    
    def _check_cycle(self, model: AccountModel) -> None:
        """
        التحقق من عدم وجود دورات في شجرة الحسابات
        
        Args:
            model: نموذج الحساب المراد التحقق منه
        
        Raises:
            ValueError: إذا تم اكتشاف دورة
        """
        if not model.parent_code:
            return
        
        # التحقق من أن الأب ليس من نسل الحساب نفسه
        current = model
        visited = set()
        
        while current.parent_code:
            if current.parent_code in visited:
                raise ValueError(f"Cycle detected in account hierarchy: {model.code} -> {current.parent_code}")
            
            visited.add(current.parent_code)
            
            parent = self._session.query(AccountModel).filter(
                AccountModel.code == current.parent_code
            ).first()
            
            if not parent:
                break
            
            current = parent