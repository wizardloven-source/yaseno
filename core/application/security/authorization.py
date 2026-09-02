# core/application/security/authorization.py
"""
نظام الصلاحيات المتقدم - النسخة الديناميكية
✅ دعم الصلاحيات من قاعدة البيانات
✅ دعم الأدوار المتداخلة
✅ دعم التخزين المؤقت (Caching)
✅ دعم التدقيق (Audit)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Set, Optional, Dict, List, Any, Callable
from functools import wraps
from datetime import datetime, timezone
import logging
import hashlib
import json
import contextvars
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# سياق المستخدم الحالي (لكل طلب) - ✅ للتخلص من استدعاء النظام التجريبي
# =============================================================================

_current_user_context_var: "contextvars.ContextVar[Optional['UserContext']]" = (
    contextvars.ContextVar("current_user_context", default=None)
)


def set_current_user_context(user_context: "Optional[UserContext]") -> None:
    """تعيين سياق المستخدم الحالي لهذا الطلب (request-scoped via contextvars)."""
    _current_user_context_var.set(user_context)


def get_current_user_context() -> "Optional[UserContext]":
    """الحصول على سياق المستخدم الحالي للطلب."""
    return _current_user_context_var.get()


def clear_current_user_context() -> None:
    """مسح سياق المستخدم الحالي للطلب."""
    _current_user_context_var.set(None)


def _find_user_context(args, kwargs) -> "Optional[UserContext]":
    """البحث عن كائن UserContext في المعاملات الموضعية أو المسماة."""
    for arg in args:
        if isinstance(arg, UserContext):
            return arg
    for val in kwargs.values():
        if isinstance(val, UserContext):
            return val
    return None


# =============================================================================
# الأنواع الأساسية (للتوافق مع الكود القديم)
# =============================================================================

class Role(Enum):
    """الأدوار الافتراضية - للتوافق مع الكود القديم"""
    VIEWER = "viewer"
    DATA_ENTRY = "data_entry"
    ACCOUNTANT = "accountant"
    SENIOR_ACCOUNTANT = "senior_accountant"
    ADMIN = "admin"
    AUDITOR = "auditor"
    
    def __str__(self) -> str:
        return self.value


class Permission(Enum):
    """الصلاحيات الافتراضية - سيتم استبدالها بقاعدة البيانات"""
    # عمليات القراءة
    VIEW_JOURNAL_ENTRY = "view_journal_entry"
    VIEW_TRIAL_BALANCE = "view_trial_balance"
    VIEW_ACCOUNT_BALANCE = "view_account_balance"
    VIEW_AUDIT_LOG = "view_audit_log"
    VIEW_PERIOD_STATUS = "view_period_status"
    
    # عمليات الكتابة
    CREATE_DRAFT = "create_draft"
    MODIFY_DRAFT = "modify_draft"
    DELETE_DRAFT = "delete_draft"
    CREATE_ENTRY = "create_entry"
    POST_ENTRY = "post_entry"
    REVERSE_ENTRY = "reverse_entry"
    BULK_POST = "bulk_post"
    
    # عمليات إدارية
    CLOSE_PERIOD = "close_period"
    OPEN_PERIOD = "open_period"
    MANAGE_ACCOUNTS = "manage_accounts"
    MANAGE_USERS = "manage_users"
    SYSTEM_CONFIG = "system_config"
    
    @classmethod
    def get_all_permissions(cls) -> List[str]:
        """الحصول على جميع الصلاحيات كقائمة نصوص"""
        return [p.value for p in cls]


# =============================================================================
# سياق المستخدم المتقدم
# =============================================================================

@dataclass(frozen=True)
class UserContext:
    """
    سياق المستخدم المتقدم - يدعم الصلاحيات الديناميكية
    """
    user_id: str
    username: str
    roles: Set[str]  # أسماء الأدوار (نصوص)
    permissions: Set[str]  # الصلاحيات الفعلية (نصوص)
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    login_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_super_admin: bool = False
    
    # ✅ دعم التخزين المؤقت للصلاحيات
    _permission_cache: Optional[Dict[str, bool]] = field(default=None, repr=False)
    
    def __post_init__(self):
        """تهيئة الكاش بعد الإنشاء"""
        if self._permission_cache is None:
            object.__setattr__(self, '_permission_cache', {})
    
    def has_permission(self, permission: str) -> bool:
        """
        التحقق من صلاحية (يدعم النصوص أو كائنات Permission)
        
        ✅ يدعم:
            - نص عادي: "post_entry"
            - كائن Permission: Permission.POST_ENTRY
            - اسم الصلاحية من القاعدة: "accounting.post_entry"
        """
        # تحويل الإدخال إلى نص
        if hasattr(permission, 'value'):
            permission_code = permission.value
        else:
            permission_code = str(permission)
        
        # ✅ المدير العام لديه كل الصلاحيات
        if self.is_super_admin:
            return True
        
        # ✅ التحقق من الكاش
        if self._permission_cache is not None:
            if permission_code in self._permission_cache:
                return self._permission_cache[permission_code]
        
        # ✅ التحقق من الصلاحية
        result = permission_code in self.permissions
        
        # ✅ تخزين في الكاش
        if self._permission_cache is not None:
            self._permission_cache[permission_code] = result
        
        return result
    
    def has_any_permission(self, *permissions: str) -> bool:
        """التحقق من وجود أي من الصلاحيات"""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, *permissions: str) -> bool:
        """التحقق من وجود جميع الصلاحيات"""
        return all(self.has_permission(p) for p in permissions)
    
    def has_role(self, role: str) -> bool:
        """التحقق من وجود دور معين"""
        return role in self.roles
    
    def has_any_role(self, *roles: str) -> bool:
        """التحقق من وجود أي من الأدوار"""
        return any(r in self.roles for r in roles)
    
    def get_permission_hash(self) -> str:
        """الحصول على هاش للصلاحيات (للتخزين المؤقت)"""
        sorted_perms = sorted(self.permissions)
        return hashlib.md5(json.dumps(sorted_perms).encode()).hexdigest()


# =============================================================================
# خدمة الصلاحيات المتقدمة
# =============================================================================

class AuthorizationService:
    """
    خدمة الصلاحيات المتقدمة - تدعم قاعدة البيانات والتخزين المؤقت
    """
    
    def __init__(self, get_user_permissions_func: Optional[Callable[[str], Set[str]]] = None):
        """
        Args:
            get_user_permissions_func: دالة لجلب صلاحيات المستخدم من قاعدة البيانات
        """
        self._get_user_permissions = get_user_permissions_func
        self._cache: Dict[str, Set[str]] = {}  # user_id -> permissions
        self._cache_ttl: int = 300  # 5 دقائق
    
    def set_permissions_provider(self, func: Callable[[str], Set[str]]) -> None:
        """تعيين مزود الصلاحيات (من قاعدة البيانات)"""
        self._get_user_permissions = func
    
    def get_user_context(
        self,
        user_id: str,
        username: str,
        roles: List[str],
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        is_super_admin: bool = False
    ) -> UserContext:
        """
        إنشاء سياق المستخدم مع الصلاحيات من قاعدة البيانات
        """
        # ✅ جلب الصلاحيات من قاعدة البيانات
        permissions = self._get_user_permissions(user_id) if self._get_user_permissions else set()
        
        # ✅ إضافة الصلاحيات من الأدوار الافتراضية (للتوافق مع الكود القديم)
        for role_name in roles:
            try:
                role_enum = Role(role_name.lower().strip())
                default_perms = DEFAULT_ROLE_PERMISSIONS.get(role_enum, set())
                permissions.update([p.value for p in default_perms])
            except ValueError:
                pass
        
        return UserContext(
            user_id=user_id,
            username=username,
            roles=set(roles),
            permissions=permissions,
            session_id=session_id,
            ip_address=ip_address,
            is_super_admin=is_super_admin
        )
    
    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """مسح الكاش"""
        if user_id:
            self._cache.pop(user_id, None)
        else:
            self._cache.clear()


# =============================================================================
# الديكوراتورات المحسنة
# =============================================================================

def require_permission(permission: str):
    """
    ديكوراتور للتحقق من الصلاحية
    
    ✅ يدعم:
        - نصوص: @require_permission("post_entry")
        - كائنات Permission: @require_permission(Permission.POST_ENTRY)
        - أسماء صلاحيات من القاعدة: @require_permission("accounting.post_entry")
    
    ✅ يحسن الأداء مع التخزين المؤقت
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # ✅ البحث عن UserContext في المعاملات
            user_context = _find_user_context(args, kwargs)
            
            if user_context is None:
                # ✅ الرجوع إلى سياق المستخدم الحالي للطلب (يُضبط عبر الـ API)
                user_context = get_current_user_context()
            
            if user_context is None:
                # ❌ لا يوجد مستخدم معرّف - رفض الوصول (بدون أي سياق تجريبي)
                from core.application.security.authorization import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=permission,
                    user_id="anonymous",
                    message=f"Authentication required: لا يوجد سياق مستخدم لتنفيذ {func.__name__}"
                )
            
            # ✅ التحقق من الصلاحية
            if not user_context.has_permission(permission):
                from core.application.security.authorization import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=permission,
                    user_id=user_context.user_id,
                    message=f"المستخدم {user_context.username} لا يملك صلاحية {permission}"
                )
            
            # ✅ حقن سياق المستخدم إذا لم يكن موجوداً في المعاملات
            if not any(isinstance(a, UserContext) for a in args) and \
               not any(isinstance(v, UserContext) for v in kwargs.values()):
                kwargs["user_context"] = user_context
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """
    ديكوراتور للتحقق من الدور
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # ✅ البحث عن UserContext في المعاملات
            user_context = _find_user_context(args, kwargs)
            
            if user_context is None:
                # ✅ الرجوع إلى سياق المستخدم الحالي للطلب
                user_context = get_current_user_context()
            
            if user_context is None:
                # ❌ لا يوجد مستخدم معرّف - رفض الوصول (بدون أي تنفيذ تجريبي)
                from core.application.security.authorization import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=None,
                    user_id="anonymous",
                    required_role=role,
                    message=f"Authentication required: لا يوجد سياق مستخدم لتنفيذ {func.__name__}"
                )
            
            if not user_context.has_role(role):
                from core.application.security.authorization import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=None,
                    user_id=user_context.user_id,
                    required_role=role
                )
            
            # ✅ حقن سياق المستخدم إذا لم يكن موجوداً في المعاملات
            if not any(isinstance(a, UserContext) for a in args) and \
               not any(isinstance(v, UserContext) for v in kwargs.values()):
                kwargs["user_context"] = user_context
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# الصلاحيات الافتراضية - للتطوير والتوافق
# =============================================================================

DEFAULT_ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.VIEW_JOURNAL_ENTRY,
        Permission.VIEW_TRIAL_BALANCE,
        Permission.VIEW_ACCOUNT_BALANCE,
        Permission.VIEW_PERIOD_STATUS,
    },
    
    Role.DATA_ENTRY: {
        Permission.VIEW_JOURNAL_ENTRY,
        Permission.VIEW_TRIAL_BALANCE,
        Permission.VIEW_ACCOUNT_BALANCE,
        Permission.VIEW_PERIOD_STATUS,
        Permission.CREATE_DRAFT,
        Permission.MODIFY_DRAFT,
        Permission.DELETE_DRAFT,
    },
    
    Role.ACCOUNTANT: {
        Permission.VIEW_JOURNAL_ENTRY,
        Permission.VIEW_TRIAL_BALANCE,
        Permission.VIEW_ACCOUNT_BALANCE,
        Permission.VIEW_PERIOD_STATUS,
        Permission.CREATE_DRAFT,
        Permission.MODIFY_DRAFT,
        Permission.DELETE_DRAFT,
        Permission.CREATE_ENTRY,
        Permission.POST_ENTRY,
    },
    
    Role.SENIOR_ACCOUNTANT: {
        Permission.VIEW_JOURNAL_ENTRY,
        Permission.VIEW_TRIAL_BALANCE,
        Permission.VIEW_ACCOUNT_BALANCE,
        Permission.VIEW_PERIOD_STATUS,
        Permission.CREATE_DRAFT,
        Permission.MODIFY_DRAFT,
        Permission.DELETE_DRAFT,
        Permission.CREATE_ENTRY,
        Permission.POST_ENTRY,
        Permission.REVERSE_ENTRY,
        Permission.BULK_POST,
    },
    
    Role.ADMIN: {
        Permission.VIEW_JOURNAL_ENTRY,
        Permission.VIEW_TRIAL_BALANCE,
        Permission.VIEW_ACCOUNT_BALANCE,
        Permission.VIEW_PERIOD_STATUS,
        Permission.VIEW_AUDIT_LOG,
        Permission.CREATE_DRAFT,
        Permission.MODIFY_DRAFT,
        Permission.DELETE_DRAFT,
        Permission.CREATE_ENTRY,
        Permission.POST_ENTRY,
        Permission.REVERSE_ENTRY,
        Permission.BULK_POST,
        Permission.CLOSE_PERIOD,
        Permission.OPEN_PERIOD,
        Permission.MANAGE_ACCOUNTS,
        Permission.MANAGE_USERS,
        Permission.SYSTEM_CONFIG,
    },
    
    Role.AUDITOR: {
        Permission.VIEW_JOURNAL_ENTRY,
        Permission.VIEW_TRIAL_BALANCE,
        Permission.VIEW_ACCOUNT_BALANCE,
        Permission.VIEW_PERIOD_STATUS,
        Permission.VIEW_AUDIT_LOG,
    },
}


# =============================================================================
# دالة مساعدة للحصول على الصلاحيات من قاعدة البيانات
# =============================================================================

def get_user_permissions_from_db(user_id: str, uow) -> Set[str]:
    """
    جلب صلاحيات المستخدم من قاعدة البيانات
    
    هذه الدالة تستخدم مع AuthorizationService
    
    Args:
        user_id: معرف المستخدم
        uow: Unit of Work
    
    Returns:
        Set[str]: مجموعة الصلاحيات
    """
    try:
        # ✅ استيراد المستودع
        from core.infrastructure.db.postgres.auth_repository import PostgresUserRepository
        
        user_repo = PostgresUserRepository(uow.session)
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return set()
        
        # ✅ جمع الصلاحيات من الأدوار
        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                if perm.is_active:
                    permissions.add(perm.code)
        
        return permissions
    except Exception as e:
        logger.error(f"خطأ في جلب صلاحيات المستخدم {user_id}: {e}")
        return set()


# =============================================================================
# مدير الصلاحيات العالمي
# =============================================================================

class PermissionManager:
    """
    مدير الصلاحيات المركزي - نقطة الوصول الوحيدة للصلاحيات
    """
    
    _instance: Optional['PermissionManager'] = None
    _authorization_service: Optional[AuthorizationService] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._authorization_service = AuthorizationService()
    
    def initialize(self, uow_provider: Callable):
        """تهيئة مدير الصلاحيات مع مزود قاعدة البيانات"""
        def get_permissions(user_id: str) -> Set[str]:
            uow = uow_provider()
            with uow:
                return get_user_permissions_from_db(user_id, uow)
        
        self._authorization_service.set_permissions_provider(get_permissions)
        logger.info("✅ PermissionManager initialized with database provider")
    
    def get_user_context(
        self,
        user_id: str,
        username: str,
        roles: List[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        is_super_admin: bool = False
    ) -> UserContext:
        """الحصول على سياق المستخدم"""
        return self._authorization_service.get_user_context(
            user_id=user_id,
            username=username,
            roles=roles or [],
            session_id=session_id,
            ip_address=ip_address,
            is_super_admin=is_super_admin
        )
    
    def clear_cache(self, user_id: Optional[str] = None):
        """مسح الكاش"""
        self._authorization_service.clear_cache(user_id)
    
    @staticmethod
    def instance() -> 'PermissionManager':
        return PermissionManager()

# =============================================================================
# استثناء منع الوصول
# =============================================================================

class PermissionDeniedError(Exception):
    """
    خطأ منع الوصول عند غياب الصلاحيات أو الأدوار المحاسبية المطلوبة
    """
    
    def __init__(
        self,
        permission: Optional[str] = None,
        user_id: str = "",
        required_role: Optional[str] = None,
        message: Optional[str] = None
    ):
        self.permission = permission
        self.user_id = user_id
        self.required_role = required_role
        
        if message:
            self.message = message
        else:
            self.message = f"User '{user_id}' does not have the required access level."
            if permission:
                self.message += f" Missing permission: {permission}"
            if required_role:
                self.message += f" Requires role: {required_role}"
                
        super().__init__(self.message)
# =============================================================================
# دالة مساعدة للتطبيق السريع
# =============================================================================

def get_user_context(user_id: str, username: str, roles: List[str] = None) -> UserContext:
    """
    دالة مساعدة سريعة للحصول على سياق المستخدم
    
    Args:
        user_id: معرف المستخدم
        username: اسم المستخدم
        roles: قائمة الأدوار (اختياري)
    
    Returns:
        UserContext: سياق المستخدم
    """
    return PermissionManager.instance().get_user_context(
        user_id=user_id,
        username=username,
        roles=roles or []
    )


__all__ = [
    "Role",
    "Permission",
    "UserContext",
    "PermissionDeniedError",
    "require_permission",
    "require_role",
    "AuthorizationService",
    "PermissionManager",
    "DEFAULT_ROLE_PERMISSIONS",
    "get_user_permissions_from_db",
    "get_user_context",
    "set_current_user_context",
    "get_current_user_context",
    "clear_current_user_context",
]