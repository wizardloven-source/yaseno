# core/application/security/authorization_service.py
"""
Authorization Service - خدمة الصلاحيات الديناميكية
✅ محدث: دعم تشفير كلمات المرور عبر PasswordHasher
✅ محدث: دعم تغيير كلمة المرور
✅ محدث: دعم التحقق من صحة كلمة المرور
"""

from typing import Optional, Dict, Any, List
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.domain.auth.entities import User, Role, Permission
from core.domain.auth.value_objects import UserId, RoleId, PermissionId
from core.domain.auth.interfaces import IUserRepository, IRoleRepository, IPermissionRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import PermissionDeniedError, ValidationError

# ✅ استيراد خدمة تشفير كلمات المرور
from core.application.security.password_hasher import PasswordHasher

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserContext:
    """سياق المستخدم الحالي"""
    user_id: str
    username: str
    full_name: str
    is_super_admin: bool
    permissions: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    login_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def has_permission(self, permission_code: str) -> bool:
        """التحقق من وجود صلاحية"""
        if self.is_super_admin:
            return True
        return permission_code in self.permissions

    def has_any_permission(self, *permission_codes: str) -> bool:
        """التحقق من وجود أي من الصلاحيات"""
        return any(self.has_permission(p) for p in permission_codes)

    def has_all_permissions(self, *permission_codes: str) -> bool:
        """التحقق من وجود جميع الصلاحيات"""
        return all(self.has_permission(p) for p in permission_codes)
    
    def has_role(self, role_name: str) -> bool:
        """التحقق من وجود دور معين (يحتاج إلى تنفيذ)"""
        # سيتم تنفيذها عند ربط الأدوار بالسياق
        return False


class AuthorizationService:
    """
    خدمة الصلاحيات - تدير المستخدمين والأدوار والصلاحيات
    ✅ محدث: دعم تشفير كلمات المرور
    """

    def __init__(self, uow: IUnitOfWork):
        self._uow = uow

    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """الحصول على سياق المستخدم من قاعدة البيانات"""
        with self._uow:
            user_repo = self._uow.users
            user = user_repo.get_by_id(UserId.from_string(user_id))
            
            if not user:
                return None

            permissions = []
            for role in user.roles:
                for perm in role.permissions:
                    if perm.is_active:
                        permissions.append(perm.code)

            return UserContext(
                user_id=str(user.id.value),
                username=user.username,
                full_name=user.full_name,
                is_super_admin=user.is_super_admin,
                permissions=list(set(permissions))  # إزالة التكرارات
            )

    def authenticate(self, username: str, password: str) -> Optional[UserContext]:
        """
        مصادقة المستخدم باستخدام اسم المستخدم وكلمة المرور
        
        ✅ محدث: استخدام PasswordHasher للتحقق من كلمة المرور
        
        Args:
            username: اسم المستخدم
            password: كلمة المرور (نص عادي)
        
        Returns:
            Optional[UserContext]: سياق المستخدم إذا نجحت المصادقة، وإلا None
        """
        with self._uow:
            user_repo = self._uow.users
            user = user_repo.get_by_username(username)
            
            if not user:
                logger.warning(f"Authentication failed: user '{username}' not found")
                return None
            
            # ✅ التحقق من كلمة المرور باستخدام bcrypt
            if not PasswordHasher.verify(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for user '{username}'")
                return None
            
            # ✅ التحقق من أن المستخدم نشط
            if not user.is_active:
                logger.warning(f"Authentication failed: user '{username}' is inactive")
                return None
            
            # ✅ تحديث وقت آخر تسجيل دخول
            user.last_login = datetime.now(timezone.utc)
            user_repo.save(user)
            self._uow.commit()
            
            logger.info(f"User '{username}' authenticated successfully")
            
            # ✅ إرجاع سياق المستخدم
            return self.get_user_context(str(user.id.value))

    def change_password(
        self, 
        user_id: str, 
        old_password: str, 
        new_password: str,
        confirm_password: Optional[str] = None
    ) -> bool:
        """
        تغيير كلمة مرور المستخدم
        
        ✅ محدث: استخدام PasswordHasher للتحقق والتشفير
        
        Args:
            user_id: معرف المستخدم
            old_password: كلمة المرور القديمة
            new_password: كلمة المرور الجديدة
            confirm_password: تأكيد كلمة المرور (اختياري)
        
        Returns:
            bool: True إذا تم التغيير بنجاح
        
        Raises:
            ValidationError: إذا فشل التحقق من صحة كلمة المرور
        """
        with self._uow:
            user_repo = self._uow.users
            user = user_repo.get_by_id(UserId.from_string(user_id))
            
            if not user:
                raise ValidationError(f"User '{user_id}' not found")
            
            # ✅ التحقق من كلمة المرور القديمة
            if not PasswordHasher.verify(old_password, user.password_hash):
                raise ValidationError("Invalid current password")
            
            # ✅ التحقق من تطابق كلمة المرور الجديدة مع التأكيد
            if confirm_password and new_password != confirm_password:
                raise ValidationError("Passwords do not match")
            
            # ✅ التحقق من قوة كلمة المرور الجديدة
            if len(new_password) < PasswordHasher.MIN_PASSWORD_LENGTH:
                raise ValidationError(
                    f"Password must be at least {PasswordHasher.MIN_PASSWORD_LENGTH} characters long"
                )
            
            # ✅ تشفير كلمة المرور الجديدة
            user.password_hash = PasswordHasher.hash(new_password)
            user.updated_at = datetime.now(timezone.utc)
            user.version += 1
            
            user_repo.save(user)
            self._uow.commit()
            
            logger.info(f"Password changed for user '{user.username}'")
            return True

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """
        إعادة تعيين كلمة مرور المستخدم (للمديرين فقط)
        
        ✅ محدث: استخدام PasswordHasher للتشفير
        
        Args:
            user_id: معرف المستخدم
            new_password: كلمة المرور الجديدة
        
        Returns:
            bool: True إذا تم التغيير بنجاح
        """
        with self._uow:
            user_repo = self._uow.users
            user = user_repo.get_by_id(UserId.from_string(user_id))
            
            if not user:
                raise ValidationError(f"User '{user_id}' not found")
            
            # ✅ التحقق من قوة كلمة المرور
            if len(new_password) < PasswordHasher.MIN_PASSWORD_LENGTH:
                raise ValidationError(
                    f"Password must be at least {PasswordHasher.MIN_PASSWORD_LENGTH} characters long"
                )
            
            # ✅ تشفير كلمة المرور الجديدة
            user.password_hash = PasswordHasher.hash(new_password)
            user.updated_at = datetime.now(timezone.utc)
            user.version += 1
            
            user_repo.save(user)
            self._uow.commit()
            
            logger.info(f"Password reset for user '{user.username}'")
            return True

    def create_role(self, name: str, display_name: str, description: Optional[str] = None, is_admin: bool = False) -> Role:
        """إنشاء دور جديد"""
        role = Role(
            id=RoleId.generate(),
            name=name,
            display_name=display_name,
            description=description,
            is_admin=is_admin
        )
        with self._uow:
            self._uow.roles.save(role)
            self._uow.commit()
        return role

    def create_permission(self, code: str, name: str, category: str, description: Optional[str] = None) -> Permission:
        """إنشاء صلاحية جديدة"""
        permission = Permission(
            id=PermissionId.generate(),
            code=code,
            name=name,
            category=category,
            description=description
        )
        with self._uow:
            self._uow.permissions.save(permission)
            self._uow.commit()
        return permission

    def assign_permission_to_role(self, role_id: str, permission_code: str) -> bool:
        """تعيين صلاحية لدور"""
        with self._uow:
            role_repo = self._uow.roles
            perm_repo = self._uow.permissions

            role = role_repo.get_by_id(RoleId.from_string(role_id))
            if not role:
                return False

            permission = perm_repo.get_by_code(permission_code)
            if not permission:
                return False

            if permission not in role.permissions:
                role.permissions.append(permission)
                role_repo.save(role)
                self._uow.commit()
            return True

    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """تعيين دور لمستخدم"""
        with self._uow:
            user_repo = self._uow.users
            role_repo = self._uow.roles

            user = user_repo.get_by_id(UserId.from_string(user_id))
            if not user:
                return False

            role = role_repo.get_by_name(role_name)
            if not role:
                return False

            if role not in user.roles:
                user.roles.append(role)
                user_repo.save(user)
                self._uow.commit()
            return True

    def get_user_permissions(self, user_id: str) -> List[str]:
        """الحصول على جميع صلاحيات المستخدم"""
        context = self.get_user_context(user_id)
        if not context:
            return []
        return context.permissions
    
    def validate_password_strength(self, password: str) -> tuple[bool, Optional[str]]:
        """
        التحقق من قوة كلمة المرور
        
        ✅ محدث: استخدام PasswordHasher للتحقق
        
        Args:
            password: كلمة المرور المراد التحقق منها
        
        Returns:
            tuple[bool, Optional[str]]: (صالح, رسالة الخطأ)
        """
        if len(password) < PasswordHasher.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {PasswordHasher.MIN_PASSWORD_LENGTH} characters"
        
        # ✅ التحقق من وجود حرف كبير
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        # ✅ التحقق من وجود حرف صغير
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        # ✅ التحقق من وجود رقم
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        # ✅ التحقق من وجود حرف خاص
        special_chars = "!@#$%^&*()_+-=[]{};':\"\\|,.<>/?`~"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        return True, None


# ========== ديكوراتور (Decorator) جديد ==========

def require_permission(permission_code: str):
    """
    ديكوراتور للتحقق من صلاحية المستخدم
    
    الاستخدام:
        @require_permission("accounting.post_entry")
        def post_entry_handler(command, user_context):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # البحث عن UserContext في المعاملات
            user_context = None
            for arg in args:
                if isinstance(arg, UserContext):
                    user_context = arg
                    break
            if not user_context:
                for key, val in kwargs.items():
                    if isinstance(val, UserContext):
                        user_context = val
                        break

            if not user_context:
                raise PermissionDeniedError(
                    permission_code,
                    "unknown",
                    "لم يتم العثور على سياق المستخدم"
                )

            if not user_context.has_permission(permission_code):
                raise PermissionDeniedError(
                    permission_code,
                    user_context.user_id,
                    f"المستخدم {user_context.username} لا يملك صلاحية {permission_code}"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator


# ✅ تصدير الدوال الجديدة
__all__ = [
    "UserContext",
    "AuthorizationService",
    "require_permission",
]