# core/application/customers/converters.py
"""Converters for Customers Module"""

from core.domain.customers.entities import Customer
from .dtos import CustomerDTO


def customer_to_dto(customer: Customer) -> CustomerDTO:
    if not customer:
        return None

    return CustomerDTO(
        id=str(customer.id),
        code=str(customer.code),
        name=customer.name,
        status=customer.status.value,
        email=customer.contact_info.email,
        phone=customer.contact_info.phone,
        mobile=customer.contact_info.mobile,
        street=customer.address.street,
        city=customer.address.city,
        country=customer.address.country,
        tax_number=customer.tax_number,
        credit_limit=float(customer.credit_limit),
        currency=customer.currency,
        notes=customer.notes,
        created_at=customer.created_at,
        created_by=customer.created_by,
        updated_at=customer.updated_at,
        updated_by=customer.updated_by,
        version=customer.version,
    )