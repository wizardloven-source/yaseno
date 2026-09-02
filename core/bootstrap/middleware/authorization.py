# core/bootstrap/middleware/authorization.py
"""
Authorization Middleware - التحقق من صلاحيات المستخدم
مستخرج من bootstrap.py و infrastructure/messaging/middleware.py
"""

from typing import Any, Dict, Optional, Callable
import logging

from .base import Middleware

logger = logging.getLogger(__name__)


class AuthorizationMiddleware(Middleware):
    """
    Middleware للتحقق من صلاحيات المستخدم
    
    الميزات:
        1. التحقق من الصلاحيات المطلوبة للأمر
        2. التحقق من الأدوار المطلوبة
        3. دعم المستخدمين الفائقين (Super Admin)
        4. تخزين مؤقت للصلاحيات
    """
    
    def __init__(
        self,
        user_context_provider: Callable[[], Optional[Any]],
        permission_cache: Optional[Dict[str, set]] = None
    ):
        """
        Args:
            user_context_provider: دالة تعيد سياق المستخدم الحالي
            permission_cache: كاش الصلاحيات (اختياري)
        """
        self._user_context_provider = user_context_provider
        self._permission_cache = permission_cache or {}
    
    def before(self, command: Any, context: Dict) -> Dict:
        """التحقق من الصلاحيات قبل تنفيذ الأمر"""
        # الحصول على سياق المستخدم
        user_context = self._user_context_provider()
        context['user_context'] = user_context
        
        if not user_context:
            # إذا لم يكن هناك مستخدم، نسمح فقط بالأوامر العامة
            if self._requires_authentication(command):
                from core.shared.exceptions import PermissionDeniedError
                raise PermissionDeniedError(
                    permission="authentication",
                    user_id="unknown",
                    resource=self._get_command_name(command)
                )
            return context
        
        # التحقق من الصلاحيات
        required_permission = self._get_required_permission(command)
        if required_permission:
            if not user_context.has_permission(required_permission):
                from core.shared.exceptions import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=required_permission,
                    user_id=user_context.user_id,
                    resource=self._get_command_name(command)
                )
        
        # التحقق من الأدوار
        required_role = self._get_required_role(command)
        if required_role:
            if not user_context.has_role(required_role):
                from core.shared.exceptions import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=f"role:{required_role}",
                    user_id=user_context.user_id,
                    resource=self._get_command_name(command)
                )
        
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """لا يوجد منطق بعد التنفيذ"""
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """معالجة أخطاء الصلاحيات"""
        if isinstance(error, PermissionDeniedError):
            logger.warning(f"🔒 Permission denied: {error}")
        return None
    
    def _requires_authentication(self, command: Any) -> bool:
        """التحقق مما إذا كان الأمر يتطلب مصادقة"""
        # الأوامر التي لا تتطلب مصادقة
        public_commands = [
            'LoginCommand',
            'ResetPasswordCommand',
            'GetSettingsQuery',
        ]
        command_name = self._get_command_name(command)
        return command_name not in public_commands
    
    def _get_required_permission(self, command: Any) -> Optional[str]:
        """الحصول على الصلاحية المطلوبة للأمر"""
        if hasattr(command, 'required_permission'):
            return command.required_permission
        
        # البحث في خصائص الأمر
        for attr in ['permission', 'permission_required', 'required_permission']:
            if hasattr(command, attr):
                value = getattr(command, attr)
                if value:
                    return str(value)
        
        return None
    
    def _get_required_role(self, command: Any) -> Optional[str]:
        """الحصول على الدور المطلوب للأمر"""
        if hasattr(command, 'required_role'):
            return command.required_role
        
        if hasattr(command, 'role_required'):
            return command.role_required
        
        return None
    
    def _get_command_name(self, command: Any) -> str:
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    @property
    def priority(self) -> int:
        # ينفذ بعد المعاملة
        return 40
    
    @property
    def name(self) -> str:
        return "authorization"


class PermissionDeniedError(Exception):
    """استثناء يحدث عند عدم وجود صلاحية"""
    
    def __init__(self, permission: str, user_id: str, resource: Optional[str] = None):
        self.permission = permission
        self.user_id = user_id
        self.resource = resource
        message = f"Permission denied: {permission} for user {user_id}"
        if resource:
            message += f" on resource {resource}"
        super().__init__(message)