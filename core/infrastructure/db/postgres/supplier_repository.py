"""PostgreSQL implementation of ISupplierRepository"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, or_, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.domain.suppliers.entities import Supplier
from core.domain.suppliers.value_objects import (
    SupplierId, SupplierCode, SupplierStatus, ContactInfo, Address
)
from core.domain.suppliers.interfaces import ISupplierRepository
from core.shared.exceptions import ConcurrentModificationError
from core.infrastructure.db.models.supplier_model import SupplierModel


def _domain_to_model(supplier: Supplier) -> SupplierModel:
    return SupplierModel(
        id=supplier.id.value,
        code=str(supplier.code),
        name=supplier.name,
        email=supplier.contact_info.email,
        phone=supplier.contact_info.phone,
        mobile=supplier.contact_info.mobile,
        street=supplier.address.street,
        city=supplier.address.city,
        country=supplier.address.country,
        tax_number=supplier.tax_number,
        credit_limit=supplier.credit_limit,
        currency=supplier.currency,
        notes=supplier.notes,
        status=supplier.status.value,
        is_deleted=supplier.deleted_at is not None,
        deleted_at=supplier.deleted_at,
        deleted_by=supplier.deleted_by,
        created_at=supplier.created_at,
        created_by=supplier.created_by,
        updated_at=supplier.updated_at,
        updated_by=supplier.updated_by,
        version=supplier.version
    )


def _model_to_domain(model: SupplierModel) -> Supplier:
    status_map = {
        "active": SupplierStatus.ACTIVE,
        "inactive": SupplierStatus.INACTIVE,
        "suspended": SupplierStatus.SUSPENDED,
        "blocked": SupplierStatus.BLOCKED,
    }
    status = status_map.get(model.status, SupplierStatus.ACTIVE)

    supplier = Supplier(
        id=SupplierId(model.id),
        code=SupplierCode(model.code),
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

    return supplier


class PostgresSupplierRepository(ISupplierRepository):
    """
    PostgreSQL implementation of ISupplierRepository with Optimistic Locking
    """
    
    def __init__(self, session: Session):
        self._session = session

    def save(self, supplier: Supplier) -> None:
        """
        Save supplier to database with Optimistic Locking
        
        ✅ التعديل: استخدام UPDATE مع شرط الإصدار للتحقق من التزامن
        """
        existing = self._session.execute(
            select(SupplierModel).where(SupplierModel.id == supplier.id.value)
        ).scalar_one_or_none()

        if existing:
            # ✅ التحديث مع التحقق من الإصدار (Optimistic Locking)
            now = datetime.now(timezone.utc)
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(SupplierModel)
                .where(
                    SupplierModel.id == supplier.id.value,
                    SupplierModel.version == supplier.version  # ✅ شرط التحقق
                )
                .values(
                    code=str(supplier.code),
                    name=supplier.name,
                    email=supplier.contact_info.email,
                    phone=supplier.contact_info.phone,
                    mobile=supplier.contact_info.mobile,
                    street=supplier.address.street,
                    city=supplier.address.city,
                    country=supplier.address.country,
                    tax_number=supplier.tax_number,
                    credit_limit=supplier.credit_limit,
                    currency=supplier.currency,
                    notes=supplier.notes,
                    status=supplier.status.value,
                    is_deleted=supplier.deleted_at is not None,
                    deleted_at=supplier.deleted_at,
                    deleted_by=supplier.deleted_by,
                    updated_at=now,
                    updated_by=supplier.updated_by,
                    version=new_version
                )
            )
            
            # ✅ التحقق: إذا لم يتم تحديث أي صف، فهذا يعني تعارض في الإصدار
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Supplier",
                    str(supplier.id),
                    supplier.version,
                    existing.version
                )
            
            # ✅ تحديث الكائن المحلي بالنسخة الجديدة
            supplier.version = new_version
            
        else:
            # إنشاء مورد جديد
            model = _domain_to_model(supplier)
            self._session.add(model)
            self._session.flush()
            supplier.version = 1  # الإصدار الأولي

    def get_by_id(self, supplier_id: SupplierId) -> Optional[Supplier]:
        model = self._session.execute(
            select(SupplierModel).where(SupplierModel.id == supplier_id.value)
        ).scalar_one_or_none()

        if not model:
            return None
        return _model_to_domain(model)

    def get_by_code(self, code: SupplierCode) -> Optional[Supplier]:
        model = self._session.execute(
            select(SupplierModel).where(SupplierModel.code == str(code))
        ).scalar_one_or_none()

        if not model:
            return None
        return _model_to_domain(model)

    def list_all(
        self,
        status: Optional[SupplierStatus] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Supplier]:
        query = select(SupplierModel)

        if status:
            query = query.where(SupplierModel.status == status.value)

        if not include_deleted:
            query = query.where(SupplierModel.is_deleted == False)

        models = self._session.execute(
            query.order_by(SupplierModel.name).limit(limit).offset(offset)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def search(
        self,
        search_text: str,
        status: Optional[SupplierStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Supplier]:
        search_pattern = f"%{search_text}%"

        conditions = [
            SupplierModel.code.ilike(search_pattern),
            SupplierModel.name.ilike(search_pattern),
            SupplierModel.email.ilike(search_pattern),
            SupplierModel.phone.ilike(search_pattern),
        ]

        query = select(SupplierModel).where(or_(*conditions))

        if status:
            query = query.where(SupplierModel.status == status.value)

        query = query.where(SupplierModel.is_deleted == False)

        models = self._session.execute(
            query.order_by(SupplierModel.name).limit(limit).offset(offset)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def get_next_code(self, prefix: str = "S") -> str:
        import re

        result = self._session.execute(
            select(SupplierModel.code)
            .where(SupplierModel.code.regexp_match(f'^{prefix}[0-9]+$'))
            .order_by(SupplierModel.code.desc())
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

    def delete(self, supplier_id: SupplierId, permanent: bool = False) -> bool:
        model = self._session.execute(
            select(SupplierModel).where(SupplierModel.id == supplier_id.value)
        ).scalar_one_or_none()

        if not model:
            return False

        if permanent:
            self._session.delete(model)
        else:
            model.is_deleted = True
            model.deleted_at = datetime.now(timezone.utc)

        return True

    def count(self, status: Optional[SupplierStatus] = None, include_deleted: bool = False) -> int:
        query = select(func.count()).select_from(SupplierModel)

        if status:
            query = query.where(SupplierModel.status == status.value)

        if not include_deleted:
            query = query.where(SupplierModel.is_deleted == False)

        result = self._session.execute(query).scalar()
        return result or 0