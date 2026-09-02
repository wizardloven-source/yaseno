# core/application/users/converters.py
"""Converters for Users - تحويل بين Domain Entities و DTOs"""

from core.domain.auth.entities import User
from .dtos import UserDTO


def user_to_dto(user: User) -> UserDTO:
    """تحويل كيان المستخدم إلى DTO"""
    if not user:
        return None

    return UserDTO(
        id=str(user.id.value),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_super_admin=user.is_super_admin,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
        created_by=user.created_by,
        updated_at=user.updated_at,
        updated_by=user.updated_by,
        last_login=user.last_login,
        version=user.version,
    )


__all__ = [
    "user_to_dto",
]