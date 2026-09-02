"""
Postgres Customer Branch Repository - تنفيذ مستودع فروع العملاء
الإصدار: 1.0.0
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from core.domain.customer_branch.entities import CustomerBranch
from core.domain.customer_branch.value_objects import (
    BranchId, BranchCode, BranchStatus,
    BranchAddress, BranchContact, BranchGeoLocation
)
from core.domain.customer_branch.interfaces import ICustomerBranchRepository
from core.infrastructure.db.models.customer_branch_model import CustomerBranchModel


class PostgresCustomerBranchRepository(ICustomerBranchRepository):
    """
    تنفيذ PostgreSQL لمستودع فروع العملاء
    
    الميزات:
        1. تحويل تلقائي بين Domain و ORM
        2. دعم Optimistic Locking عبر version
        3. دعم الحذف الناعم (Soft Delete)
        4. بحث متقدم مع دعم التصفية
        5. معالجة الأخطاء الموحدة
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية
    # =========================================================================
    
    def save(self, branch: CustomerBranch) -> None:
        """
        حفظ فرع عميل (جديد أو محدث)
        
        Args:
            branch: كيان الفرع من Domain Layer
        """
        model = self._to_model(branch)
        self._session.merge(model)
        self._session.flush()
    
    def get_by_id(self, branch_id: BranchId) -> Optional[CustomerBranch]:
        """
        الحصول على فرع بواسطة المعرف
        
        Args:
            branch_id: معرف الفرع
        
        Returns:
            Optional[CustomerBranch]: كيان الفرع أو None
        """
        model = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.id == branch_id.value
        ).first()
        return self._to_entity(model) if model else None
    
    def get_by_code(self, code: BranchCode) -> Optional[CustomerBranch]:
        """
        الحصول على فرع بواسطة الكود
        
        Args:
            code: كود الفرع
        
        Returns:
            Optional[CustomerBranch]: كيان الفرع أو None
        """
        model = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.code == code.value,
            CustomerBranchModel.is_deleted == False
        ).first()
        return self._to_entity(model) if model else None
    
    def get_by_customer(
        self,
        customer_id: str,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[CustomerBranch]:
        """
        الحصول على فروع عميل معين
        
        Args:
            customer_id: معرف العميل
            include_inactive: تضمين الفروع غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[CustomerBranch]: قائمة فروع العميل
        """
        query = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.customer_id == customer_id,
            CustomerBranchModel.is_deleted == False
        )
        
        if not include_inactive:
            query = query.filter(CustomerBranchModel.status == "active")
        
        # ترتيب حسب الافتراضي أولاً ثم حسب الكود
        query = query.order_by(
            desc(CustomerBranchModel.is_default),
            asc(CustomerBranchModel.code)
        )
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    def get_default_branch(self, customer_id: str) -> Optional[CustomerBranch]:
        """
        الحصول على الفرع الافتراضي لعميل
        
        Args:
            customer_id: معرف العميل
        
        Returns:
            Optional[CustomerBranch]: الفرع الافتراضي أو None
        """
        model = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.customer_id == customer_id,
            CustomerBranchModel.is_default == True,
            CustomerBranchModel.is_deleted == False
        ).first()
        return self._to_entity(model) if model else None
    
    def list_all(
        self,
        status: Optional[BranchStatus] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[CustomerBranch]:
        """
        قائمة جميع الفروع
        
        Args:
            status: حالة الفرع (اختياري)
            include_deleted: تضمين الفروع المحذوفة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            List[CustomerBranch]: قائمة جميع الفروع
        """
        query = self._session.query(CustomerBranchModel)
        
        if not include_deleted:
            query = query.filter(CustomerBranchModel.is_deleted == False)
        
        if status:
            query = query.filter(CustomerBranchModel.status == status.value)
        
        # ترتيب حسب العميل ثم الكود
        query = query.order_by(
            asc(CustomerBranchModel.customer_name),
            asc(CustomerBranchModel.code)
        )
        
        models = query.limit(limit).offset(offset).all()
        return [self._to_entity(m) for m in models]
    
    def search(
        self,
        search_text: str,
        customer_id: Optional[str] = None,
        limit: int = 50
    ) -> List[CustomerBranch]:
        """
        البحث عن فروع
        
        Args:
            search_text: النص المطلوب البحث عنه
            customer_id: معرف العميل (اختياري - للتصفية)
            limit: الحد الأقصى للنتائج
        
        Returns:
            List[CustomerBranch]: قائمة الفروع المطابقة
        """
        query = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.is_deleted == False
        )
        
        if customer_id:
            query = query.filter(CustomerBranchModel.customer_id == customer_id)
        
        # البحث في عدة حقول
        search = f"%{search_text}%"
        query = query.filter(
            or_(
                CustomerBranchModel.code.ilike(search),
                CustomerBranchModel.name.ilike(search),
                CustomerBranchModel.city.ilike(search),
                CustomerBranchModel.phone.ilike(search),
                CustomerBranchModel.mobile.ilike(search),
                CustomerBranchModel.email.ilike(search),
                CustomerBranchModel.contact_person.ilike(search),
                CustomerBranchModel.street.ilike(search)
            )
        )
        
        # ترتيب حسب الأكثر تطابقاً
        query = query.order_by(
            asc(CustomerBranchModel.name)
        )
        
        models = query.limit(limit).all()
        return [self._to_entity(m) for m in models]
    
    def delete(self, branch_id: BranchId, permanent: bool = False) -> bool:
        """
        حذف فرع
        
        Args:
            branch_id: معرف الفرع
            permanent: حذف دائم (True) أو ناعم (False)
        
        Returns:
            bool: نجاح العملية
        """
        model = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.id == branch_id.value
        ).first()
        
        if not model:
            return False
        
        if permanent:
            self._session.delete(model)
        else:
            # حذف ناعم: تعطيل فقط
            from datetime import timezone
            model.is_deleted = True
            model.status = "deleted"
            model.deleted_at = datetime.now(timezone.utc)
        
        self._session.flush()
        return True
    
    def exists_by_code(self, code: BranchCode) -> bool:
        """
        التحقق من وجود فرع بالكود
        
        Args:
            code: كود الفرع
        
        Returns:
            bool: True إذا كان موجوداً
        """
        return self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.code == code.value,
            CustomerBranchModel.is_deleted == False
        ).first() is not None
    
    def count_by_customer(self, customer_id: str) -> int:
        """
        حساب عدد فروع العميل
        
        Args:
            customer_id: معرف العميل
        
        Returns:
            int: عدد الفروع
        """
        return self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.customer_id == customer_id,
            CustomerBranchModel.is_deleted == False
        ).count()
    
    def get_next_code(self, prefix: str = "BR") -> str:
        """
        توليد كود فرع تلقائي
        
        Args:
            prefix: بادئة الكود (افتراضي: BR)
        
        Returns:
            str: الكود التالي (مثل: BR-00001)
        """
        # الحصول على آخر كود
        last = self._session.query(CustomerBranchModel).filter(
            CustomerBranchModel.code.like(f"{prefix}-%")
        ).order_by(desc(CustomerBranchModel.code)).first()
        
        if not last:
            return f"{prefix}-00001"
        
        # استخراج الرقم التسلسلي
        try:
            parts = last.code.split('-')
            if len(parts) == 2:
                num = int(parts[1]) + 1
                return f"{prefix}-{num:05d}"
        except:
            pass
        
        return f"{prefix}-00001"
    
    # =========================================================================
    # دوال التحويل (Converters)
    # =========================================================================
    
    def _to_model(self, entity: CustomerBranch) -> CustomerBranchModel:
        """
        تحويل Domain Entity → ORM Model
        
        Args:
            entity: كيان الفرع من Domain Layer
        
        Returns:
            CustomerBranchModel: نموذج ORM
        """
        return CustomerBranchModel(
            id=entity.id.value,
            code=entity.code.value,
            name=entity.name,
            customer_id=entity.customer_id,
            customer_name=entity.customer_name,
            customer_code=entity.customer_code,
            
            # العنوان
            street=entity.address.street,
            city=entity.address.city,
            country=entity.address.country,
            postal_code=entity.address.postal_code,
            
            # الاتصال
            phone=entity.contact.phone,
            mobile=entity.contact.mobile,
            email=entity.contact.email,
            contact_person=entity.contact.contact_person,
            
            # الموقع الجغرافي
            latitude=entity.geo_location.latitude,
            longitude=entity.geo_location.longitude,
            
            # معلومات إضافية
            tax_number=entity.tax_number,
            is_default=entity.is_default,
            notes=entity.notes,
            working_hours=entity.working_hours,
            branch_type=entity.branch_type,
            
            # الحالة
            status=entity.status.value,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            deleted_by=entity.deleted_by,
            
            # بيانات التدقيق
            created_at=entity.created_at,
            created_by=entity.created_by,
            updated_at=entity.updated_at,
            updated_by=entity.updated_by,
            version=entity.version
        )
    
    def _to_entity(self, model: CustomerBranchModel) -> CustomerBranch:
        """
        تحويل ORM Model → Domain Entity
        
        Args:
            model: نموذج ORM
        
        Returns:
            CustomerBranch: كيان الفرع من Domain Layer
        """
        if not model:
            return None
        
        return CustomerBranch(
            id=BranchId(model.id),
            code=BranchCode(model.code),
            name=model.name,
            status=BranchStatus(model.status),
            customer_id=model.customer_id,
            customer_name=model.customer_name,
            customer_code=model.customer_code,
            
            # العنوان
            address=BranchAddress(
                street=model.street,
                city=model.city,
                country=model.country,
                postal_code=model.postal_code
            ),
            
            # الاتصال
            contact=BranchContact(
                email=model.email,
                phone=model.phone,
                mobile=model.mobile,
                contact_person=model.contact_person
            ),
            
            # الموقع الجغرافي
            geo_location=BranchGeoLocation(
                latitude=model.latitude,
                longitude=model.longitude
            ),
            
            # معلومات إضافية
            tax_number=model.tax_number,
            is_default=model.is_default,
            notes=model.notes,
            working_hours=model.working_hours,
            branch_type=model.branch_type,
            
            # الحذف
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            deleted_by=model.deleted_by,
            
            # بيانات التدقيق
            created_at=model.created_at,
            created_by=model.created_by,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
            version=model.version
        )