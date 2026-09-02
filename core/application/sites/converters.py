# core/application/sites/converters.py
"""
Converters for Sites - تحويل بين Domain Entities و DTOs
"""

from core.domain.sites.entities import Site
from .dtos import SiteDTO


def site_to_dto(site: Site) -> SiteDTO:
    """
    تحويل كيان الموقع (Domain Entity) إلى DTO
    
    Args:
        site: كيان الموقع من Domain Layer
    
    Returns:
        SiteDTO: كائن نقل البيانات للموقع
    """
    if not site:
        return None
    
    return SiteDTO(
        id=site.id.value,
        code=site.code.value,
        name=site.name,
        site_type=site.site_type.value,
        street=site.street,
        city=site.city,
        country=site.country,
        phone=site.phone,
        mobile=site.mobile,
        email=site.email,
        contact_person=site.contact_person,
        notes=site.notes,
        is_active=site.is_active,
        is_default=site.is_default,
        is_deleted=site.is_deleted,
        created_at=site.created_at,
        created_by=site.created_by,
        updated_at=site.updated_at,
        updated_by=site.updated_by,
        version=site.version,
    )


def dto_to_site(dto: SiteDTO) -> dict:
    """
    تحويل SiteDTO إلى قاموس (للاستخدام في Service Layer)
    
    Args:
        dto: كائن نقل البيانات للموقع
    
    Returns:
        Dict: قاموس يحتوي على بيانات الموقع
    """
    if not dto:
        return None
    
    return {
        'id': str(dto.id),
        'code': dto.code,
        'name': dto.name,
        'site_type': dto.site_type,
        'street': dto.street,
        'city': dto.city,
        'country': dto.country,
        'phone': dto.phone,
        'mobile': dto.mobile,
        'email': dto.email,
        'contact_person': dto.contact_person,
        'notes': dto.notes,
        'is_active': dto.is_active,
        'is_default': dto.is_default,
        'is_deleted': dto.is_deleted,
        'created_at': dto.created_at.isoformat() if dto.created_at else None,
        'created_by': dto.created_by,
        'updated_at': dto.updated_at.isoformat() if dto.updated_at else None,
        'updated_by': dto.updated_by,
        'version': dto.version,
    }


__all__ = [
    "site_to_dto",
    "dto_to_site",
]