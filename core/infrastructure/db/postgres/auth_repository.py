"""
Authorization Repository - مستودع الصلاحيات والأدوار
✅ محدث: دعم تشفير كلمات المرور عبر PasswordHasher
✅ محدث: تحسين Optimistic Locking
✅ محدث: إضافة دالة update_password
✅ جديد: save_atomic لحفظ عدة مستخدمين دفعة واحدة
✅ جديد: lock_users_for_update (SELECT FOR UPDATE)
✅ جديد: bulk_update_roles
✅ جديد: soft_delete مع Optimistic Locking
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update, and_
from sqlalchemy.orm import Session, selectinload

from core.domain.auth.entities import User, Role, Permission
from core.domain.auth.value_objects import UserId, RoleId, PermissionId
from core.domain.auth.interfaces import IUserRepository, IRoleRepository, IPermissionRepository
from core.shared.exceptions import ConcurrentModificationError

# ✅ استيراد خدمة تشفير كلمات المرور
from core.application.security.password_hasher import PasswordHasher

from ..models.auth_models import UserModel, RoleModel, PermissionModel

import logging
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# ========== دوال التحويل ==========

def _user_model_to_domain(model: UserModel) -> User:
    """تحويل ORM User إلى Domain User"""
    return User(
        id=UserId(model.id),
        username=model.username,
        email=model.email,
        full_name=model.full_name,
        is_active=model.is_active,
        is_super_admin=model.is_super_admin,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        last_login=model.last_login,
        version=model.version
    )


def _role_model_to_domain(model: RoleModel) -> Role:
    """تحويل ORM Role إلى Domain Role"""
    return Role(
        id=RoleId(model.id),
        name=model.name,
        display_name=model.display_name,
        description=model.description,
        is_admin=model.is_admin,
        is_active=model.is_active,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )


def _permission_model_to_domain(model: PermissionModel) -> Permission:
    """تحويل ORM Permission إلى Domain Permission"""
    return Permission(
        id=PermissionId(model.id),
        code=model.code,
        name=model.name,
        description=model.description,
        category=model.category,
        is_active=model.is_active,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )


# ========== مستودع المستخدمين ==========

class PostgresUserRepository(IUserRepository):
    """تطبيق PostgreSQL لمستودع المستخدمين"""
    
    def __init__(self, session: Session):
        self._session = session

    # ========== العمليات الأساسية ==========
    
    def save(self, user: User) -> None:
        """حفظ المستخدم مع Optimistic Locking وتشفير كلمة المرور"""
        existing = self._session.execute(
            select(UserModel).where(UserModel.id == user.id.value)
        ).scalar_one_or_none()

        if existing:
            # ✅ تحديث مع التحقق من الإصدار
            now = utc_now()
            new_version = existing.version + 1
            
            # ✅ تشفير كلمة المرور إذا تم تغييرها ولم تكن مشفرة بالفعل
            password_hash = user.password_hash
            if password_hash and not PasswordHasher.is_valid_hash(password_hash):
                password_hash = PasswordHasher.hash(password_hash)
            
            result = self._session.execute(
                update(UserModel)
                .where(
                    UserModel.id == user.id.value,
                    UserModel.version == user.version  # ✅ Optimistic Locking
                )
                .values(
                    username=user.username,
                    email=user.email,
                    password_hash=password_hash,  # ✅ مشفرة
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_super_admin=user.is_super_admin,
                    updated_at=now,
                    updated_by=user.updated_by,
                    last_login=user.last_login,
                    version=new_version
                )
            )
            
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "User", 
                    str(user.id), 
                    user.version, 
                    existing.version
                )
            
            user.version = new_version
            
        else:
            # ✅ إنشاء مستخدم جديد مع تشفير كلمة المرور
            password_hash = user.password_hash
            if password_hash and not PasswordHasher.is_valid_hash(password_hash):
                password_hash = PasswordHasher.hash(password_hash)
            
            model = UserModel(
                id=user.id.value,
                username=user.username,
                email=user.email,
                password_hash=password_hash,  # ✅ مشفرة
                full_name=user.full_name,
                is_active=user.is_active,
                is_super_admin=user.is_super_admin,
                created_by=user.created_by,
                updated_by=user.updated_by,
            )
            self._session.add(model)
            self._session.flush()
            user.version = 1

    # ========== 💾 حفظ ذري (Atomic Save) ==========
    
    def save_atomic(self, users: List[User]) -> None:
        """
        حفظ عدة مستخدمين دفعة واحدة مع Optimistic Locking.
        
        Args:
            users: قائمة المستخدمين للحفظ
            
        Raises:
            ConcurrentModificationError: إذا تم تعديل أي مستخدم بشكل متزامن
        """
        if not users:
            return
        
        clock = get_clock()
        now = clock.now()
        
        # جلب الإصدارات الحالية للتحقق منها
        user_ids = [u.id.value for u in users]
        current_versions = self._session.execute(
            select(UserModel.id, UserModel.version)
            .where(UserModel.id.in_(user_ids))
        ).all()
        
        version_map = {str(row[0]): row[1] for row in current_versions}
        
        for user in users:
            user_id_str = str(user.id.value)
            
            if user_id_str in version_map:
                # ✅ التحقق من الإصدار (Optimistic Locking)
                if user.version != version_map[user_id_str]:
                    raise ConcurrentModificationError(
                        "User",
                        user_id_str,
                        user.version,
                        version_map[user_id_str]
                    )
                
                # تحديث المستخدم
                new_version = version_map[user_id_str] + 1
                
                # تشفير كلمة المرور إذا لزم الأمر
                password_hash = user.password_hash
                if password_hash and not PasswordHasher.is_valid_hash(password_hash):
                    password_hash = PasswordHasher.hash(password_hash)
                
                result = self._session.execute(
                    update(UserModel)
                    .where(
                        UserModel.id == user.id.value,
                        UserModel.version == user.version
                    )
                    .values(
                        username=user.username,
                        email=user.email,
                        password_hash=password_hash,
                        full_name=user.full_name,
                        is_active=user.is_active,
                        is_super_admin=user.is_super_admin,
                        updated_at=now,
                        updated_by=user.updated_by,
                        last_login=user.last_login,
                        version=new_version
                    )
                )
                
                if result.rowcount == 0:
                    raise ConcurrentModificationError(
                        "User",
                        user_id_str,
                        user.version,
                        version_map[user_id_str]
                    )
                
                user.version = new_version
                
            else:
                # مستخدم جديد
                password_hash = user.password_hash
                if password_hash and not PasswordHasher.is_valid_hash(password_hash):
                    password_hash = PasswordHasher.hash(password_hash)
                
                model = UserModel(
                    id=user.id.value,
                    username=user.username,
                    email=user.email,
                    password_hash=password_hash,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_super_admin=user.is_super_admin,
                    created_by=user.created_by,
                    updated_by=user.updated_by,
                )
                self._session.add(model)
                self._session.flush()
                user.version = 1
        
        logger.debug(f"💾 Atomic save completed for {len(users)} users")

    # ========== 🔒 قفل المستخدمين للتحديث ==========
    
    def lock_users_for_update(self, user_ids: List[UserId]) -> List[User]:
        """
        قفل المستخدمين باستخدام SELECT FOR UPDATE لمنع التعديل المتزامن.
        
        Args:
            user_ids: قائمة معرفات المستخدمين المراد قفلها
            
        Returns:
            List[User]: قائمة المستخدمين المقفلة
            
        Raises:
            ValueError: إذا لم يتم العثور على أحد المستخدمين
        """
        if not user_ids:
            return []
        
        ids = [uid.value for uid in user_ids]
        
        # 🔒 قفل الصفوف للتحديث
        models = self._session.execute(
            select(UserModel)
            .where(UserModel.id.in_(ids))
            .with_for_update()  # 🔒 قفل حصري
        ).scalars().all()
        
        # التحقق من وجود جميع المستخدمين المطلوبين
        found_ids = {str(m.id) for m in models}
        requested_ids = {str(uid.value) for uid in user_ids}
        
        missing = requested_ids - found_ids
        if missing:
            raise ValueError(f"Users not found: {', '.join(missing)}")
        
        # تحويل إلى Domain Entities
        users = []
        for model in models:
            user = _user_model_to_domain(model)
            user.password_hash = model.password_hash
            users.append(user)
        
        logger.debug(f"🔒 Locked {len(users)} users for update")
        return users

    # ========== عمليات الاستعلام ==========
    
    def get_by_id(self, user_id: UserId) -> Optional[User]:
        model = self._session.execute(
            select(UserModel).options(selectinload(UserModel.roles)).where(UserModel.id == user_id.value)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        # ✅ تحويل إلى Domain مع الاحتفاظ بكلمة المرور المشفرة
        user = _user_model_to_domain(model)
        user.password_hash = model.password_hash
        return user

    def get_by_username(self, username: str) -> Optional[User]:
        model = self._session.execute(
            select(UserModel).options(selectinload(UserModel.roles)).where(UserModel.username == username)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        user = _user_model_to_domain(model)
        user.password_hash = model.password_hash
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        model = self._session.execute(
            select(UserModel).options(selectinload(UserModel.roles)).where(UserModel.email == email)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        user = _user_model_to_domain(model)
        user.password_hash = model.password_hash
        return user

    def list_all(self, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[User]:
        query = select(UserModel).options(selectinload(UserModel.roles))
        if not include_inactive:
            query = query.where(UserModel.is_active == True)
        models = self._session.execute(query.limit(limit).offset(offset)).unique().scalars().all()
        return [_user_model_to_domain(m) for m in models]

    # ========== عمليات التحديث المتخصصة ==========
    
    def update_password(self, user_id: UserId, new_password: str, version: Optional[int] = None) -> bool:
        """
        تحديث كلمة مرور المستخدم فقط مع Optimistic Locking.
        
        Args:
            user_id: معرف المستخدم
            new_password: كلمة المرور الجديدة (نص عادي)
            version: الإصدار المتوقع (اختياري، للتحقق من التزامن)
        
        Returns:
            bool: True إذا تم التحديث بنجاح
            
        Raises:
            ConcurrentModificationError: إذا تم تعديل المستخدم بشكل متزامن
        """
        # ✅ تشفير كلمة المرور
        hashed_password = PasswordHasher.hash(new_password)
        
        # بناء الاستعلام مع أو بدون التحقق من الإصدار
        stmt = update(UserModel).where(UserModel.id == user_id.value)
        
        if version is not None:
            # ✅ مع التحقق من الإصدار
            stmt = stmt.where(UserModel.version == version)
            result = self._session.execute(
                stmt.values(
                    password_hash=hashed_password,
                    updated_at=utc_now(),
                    version=UserModel.version + 1
                )
            )
            
            if result.rowcount == 0:
                # جلب الإصدار الحالي لمعرفة سبب الفشل
                current = self._session.execute(
                    select(UserModel.version).where(UserModel.id == user_id.value)
                ).scalar()
                
                raise ConcurrentModificationError(
                    "User",
                    str(user_id.value),
                    version,
                    current or 0
                )
        else:
            # بدون التحقق من الإصدار (للمسؤولين فقط)
            result = self._session.execute(
                stmt.values(
                    password_hash=hashed_password,
                    updated_at=utc_now(),
                    version=UserModel.version + 1
                )
            )
        
        return result.rowcount > 0

    def soft_delete(self, user_id: UserId, deleted_by: str, version: Optional[int] = None) -> bool:
        """
        حذف ناعم (تعطيل) مستخدم مع Optimistic Locking.
        
        Args:
            user_id: معرف المستخدم
            deleted_by: من قام بالحذف
            version: الإصدار المتوقع (اختياري)
        
        Returns:
            bool: True إذا تم التعطيل بنجاح
            
        Raises:
            ConcurrentModificationError: إذا تم تعديل المستخدم بشكل متزامن
        """
        now = utc_now()
        
        stmt = update(UserModel).where(
            UserModel.id == user_id.value,
            UserModel.is_active == True  # فقط المستخدمين النشطين
        )
        
        if version is not None:
            stmt = stmt.where(UserModel.version == version)
        
        result = self._session.execute(
            stmt.values(
                is_active=False,
                updated_at=now,
                updated_by=deleted_by,
                version=UserModel.version + 1
            )
        )
        
        if version is not None and result.rowcount == 0:
            current = self._session.execute(
                select(UserModel.version, UserModel.is_active)
                .where(UserModel.id == user_id.value)
            ).first()
            
            if not current:
                return False
            
            current_version, is_active = current
            if not is_active:
                return True  # بالفعل غير نشط
            
            raise ConcurrentModificationError(
                "User",
                str(user_id.value),
                version,
                current_version
            )
        
        return result.rowcount > 0

    def bulk_update_roles(self, user_ids: List[UserId], role_names: List[str]) -> int:
        """
        تحديث أدوار عدة مستخدمين دفعة واحدة.
        
        Args:
            user_ids: قائمة معرفات المستخدمين
            role_names: قائمة أسماء الأدوار
            
        Returns:
            int: عدد المستخدمين المحدثين
        """
        if not user_ids or not role_names:
            return 0
        
        # جلب الأدوار
        roles = self._session.execute(
            select(RoleModel).where(RoleModel.name.in_(role_names))
        ).scalars().all()
        
        if not roles:
            return 0
        
        # تحديث كل مستخدم
        updated_count = 0
        for user_id in user_ids:
            user = self.get_by_id(user_id)
            if user:
                # إضافة الأدوار الجديدة
                for role in roles:
                    if role not in user.roles:
                        user.roles.append(role)
                
                self.save(user)  # ✅ سيتم التحقق من الإصدار
                updated_count += 1
        
        return updated_count

    def delete(self, user_id: UserId) -> bool:
        model = self._session.execute(
            select(UserModel).where(UserModel.id == user_id.value)
        ).scalar_one_or_none()
        if not model:
            return False
        self._session.delete(model)
        return True


# ========== مستودع الأدوار ==========

class PostgresRoleRepository(IRoleRepository):
    """تطبيق PostgreSQL لمستودع الأدوار"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, role: Role) -> None:
        existing = self._session.execute(
            select(RoleModel).where(RoleModel.id == role.id.value)
        ).scalar_one_or_none()

        if existing:
            now = utc_now()
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(RoleModel)
                .where(
                    RoleModel.id == role.id.value,
                    RoleModel.version == role.version  # ✅ Optimistic Locking
                )
                .values(
                    name=role.name,
                    display_name=role.display_name,
                    description=role.description,
                    is_admin=role.is_admin,
                    is_active=role.is_active,
                    updated_at=now,
                    updated_by=role.updated_by,
                    version=new_version
                )
            )
            
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Role", 
                    str(role.id), 
                    role.version, 
                    existing.version
                )
            
            role.version = new_version
            
        else:
            model = RoleModel(
                id=role.id.value,
                name=role.name,
                display_name=role.display_name,
                description=role.description,
                is_admin=role.is_admin,
                is_active=role.is_active,
                created_by=role.created_by,
                updated_by=role.updated_by,
            )
            self._session.add(model)
            self._session.flush()
            role.version = 1

    def get_by_id(self, role_id: RoleId) -> Optional[Role]:
        model = self._session.execute(
            select(RoleModel).options(selectinload(RoleModel.permissions)).where(RoleModel.id == role_id.value)
        ).unique().scalar_one_or_none()
        return _role_model_to_domain(model) if model else None

    def get_by_name(self, name: str) -> Optional[Role]:
        model = self._session.execute(
            select(RoleModel).options(selectinload(RoleModel.permissions)).where(RoleModel.name == name)
        ).unique().scalar_one_or_none()
        return _role_model_to_domain(model) if model else None

    def list_all(self, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[Role]:
        query = select(RoleModel).options(selectinload(RoleModel.permissions))
        if not include_inactive:
            query = query.where(RoleModel.is_active == True)
        models = self._session.execute(query.limit(limit).offset(offset)).unique().scalars().all()
        return [_role_model_to_domain(m) for m in models]

    def delete(self, role_id: RoleId) -> bool:
        model = self._session.execute(
            select(RoleModel).where(RoleModel.id == role_id.value)
        ).scalar_one_or_none()
        if not model:
            return False
        self._session.delete(model)
        return True


# ========== مستودع الصلاحيات ==========

class PostgresPermissionRepository(IPermissionRepository):
    """تطبيق PostgreSQL لمستودع الصلاحيات"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, permission: Permission) -> None:
        existing = self._session.execute(
            select(PermissionModel).where(PermissionModel.id == permission.id.value)
        ).scalar_one_or_none()

        if existing:
            now = utc_now()
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(PermissionModel)
                .where(
                    PermissionModel.id == permission.id.value,
                    PermissionModel.version == permission.version  # ✅ Optimistic Locking
                )
                .values(
                    code=permission.code,
                    name=permission.name,
                    description=permission.description,
                    category=permission.category,
                    is_active=permission.is_active,
                    updated_at=now,
                    updated_by=permission.updated_by,
                    version=new_version
                )
            )
            
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Permission", 
                    str(permission.id), 
                    permission.version, 
                    existing.version
                )
            
            permission.version = new_version
            
        else:
            model = PermissionModel(
                id=permission.id.value,
                code=permission.code,
                name=permission.name,
                description=permission.description,
                category=permission.category,
                is_active=permission.is_active,
                created_by=permission.created_by,
                updated_by=permission.updated_by,
            )
            self._session.add(model)
            self._session.flush()
            permission.version = 1

    def get_by_id(self, permission_id: PermissionId) -> Optional[Permission]:
        model = self._session.execute(
            select(PermissionModel).where(PermissionModel.id == permission_id.value)
        ).scalar_one_or_none()
        return _permission_model_to_domain(model) if model else None

    def get_by_code(self, code: str) -> Optional[Permission]:
        model = self._session.execute(
            select(PermissionModel).where(PermissionModel.code == code)
        ).scalar_one_or_none()
        return _permission_model_to_domain(model) if model else None

    def list_all(self, category: Optional[str] = None, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[Permission]:
        query = select(PermissionModel)
        if category:
            query = query.where(PermissionModel.category == category)
        if not include_inactive:
            query = query.where(PermissionModel.is_active == True)
        models = self._session.execute(query.limit(limit).offset(offset)).scalars().all()
        return [_permission_model_to_domain(m) for m in models]

    def list_by_category(self, category: str) -> List[Permission]:
        return self.list_all(category=category)

    def delete(self, permission_id: PermissionId) -> bool:
        model = self._session.execute(
            select(PermissionModel).where(PermissionModel.id == permission_id.value)
        ).scalar_one_or_none()
        if not model:
            return False
        self._session.delete(model)
        return True