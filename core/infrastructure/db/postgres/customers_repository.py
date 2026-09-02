"""PostgreSQL implementation of ICustomerRepository"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, or_, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.domain.customers.entities import Customer
from core.domain.customers.value_objects import (
    CustomerId, CustomerCode, CustomerStatus, ContactInfo, Address
)
from core.domain.customers.exceptions import CustomerNotFoundError
from core.domain.customers.interfaces import ICustomerRepository
from core.shared.exceptions import ConcurrentModificationError
from core.infrastructure.db.models.customer_model import CustomerModel


def _domain_to_model(customer: Customer) -> CustomerModel:
    """Convert domain Customer to ORM model"""
    return CustomerModel(
        id=customer.id.value,
        code=str(customer.code),
        name=customer.name,
        email=customer.contact_info.email,
        phone=customer.contact_info.phone,
        mobile=customer.contact_info.mobile,
        street=customer.address.street,
        city=customer.address.city,
        country=customer.address.country,
        tax_number=customer.tax_number,
        credit_limit=customer.credit_limit,
        currency=customer.currency,
        notes=customer.notes,
        status=customer.status.value,
        is_deleted=customer.deleted_at is not None,
        deleted_at=customer.deleted_at,
        deleted_by=customer.deleted_by,
        created_at=customer.created_at,
        created_by=customer.created_by,
        updated_at=customer.updated_at,
        updated_by=customer.updated_by,
        version=customer.version
    )


def _model_to_domain(model: CustomerModel) -> Customer:
    """Convert ORM model to domain Customer"""
    status_map = {
        "active": CustomerStatus.ACTIVE,
        "inactive": CustomerStatus.INACTIVE,
        "suspended": CustomerStatus.SUSPENDED,
        "blocked": CustomerStatus.BLOCKED,
    }
    status = status_map.get(model.status, CustomerStatus.ACTIVE)

    customer = Customer(
        id=CustomerId(model.id),
        code=CustomerCode(model.code),
        name=model.name,
        status=status,
        contact_info=ContactInfo(
            email=model.email,
            phone=model.phone,
            mobile=model.mobile
        ),
        address=Address(
            street=model.street,
            city=model.city,
            country=model.country
        ),
        tax_number=model.tax_number,
        credit_limit=model.credit_limit,
        currency=model.currency,
        notes=model.notes,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        deleted_at=model.deleted_at,
        deleted_by=model.deleted_by,
        version=model.version
    )

    return customer


class PostgresCustomerRepository(ICustomerRepository):
    """PostgreSQL implementation of ICustomerRepository with Optimistic Locking"""
    
    def __init__(self, session: Session):
        self._session = session

    def save(self, customer: Customer) -> None:
        """
        Save customer to database with Optimistic Locking
        
        ✅ التعديل: استخدام UPDATE مع شرط الإصدار للتحقق من التزامن
        """
        existing = self._session.execute(
            select(CustomerModel).where(CustomerModel.id == customer.id.value)
        ).scalar_one_or_none()

        if existing:
            # ✅ التحديث مع التحقق من الإصدار (Optimistic Locking)
            now = datetime.now(timezone.utc)
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(CustomerModel)
                .where(
                    CustomerModel.id == customer.id.value,
                    CustomerModel.version == customer.version  # ✅ شرط التحقق
                )
                .values(
                    code=str(customer.code),
                    name=customer.name,
                    email=customer.contact_info.email,
                    phone=customer.contact_info.phone,
                    mobile=customer.contact_info.mobile,
                    street=customer.address.street,
                    city=customer.address.city,
                    country=customer.address.country,
                    tax_number=customer.tax_number,
                    credit_limit=customer.credit_limit,
                    currency=customer.currency,
                    notes=customer.notes,
                    status=customer.status.value,
                    is_deleted=customer.deleted_at is not None,
                    deleted_at=customer.deleted_at,
                    deleted_by=customer.deleted_by,
                    updated_at=now,
                    updated_by=customer.updated_by,
                    version=new_version
                )
            )
            
            # ✅ التحقق: إذا لم يتم تحديث أي صف، فهذا يعني تعارض في الإصدار
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Customer",
                    str(customer.id),
                    customer.version,
                    existing.version
                )
            
            # ✅ تحديث الكائن المحلي بالنسخة الجديدة
            customer.version = new_version
            
        else:
            # إنشاء عميل جديد
            model = _domain_to_model(customer)
            self._session.add(model)
            self._session.flush()
            customer.version = 1  # الإصدار الأولي

    def get_by_id(self, customer_id: CustomerId) -> Optional[Customer]:
        """Get customer by ID"""
        model = self._session.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id.value)
        ).scalar_one_or_none()

        if not model:
            return None
        return _model_to_domain(model)

    def get_by_code(self, code: CustomerCode) -> Optional[Customer]:
        """Get customer by code"""
        model = self._session.execute(
            select(CustomerModel).where(CustomerModel.code == str(code))
        ).scalar_one_or_none()

        if not model:
            return None
        return _model_to_domain(model)

    def list_all(
        self,
        status: Optional[CustomerStatus] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Customer]:
        """List all customers with optional filters"""
        query = select(CustomerModel)

        if status:
            query = query.where(CustomerModel.status == status.value)

        if not include_deleted:
            query = query.where(CustomerModel.is_deleted == False)

        models = self._session.execute(
            query.order_by(CustomerModel.name).limit(limit).offset(offset)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def search(
        self,
        search_text: str,
        status: Optional[CustomerStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Customer]:
        """Search customers by text"""
        search_pattern = f"%{search_text}%"

        conditions = [
            CustomerModel.code.ilike(search_pattern),
            CustomerModel.name.ilike(search_pattern),
            CustomerModel.email.ilike(search_pattern),
            CustomerModel.phone.ilike(search_pattern),
        ]

        query = select(CustomerModel).where(or_(*conditions))

        if status:
            query = query.where(CustomerModel.status == status.value)

        query = query.where(CustomerModel.is_deleted == False)

        models = self._session.execute(
            query.order_by(CustomerModel.name).limit(limit).offset(offset)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def get_next_code(self, prefix: str = "C") -> str:
        """Generate next customer code"""
        import re

        result = self._session.execute(
            select(CustomerModel.code)
            .where(CustomerModel.code.regexp_match(f'^{prefix}[0-9]+$'))
            .order_by(CustomerModel.code.desc())
            .limit(1)
        ).scalar_one_or_none()

        if result:
            match = re.search(rf'{prefix}(\d+)', result)
            if match:
                next_num = int(match.group(1)) + 1
            else:
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:05d}"

    def delete(self, customer_id: CustomerId, permanent: bool = False) -> bool:
        """Delete customer (soft or hard delete)"""
        model = self._session.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id.value)
        ).scalar_one_or_none()

        if not model:
            return False

        if permanent:
            self._session.delete(model)
        else:
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)

        return True

    def count(self, status: Optional[CustomerStatus] = None, include_deleted: bool = False) -> int:
        """Count customers"""
        query = select(func.count()).select_from(CustomerModel)

        if status:
            query = query.where(CustomerModel.status == status.value)

        if not include_deleted:
            query = query.where(CustomerModel.is_deleted == False)

        result = self._session.execute(query).scalar()
        return result or 0