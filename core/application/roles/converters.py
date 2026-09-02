# core/application/roles/converters.py
"""Converters for Roles"""

from core.domain.auth.entities import Role


def role_to_dto(role: Role) -> dict:
    """تحويل كيان الدور إلى DTO"""
    if not role:
        return None
    
    return {
        "id": str(role.id.value),
        "name": role.name,
        "display_name": role.display_name,
        "description": role.description,
        "is_admin": role.is_admin,
        "is_active": role.is_active,
        "permissions": [
            {
                "id": str(p.id.value),
                "code": p.code,
                "name": p.name,
                "category": p.category
            }
            for p in role.permissions
        ],
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "created_by": role.created_by,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
        "updated_by": role.updated_by,
        "version": role.version
    }