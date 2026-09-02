# core/bootstrap/modules/security.py
"""
وحدة الأمان - تسجيل جميع خدمات الأمان
الإصدار النهائي - متوافق مع الحاوية الجديدة
"""

from typing import TYPE_CHECKING, Dict, Any, Set, Optional
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class SecurityModule(Module):
    """وحدة الأمان - المصادقة، الصلاحيات، التدقيق"""
    
    name = "security"
    description = "المصادقة، الصلاحيات، إدارة المستخدمين، وسجل التدقيق"
    dependencies = ["database"]
    version = "2.0.0"
    order = 10  # تتحمل مبكراً لأنها أساسية
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الأمان"""
        
        # ========== Repositories (Scoped) ==========
        # ✅ استخدام uow بدلاً من session مباشرة
        container.register_scoped(
            "user_repo",
            "core.infrastructure.db.postgres.auth_repository.PostgresUserRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "role_repo",
            "core.infrastructure.db.postgres.auth_repository.PostgresRoleRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "permission_repo",
            "core.infrastructure.db.postgres.auth_repository.PostgresPermissionRepository",
            dependencies=["session"]
        )
        
        # ========== Core Services (Singleton) ==========
        container.register_singleton(
            "password_hasher",
            "core.application.security.password_hasher.PasswordHasher"
        )
        container.register_singleton(
            "session_manager",
            "core.application.security.authentication.SessionManager",
            dependencies=["secret_key", "session_timeout"]
        )
        container.register_singleton(
            "login_tracker",
            "core.application.security.authentication.LoginAttemptTracker",
            dependencies=["max_login_attempts", "lockout_minutes"]
        )
        
        # ========== Services (Scoped - جلسة لكل طلب) ==========
        container.register_scoped(
            "auth_service",
            "core.application.security.authentication.AuthenticationService",
            dependencies=["user_repo"]
        )
        container.register_scoped(
            "authz_service",
            "core.application.security.authorization.AuthorizationService",
            dependencies=["user_repo", "role_repo", "permission_repo"]
        )
        
        # ========== Permission Manager (Singleton) ==========
        container.register_singleton(
            "permission_manager",
            "core.application.security.authorization.PermissionManager"
        )
        
        # ========== User Command Handlers (Transient) ==========
        container.register_transient(
            "create_user_handler",
            "core.application.handlers.users.CreateUserHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "update_user_handler",
            "core.application.handlers.users.UpdateUserHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "delete_user_handler",
            "core.application.handlers.users.DeleteUserHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "change_password_handler",
            "core.application.handlers.users.ChangePasswordHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "reset_password_handler",
            "core.application.handlers.users.ResetPasswordHandler",
            dependencies=["uow"]
        )
        
        # ========== Role Command Handlers (Transient) ==========
        container.register_transient(
            "create_role_handler",
            "core.application.handlers.roles.CreateRoleHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "update_role_handler",
            "core.application.handlers.roles.UpdateRoleHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "delete_role_handler",
            "core.application.handlers.roles.DeleteRoleHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "assign_permission_handler",
            "core.application.handlers.roles.AssignPermissionHandler",
            dependencies=["uow"]
        )
        
        # ========== Query Handlers (Transient) ==========
        # ✅ استخدام uow بدلاً من repositories مباشرة
        container.register_transient(
            "get_user_handler",
            "core.application.handlers.users.GetUserQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "list_users_handler",
            "core.application.handlers.users.ListUsersQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "get_role_handler",
            "core.application.handlers.roles.GetRoleQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "list_roles_handler",
            "core.application.handlers.roles.ListRolesQueryHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "get_user_permissions_handler",
            "core.application.handlers.users.GetUserPermissionsQueryHandler",
            dependencies=["uow"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تهيئة أنظمة الأمان وتسجيل المعالجات"""
        
        # ========== 1. تهيئة Permission Manager ==========
        permission_manager = container.resolve("permission_manager")
        
        def get_permissions_provider(user_id: str) -> Set[str]:
            """جلب صلاحيات المستخدم من قاعدة البيانات"""
            try:
                # ✅ استخدام النطاق الجديد
                with container.scope() as scoped_container:
                    uow = scoped_container.resolve("uow")
                    with uow:
                        from core.application.security.authorization import get_user_permissions_from_db
                        return get_user_permissions_from_db(user_id, uow)
            except Exception as e:
                logger.error(f"Error getting permissions for user {user_id}: {e}")
                return set()
        
        permission_manager.initialize(get_permissions_provider)
        logger.info("✅ Permission Manager initialized")
        
        # تسجيل Permission Manager كـ instance
        container.register_instance("permission_manager", permission_manager)
        
        # ========== 2. تسجيل Handlers في Command/Query Bus ==========
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow (SCOPED)
        with container.scope() as scoped_container:
            command_bus = container.resolve("command_bus")
            query_bus = container.resolve("query_bus")
            
            # ===== Command Handlers =====
            # User Commands
            try:
                command_bus.register("CreateUserCommand", "create_user_handler")
                logger.info("✅ Registered CreateUserCommand")
            except Exception as e:
                logger.error(f"Failed to register CreateUserCommand: {e}")
                raise
            
            try:
                command_bus.register("UpdateUserCommand", "update_user_handler")
                logger.info("✅ Registered UpdateUserCommand")
            except Exception as e:
                logger.error(f"Failed to register UpdateUserCommand: {e}")
                raise
            
            try:
                command_bus.register("DeleteUserCommand", "delete_user_handler")
                logger.info("✅ Registered DeleteUserCommand")
            except Exception as e:
                logger.error(f"Failed to register DeleteUserCommand: {e}")
                raise
            
            try:
                command_bus.register("ChangePasswordCommand", "change_password_handler")
                logger.info("✅ Registered ChangePasswordCommand")
            except Exception as e:
                logger.error(f"Failed to register ChangePasswordCommand: {e}")
                raise
            
            try:
                command_bus.register("ResetPasswordCommand", "reset_password_handler")
                logger.info("✅ Registered ResetPasswordCommand")
            except Exception as e:
                logger.error(f"Failed to register ResetPasswordCommand: {e}")
                raise
            
            # Role Commands
            try:
                command_bus.register("CreateRoleCommand", "create_role_handler")
                logger.info("✅ Registered CreateRoleCommand")
            except Exception as e:
                logger.error(f"Failed to register CreateRoleCommand: {e}")
                raise
            
            try:
                command_bus.register("UpdateRoleCommand", "update_role_handler")
                logger.info("✅ Registered UpdateRoleCommand")
            except Exception as e:
                logger.error(f"Failed to register UpdateRoleCommand: {e}")
                raise
            
            try:
                command_bus.register("DeleteRoleCommand", "delete_role_handler")
                logger.info("✅ Registered DeleteRoleCommand")
            except Exception as e:
                logger.error(f"Failed to register DeleteRoleCommand: {e}")
                raise
            
            try:
                command_bus.register("AssignPermissionCommand", "assign_permission_handler")
                logger.info("✅ Registered AssignPermissionCommand")
            except Exception as e:
                logger.error(f"Failed to register AssignPermissionCommand: {e}")
                raise
            
            # ===== Query Handlers =====
            try:
                query_bus.register("GetUserQuery", "get_user_handler")
                logger.info("✅ Registered GetUserQuery")
            except Exception as e:
                logger.error(f"Failed to register GetUserQuery: {e}")
                raise
            
            try:
                query_bus.register("ListUsersQuery", "list_users_handler")
                logger.info("✅ Registered ListUsersQuery")
            except Exception as e:
                logger.error(f"Failed to register ListUsersQuery: {e}")
                raise
            
            try:
                query_bus.register("GetRoleQuery", "get_role_handler")
                logger.info("✅ Registered GetRoleQuery")
            except Exception as e:
                logger.error(f"Failed to register GetRoleQuery: {e}")
                raise
            
            try:
                query_bus.register("ListRolesQuery", "list_roles_handler")
                logger.info("✅ Registered ListRolesQuery")
            except Exception as e:
                logger.error(f"Failed to register ListRolesQuery: {e}")
                raise
            
            try:
                query_bus.register("GetUserPermissionsQuery", "get_user_permissions_handler")
                logger.info("✅ Registered GetUserPermissionsQuery")
            except Exception as e:
                logger.error(f"Failed to register GetUserPermissionsQuery: {e}")
                raise