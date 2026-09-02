# core/application/customer_branch/converters.py
"""
Customer Branch Converters - محولات فروع العملاء
"""

from typing import Optional

from core.domain.customer_branch.entities import CustomerBranch
from core.domain.customer_branch.value_objects import (
    BranchId, BranchCode, BranchStatus,
    BranchAddress, BranchContact, BranchGeoLocation
)

from .dtos import (
    CustomerBranchDTO,
    BranchAddressDTO,
    BranchContactDTO,
    BranchGeoLocationDTO,
    CreateBranchDTO
)


def branch_to_dto(branch: CustomerBranch) -> CustomerBranchDTO:
    """تحويل كيان الفرع إلى DTO"""
    if not branch:
        return None
    
    return CustomerBranchDTO(
        id=str(branch.id),
        code=str(branch.code),
        name=branch.name,
        status=branch.status.value,
        customer_id=branch.customer_id,
        customer_name=branch.customer_name,
        customer_code=branch.customer_code,
        address=BranchAddressDTO(
            street=branch.address.street,
            city=branch.address.city,
            country=branch.address.country,
            postal_code=branch.address.postal_code
        ),
        contact=BranchContactDTO(
            email=branch.contact.email,
            phone=branch.contact.phone,
            mobile=branch.contact.mobile,
            contact_person=branch.contact.contact_person
        ),
        geo_location=BranchGeoLocationDTO(
            latitude=branch.geo_location.latitude,
            longitude=branch.geo_location.longitude
        ),
        tax_number=branch.tax_number,
        is_default=branch.is_default,
        notes=branch.notes,
        working_hours=branch.working_hours,
        branch_type=branch.branch_type,
        created_at=branch.created_at,
        created_by=branch.created_by,
        updated_at=branch.updated_at,
        updated_by=branch.updated_by,
        version=branch.version
    )


def dto_to_branch(dto: CreateBranchDTO) -> CustomerBranch:
    """تحويل DTO إلى كيان فرع"""
    if not dto:
        return None
    
    return CustomerBranch.create(
        code=dto.code,
        name=dto.name,
        customer_id=dto.customer_id,
        customer_name=dto.customer_name,
        customer_code=dto.customer_code,
        address=BranchAddress(
            street=dto.street,
            city=dto.city,
            country=dto.country,
            postal_code=dto.postal_code
        ),
        contact=BranchContact(
            email=dto.email,
            phone=dto.phone,
            mobile=dto.mobile,
            contact_person=dto.contact_person
        ),
        geo_location=BranchGeoLocation(
            latitude=dto.latitude,
            longitude=dto.longitude
        ),
        tax_number=dto.tax_number,
        is_default=dto.is_default,
        notes=dto.notes,
        working_hours=dto.working_hours,
        branch_type=dto.branch_type,
        created_by=dto.created_by
    )


def branches_to_dto_list(branches: list) -> list:
    """تحويل قائمة فروع إلى قائمة DTOs"""
    if not branches:
        return []
    return [branch_to_dto(b) for b in branches if b]