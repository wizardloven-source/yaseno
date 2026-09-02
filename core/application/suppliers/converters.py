# C:\Users\MTC\Desktop\erpya\core\application\suppliers\converters.py
"""Converters for Suppliers - تحويل بين Domain Entities و DTOs"""

from decimal import Decimal

from core.domain.suppliers.entities import Supplier
from core.domain.suppliers.value_objects import (
    SupplierId, SupplierCode, SupplierStatus,
    ContactInfo, Address
)
from .dtos import (
    SupplierDTO,
    ContactInfoDTO,
    AddressDTO
)


def contact_info_to_dto(contact_info: ContactInfo) -> ContactInfoDTO:
    """تحويل ContactInfo إلى DTO"""
    if not contact_info:
        return ContactInfoDTO()
    return ContactInfoDTO(
        email=contact_info.email,
        phone=contact_info.phone,
        mobile=contact_info.mobile
    )


def address_to_dto(address: Address) -> AddressDTO:
    """تحويل Address إلى DTO"""
    if not address:
        return AddressDTO()
    return AddressDTO(
        street=address.street,
        city=address.city,
        country=address.country
    )


def supplier_to_dto(supplier: Supplier) -> SupplierDTO:
    """تحويل كيان المورد إلى DTO"""
    if not supplier:
        return None
    
    return SupplierDTO(
        id=str(supplier.id),
        code=str(supplier.code),
        name=supplier.name,
        status=supplier.status.value,
        contact_info=contact_info_to_dto(supplier.contact_info),
        address=address_to_dto(supplier.address),
        tax_number=supplier.tax_number,
        credit_limit=float(supplier.credit_limit),
        currency=supplier.currency,
        notes=supplier.notes,
        created_at=supplier.created_at,
        created_by=supplier.created_by,
        updated_at=supplier.updated_at,
        updated_by=supplier.updated_by,
        version=supplier.version
    )


def dto_to_supplier_status(status: str) -> SupplierStatus:
    """تحويل نص إلى SupplierStatus"""
    status_map = {
        "active": SupplierStatus.ACTIVE,
        "inactive": SupplierStatus.INACTIVE,
        "suspended": SupplierStatus.SUSPENDED,
        "blocked": SupplierStatus.BLOCKED,
    }
    return status_map.get(status, SupplierStatus.ACTIVE)


def create_contact_info_from_dto(
    email: str = None,
    phone: str = None,
    mobile: str = None
) -> ContactInfo:
    """إنشاء ContactInfo من معاملات DTO"""
    return ContactInfo(
        email=email,
        phone=phone,
        mobile=mobile
    )


def create_address_from_dto(
    street: str = None,
    city: str = None,
    country: str = "LB"
) -> Address:
    """إنشاء Address من معاملات DTO"""
    return Address(
        street=street,
        city=city,
        country=country
    )


__all__ = [
    "contact_info_to_dto",
    "address_to_dto",
    "supplier_to_dto",
    "dto_to_supplier_status",
    "create_contact_info_from_dto",
    "create_address_from_dto",
]