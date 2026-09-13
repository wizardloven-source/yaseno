"""
Security Domain Services

Implements:
- Authorization service
- Password policy enforcement
- Account lockout logic
- Audit trail recording
"""

from datetime import datetime, timezone, timedelta
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Protocol
from uuid import UUID

from .models import (
    User, Role, Permission, AuditEvent, AuditEventType,
    PasswordPolicy, STANDARD_PERMISSIONS
)


class RepositoryProtocol(Protocol):
    """Protocol for repositories used by security services"""
    
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        ...
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        ...
    
    def save_user(self, user: User) -> None:
        ...
    
    def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        ...
    
    def save_role(self, role: Role) -> None:
        ...
    
    def save_audit_event(self, event: AuditEvent) -> None:
        ...


class AuthorizationService:
    """
    Service for authorization checks
    
    Usage:
        auth_service = AuthorizationService(user_repository)
        
        # Check single permission
        if not auth_service.check_permission(user_id, "sales.invoice.create"):
            raise PermissionDeniedError(...)
        
        # Check any permission
        if not auth_service.check_any_permission(user_id, ["sales.invoice.create", "sales.invoice.update"]):
            raise PermissionDeniedError(...)
        
        # Require permission (raises exception)
        auth_service.require_permission(user_id, "accounting.journal_entry.post")
    """
    
    def __init__(self, user_repo: RepositoryProtocol):
        self.user_repo = user_repo
    
    def get_user(self, user_id: UUID) -> Optional[User]:
        return self.user_repo.get_user_by_id(user_id)
    
    def check_permission(self, user_id: UUID, permission_code: str) -> bool:
        """Check if user has a specific permission"""
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return False
        if user.is_locked:
            if user.locked_until and datetime.now(timezone.utc) < user.locked_until:
                return False
            else:
                # Lock expired, reset
                user.reset_failed_logins()
                self.user_repo.save_user(user)
        return user.has_permission(permission_code)
    
    def check_any_permission(self, user_id: UUID, permission_codes: List[str]) -> bool:
        """Check if user has at least one of the specified permissions"""
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return False
        return user.has_any_permission(permission_codes)
    
    def check_all_permissions(self, user_id: UUID, permission_codes: List[str]) -> bool:
        """Check if user has all of the specified permissions"""
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return False
        return user.has_all_permissions(permission_codes)
    
    def require_permission(self, user_id: UUID, permission_code: str) -> None:
        """Require a permission, raise exception if not granted"""
        if not self.check_permission(user_id, permission_code):
            user = self.get_user(user_id)
            username = user.username if user else "unknown"
            raise PermissionDeniedError(
                f"User '{username}' does not have permission '{permission_code}'"
            )
    
    def require_any_permission(self, user_id: UUID, permission_codes: List[str]) -> None:
        """Require at least one permission, raise exception if none granted"""
        if not self.check_any_permission(user_id, permission_codes):
            user = self.get_user(user_id)
            username = user.username if user else "unknown"
            raise PermissionDeniedError(
                f"User '{username}' does not have any of the required permissions: {permission_codes}"
            )
    
    def require_all_permissions(self, user_id: UUID, permission_codes: List[str]) -> None:
        """Require all permissions, raise exception if any missing"""
        if not self.check_all_permissions(user_id, permission_codes):
            user = self.get_user(user_id)
            username = user.username if user else "unknown"
            missing = [p for p in permission_codes if not user.has_permission(p)]
            raise PermissionDeniedError(
                f"User '{username}' is missing permissions: {missing}"
            )


class PermissionDeniedError(Exception):
    """Raised when a user does not have required permission"""
    pass


class AuthenticationService:
    """
    Service for authentication with password policy and account lockout
    """
    
    def __init__(self, user_repo: RepositoryProtocol, 
                 password_policy: Optional[PasswordPolicy] = None,
                 audit_repo: Optional[RepositoryProtocol] = None):
        self.user_repo = user_repo
        self.password_policy = password_policy or PasswordPolicy()
        self.audit_repo = audit_repo
    
    def authenticate(self, username: str, password: str, 
                     ip_address: Optional[str] = None,
                     device_info: Optional[str] = None,
                     session_id: Optional[str] = None) -> User:
        """
        Authenticate user with username and password
        
        Implements:
        - Password validation
        - Account lockout after failed attempts
        - Audit logging
        """
        import hashlib
        
        user = self.user_repo.get_user_by_username(username)
        
        if not user:
            # Log failed attempt for non-existent user (prevent enumeration)
            self._log_failed_login(username, ip_address, device_info, session_id, "User not found")
            raise AuthenticationError("Invalid credentials")
        
        if not user.is_active:
            self._log_failed_login(username, ip_address, device_info, session_id, "Account inactive")
            raise AuthenticationError("Account is inactive")
        
        # Check if account is locked
        if user.is_locked:
            if user.locked_until and datetime.now(timezone.utc) < user.locked_until:
                remaining = user.locked_until - datetime.now(timezone.utc)
                self._log_failed_login(username, ip_address, device_info, session_id, "Account locked")
                raise AccountLockedError(f"Account is locked. Try again in {remaining.seconds // 60} minutes")
            else:
                # Lock expired, reset
                user.reset_failed_logins()
                self.user_repo.save_user(user)
        
        # Verify password
        expected_hash = self._hash_password(password, user.username)
        if user.password_hash != expected_hash:
            user.record_failed_login()
            
            # Check if should lock account
            if user.failed_login_attempts >= self.password_policy.lockout_threshold:
                user.lock(self.password_policy.lockout_duration_minutes)
            
            self.user_repo.save_user(user)
            self._log_failed_login(username, ip_address, device_info, session_id, "Invalid password")
            raise AuthenticationError("Invalid credentials")
        
        # Successful login
        user.reset_failed_logins()
        user.last_login = datetime.now(timezone.utc)
        self.user_repo.save_user(user)
        
        # Log successful login
        self._log_successful_login(user, ip_address, device_info, session_id)
        
        return user
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt (use bcrypt in production)"""
        # In production, use: bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def _log_failed_login(self, username: str, ip_address: Optional[str],
                          device_info: Optional[str], session_id: Optional[str],
                          reason: str) -> None:
        """Log failed login attempt"""
        if self.audit_repo:
            event = AuditEvent.create(
                event_type=AuditEventType.LOGIN,
                entity_type="User",
                entity_id=UUID(int=0),  # Unknown user
                user_id=UUID(int=0),
                username=username,
                new_values={"reason": reason, "success": False},
                ip_address=ip_address,
                device_info=device_info,
                session_id=session_id,
                module="security"
            )
            try:
                self.audit_repo.save_audit_event(event)
            except Exception:
                pass  # Don't fail login due to audit failure
    
    def _log_successful_login(self, user: User, ip_address: Optional[str],
                               device_info: Optional[str], 
                               session_id: Optional[str]) -> None:
        """Log successful login"""
        if self.audit_repo:
            event = AuditEvent.create(
                event_type=AuditEventType.LOGIN,
                entity_type="User",
                entity_id=user.id,
                user_id=user.id,
                username=user.username,
                new_values={"success": True},
                ip_address=ip_address,
                device_info=device_info,
                session_id=session_id,
                module="security"
            )
            try:
                self.audit_repo.save_audit_event(event)
            except Exception:
                pass
    
    def change_password(self, user_id: UUID, old_password: str, 
                        new_password: str, changed_by: Optional[str] = None) -> None:
        """
        Change user password with policy validation
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify old password
        expected_hash = self._hash_password(old_password, user.username)
        if user.password_hash != expected_hash:
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password against policy
        violations = self.password_policy.validate(new_password)
        if violations:
            raise PasswordPolicyViolationError(violations)
        
        # Update password
        user.password_hash = self._hash_password(new_password, user.username)
        user.password_changed_at = datetime.now(timezone.utc)
        user.reset_failed_logins()
        self.user_repo.save_user(user)
        
        # Audit
        if self.audit_repo:
            event = AuditEvent.for_update(
                entity_type="User",
                entity_id=user.id,
                user_id=user_id,
                username=changed_by or user.username,
                old_values={},
                new_values={"password_changed": True},
                module="security"
            )
            self.audit_repo.save_audit_event(event)
    
    def validate_password(self, password: str) -> List[str]:
        """Validate password against policy, return list of violations"""
        return self.password_policy.validate(password)


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AccountLockedError(AuthenticationError):
    """Raised when account is locked"""
    pass


class PasswordPolicyViolationError(AuthenticationError):
    """Raised when password doesn't meet policy requirements"""
    
    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


class AuditTrailService:
    """
    Service for recording and querying audit events
    """
    
    def __init__(self, audit_repo: RepositoryProtocol):
        self.audit_repo = audit_repo
    
    def record(self, event: AuditEvent) -> None:
        """Record an audit event"""
        self.audit_repo.save_audit_event(event)
    
    def record_create(self, entity_type: str, entity_id: UUID, user_id: UUID, 
                      username: str, new_values: Dict[str, Any],
                      document_reference: Optional[str] = None,
                      **kwargs) -> AuditEvent:
        """Record a create event"""
        event = AuditEvent.for_create(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            new_values=new_values,
            document_reference=document_reference,
            **kwargs
        )
        self.record(event)
        return event
    
    def record_update(self, entity_type: str, entity_id: UUID, user_id: UUID,
                      username: str, old_values: Dict[str, Any],
                      new_values: Dict[str, Any], reason: Optional[str] = None,
                      **kwargs) -> AuditEvent:
        """Record an update event"""
        event = AuditEvent.for_update(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            old_values=old_values,
            new_values=new_values,
            reason=reason,
            **kwargs
        )
        self.record(event)
        return event
    
    def record_delete(self, entity_type: str, entity_id: UUID, user_id: UUID,
                      username: str, old_values: Dict[str, Any],
                      reason: Optional[str] = None, **kwargs) -> AuditEvent:
        """Record a delete event"""
        event = AuditEvent.for_delete(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            old_values=old_values,
            reason=reason,
            **kwargs
        )
        self.record(event)
        return event
    
    def record_post(self, entity_type: str, entity_id: UUID, user_id: UUID,
                    username: str, document_reference: str, **kwargs) -> AuditEvent:
        """Record a post event"""
        event = AuditEvent.for_post(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            document_reference=document_reference,
            **kwargs
        )
        self.record(event)
        return event
    
    def record_cancel(self, entity_type: str, entity_id: UUID, user_id: UUID,
                      username: str, document_reference: str, reason: str,
                      **kwargs) -> AuditEvent:
        """Record a cancel event"""
        event = AuditEvent.for_cancel(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            document_reference=document_reference,
            reason=reason,
            **kwargs
        )
        self.record(event)
        return event
    
    def query(self, entity_type: Optional[str] = None,
              entity_id: Optional[UUID] = None,
              user_id: Optional[UUID] = None,
              event_type: Optional[AuditEventType] = None,
              from_date: Optional[datetime] = None,
              to_date: Optional[datetime] = None,
              module: Optional[str] = None,
              limit: int = 100) -> List[AuditEvent]:
        """Query audit events with filters"""
        # Implementation depends on repository
        # This is a placeholder for the interface
        raise NotImplementedError("Query implementation depends on repository")
    
    def get_entity_history(self, entity_type: str, entity_id: UUID) -> List[AuditEvent]:
        """Get full audit history for an entity"""
        return self.query(entity_type=entity_type, entity_id=entity_id, limit=1000)
    
    def get_user_activity(self, user_id: UUID, 
                          from_date: Optional[datetime] = None) -> List[AuditEvent]:
        """Get all activities by a user"""
        return self.query(user_id=user_id, from_date=from_date, limit=500)


class PermissionService:
    """
    Service for managing permissions and roles
    """
    
    def __init__(self, user_repo: RepositoryProtocol, 
                 role_repo: RepositoryProtocol,
                 audit_repo: Optional[RepositoryProtocol] = None):
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.audit_repo = audit_repo
    
    def get_permission(self, code: str) -> Optional[Permission]:
        """Get a permission by code"""
        return STANDARD_PERMISSIONS.get(code)
    
    def get_all_permissions(self) -> Dict[str, Permission]:
        """Get all available permissions"""
        return STANDARD_PERMISSIONS.copy()
    
    def get_permissions_for_module(self, module: str) -> List[Permission]:
        """Get all permissions for a specific module"""
        return [p for p in STANDARD_PERMISSIONS.values() if p.module == module]
    
    def create_role(self, name: str, description: Optional[str] = None,
                    created_by: Optional[str] = None) -> Role:
        """Create a new role"""
        role = Role.create(name, description, created_by)
        self.role_repo.save_role(role)
        
        if self.audit_repo and created_by:
            user = self.user_repo.get_user_by_username(created_by)
            if user:
                self.audit_repo.save_audit_event(
                    AuditEvent.for_create(
                        entity_type="Role",
                        entity_id=role.id,
                        user_id=user.id,
                        username=created_by,
                        new_values={"name": name, "description": description},
                        module="security"
                    )
                )
        
        return role
    
    def add_permission_to_role(self, role_id: UUID, permission_code: str,
                                modified_by: Optional[str] = None) -> None:
        """Add a permission to a role"""
        role = self.role_repo.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        permission = self.get_permission(permission_code)
        if not permission:
            raise ValueError(f"Permission {permission_code} not found")
        
        old_permissions = [p.code for p in role.permissions].copy()
        role.add_permission(permission)
        self.role_repo.save_role(role)
        
        if self.audit_repo and modified_by:
            user = self.user_repo.get_user_by_username(modified_by)
            if user:
                self.audit_repo.save_audit_event(
                    AuditEvent.for_update(
                        entity_type="Role",
                        entity_id=role.id,
                        user_id=user.id,
                        username=modified_by,
                        old_values={"permissions": old_permissions},
                        new_values={"permissions": [p.code for p in role.permissions]},
                        module="security"
                    )
                )
    
    def remove_permission_from_role(self, role_id: UUID, permission_code: str,
                                     modified_by: Optional[str] = None) -> None:
        """Remove a permission from a role"""
        role = self.role_repo.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        if role.is_system:
            raise ValueError("Cannot modify system roles")
        
        old_permissions = [p.code for p in role.permissions].copy()
        role.remove_permission(permission_code)
        self.role_repo.save_role(role)
        
        if self.audit_repo and modified_by:
            user = self.user_repo.get_user_by_username(modified_by)
            if user:
                self.audit_repo.save_audit_event(
                    AuditEvent.for_update(
                        entity_type="Role",
                        entity_id=role.id,
                        user_id=user.id,
                        username=modified_by,
                        old_values={"permissions": old_permissions},
                        new_values={"permissions": [p.code for p in role.permissions]},
                        module="security"
                    )
                )
    
    def assign_role_to_user(self, user_id: UUID, role_id: UUID,
                             assigned_by: Optional[str] = None) -> None:
        """Assign a role to a user"""
        user = self.user_repo.get_user_by_id(user_id)
        role = self.role_repo.get_role_by_id(role_id)
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        if not role:
            raise ValueError(f"Role {role_id} not found")
        
        old_roles = [r.id for r in user.roles].copy()
        user.assign_role(role)
        self.user_repo.save_user(user)
        
        if self.audit_repo and assigned_by:
            assigner = self.user_repo.get_user_by_username(assigned_by)
            if assigner:
                self.audit_repo.save_audit_event(
                    AuditEvent.create(
                        event_type=AuditEventType.ROLE_ASSIGNMENT,
                        entity_type="User",
                        entity_id=user.id,
                        user_id=assigner.id,
                        username=assigned_by,
                        old_values={"roles": [str(r) for r in old_roles]},
                        new_values={"roles": [str(r) for r in user.roles]},
                        module="security"
                    )
                )
    
    def revoke_role_from_user(self, user_id: UUID, role_id: UUID,
                               revoked_by: Optional[str] = None) -> None:
        """Revoke a role from a user"""
        user = self.user_repo.get_user_by_id(user_id)
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        old_roles = [r.id for r in user.roles].copy()
        user.remove_role(role_id)
        self.user_repo.save_user(user)
        
        if self.audit_repo and revoked_by:
            revoker = self.user_repo.get_user_by_username(revoked_by)
            if revoker:
                self.audit_repo.save_audit_event(
                    AuditEvent.create(
                        event_type=AuditEventType.ROLE_ASSIGNMENT,
                        entity_type="User",
                        entity_id=user.id,
                        user_id=revoker.id,
                        username=revoked_by,
                        old_values={"roles": [str(r) for r in old_roles]},
                        new_values={"roles": [str(r) for r in user.roles]},
                        module="security"
                    )
                )
