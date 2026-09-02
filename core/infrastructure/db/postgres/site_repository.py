# core/infrastructure/db/postgres/site_repository.py
"""
PostgreSQL Repository for Sites - مستودع المواقع
✅ يدعم Optimistic Locking عبر الـ version
✅ يدعم البحث المتقدم
✅ يدعم Pagination
✅ يدعم الحذف الناعم (Soft Delete)
✅ يدعم الحقول الجديدة: responsible_type, responsible_id, currency_code, إلخ
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import select, update, func, or_, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.domain.sites.entities import Site
from core.domain.sites.value_objects import SiteId, SiteCode, SiteType
from core.domain.sites.exceptions import SiteNotFoundError, DuplicateSiteCodeError
from core.shared.exceptions import ConcurrentModificationError
from core.domain.sites.interfaces import ISiteRepository
from ..models.site_model import SiteModel

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# ========== دوال التحويل بين Domain و ORM ==========

def _model_to_domain(model: SiteModel) -> Site:
    """
    تحويل ORM Model إلى Domain Entity
    
    Args:
        model: نموذج SQLAlchemy
    
    Returns:
        كيان Site من Domain Layer
    """
    if not model:
        return None
    
    site = Site(
        id=SiteId(model.id),
        code=SiteCode(model.code),
        name=model.name,
        site_type=SiteType(model.site_type),
        street=model.street,
        city=model.city,
        country=model.country,
        phone=model.phone,
        mobile=model.mobile,
        email=model.email,
        contact_person=model.contact_person,
        notes=model.notes,
        is_active=model.is_active,
        is_default=model.is_default,
        is_deleted=model.is_deleted,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )
    
    # ✅ إضافة الحقول الجديدة
    site.responsible_type = getattr(model, 'responsible_type', 'customer')
    site.responsible_id = getattr(model, 'responsible_id', None)
    site.responsible_name = getattr(model, 'responsible_name', None)
    site.responsible_code = getattr(model, 'responsible_code', None)
    site.currency_code = getattr(model, 'currency_code', 'USD')
    site.area_sqm = getattr(model, 'area_sqm', None)
    
    return site


def _domain_to_model(site: Site) -> SiteModel:
    """
    تحويل Domain Entity إلى ORM Model
    
    Args:
        site: كيان Site من Domain Layer
    
    Returns:
        نموذج SQLAlchemy
    """
    return SiteModel(
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
        # ✅ إضافة الحقول الجديدة
        responsible_type=getattr(site, 'responsible_type', 'customer'),
        responsible_id=getattr(site, 'responsible_id', None),
        responsible_name=getattr(site, 'responsible_name', None),
        responsible_code=getattr(site, 'responsible_code', None),
        currency_code=getattr(site, 'currency_code', 'USD'),
        area_sqm=getattr(site, 'area_sqm', None)
    )


# ========== المستودع الرئيسي ==========

class PostgresSiteRepository(ISiteRepository):
    """
    PostgreSQL implementation of ISiteRepository
    
    الميزات:
        1. Optimistic Locking عبر الـ version
        2. بحث متقدم بالكود أو الاسم أو المدينة
        3. Pagination للقوائم الكبيرة
        4. معالجة التكرارات
        5. دعم الحذف الناعم (Soft Delete)
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    # ========== العمليات الأساسية ==========
    
    def save(self, site: Site) -> None:
        """
        حفظ الموقع (جديد أو محدث) مع Optimistic Locking
        
        ✅ يستخدم UPDATE مع شرط الإصدار للتحقق من التزامن
        """
        existing = self._session.execute(
            select(SiteModel).where(SiteModel.id == site.id.value)
        ).scalar_one_or_none()
        
        if existing:
            # ✅ التحديث مع التحقق من الإصدار (Optimistic Locking)
            # نسخة الكيان قد تكون مساوية لنسخة قاعدة البيانات (تعديل مباشر)
            # أو أكبر بواحد إذا زادها أسلوب دومين (تحديث عبر طريقة كائنية)
            if existing.version != site.version and existing.version != site.version - 1:
                raise ConcurrentModificationError(
                    "Site",
                    str(site.id),
                    site.version,
                    existing.version
                )
            expected_version = existing.version
            now = utc_now()
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(SiteModel)
                .where(
                    SiteModel.id == site.id.value,
                    SiteModel.version == expected_version  # ✅ شرط التحقق
                )
                .values(
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
                    updated_at=now,
                    updated_by=site.updated_by,
                    version=new_version,
                    # ✅ إضافة الحقول الجديدة
                    responsible_type=getattr(site, 'responsible_type', 'customer'),
                    responsible_id=getattr(site, 'responsible_id', None),
                    responsible_name=getattr(site, 'responsible_name', None),
                    responsible_code=getattr(site, 'responsible_code', None),
                    currency_code=getattr(site, 'currency_code', 'USD'),
                    area_sqm=getattr(site, 'area_sqm', None)
                )
            )
            
            # ✅ التحقق: إذا لم يتم تحديث أي صف، فهذا يعني تعارض في الإصدار
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Site",
                    str(site.id),
                    site.version,
                    existing.version
                )
            
            # ✅ تحديث الكائن المحلي بالنسخة الجديدة
            site.version = new_version
            site.updated_at = now
            
        else:
            # ✅ التحقق من عدم وجود كود مكرر
            duplicate = self._session.execute(
                select(SiteModel).where(SiteModel.code == site.code.value)
            ).scalar_one_or_none()
            
            if duplicate:
                raise DuplicateSiteCodeError(site.code.value)
            
            # إنشاء موقع جديد
            model = _domain_to_model(site)
            self._session.add(model)
            self._session.flush()
            site.version = 1  # الإصدار الأولي
    
    def get_by_id(self, site_id: UUID) -> Optional[Site]:
        """
        الحصول على موقع بواسطة المعرف
        
        Args:
            site_id: معرف الموقع (UUID)
        
        Returns:
            كيان Site أو None
        """
        model = self._session.execute(
            select(SiteModel).where(SiteModel.id == site_id)
        ).scalar_one_or_none()
        
        return _model_to_domain(model) if model else None
    
    def get_by_code(self, code: SiteCode) -> Optional[Site]:
        """
        الحصول على موقع بواسطة الكود
        
        Args:
            code: كود الموقع
        
        Returns:
            كيان Site أو None
        """
        model = self._session.execute(
            select(SiteModel).where(SiteModel.code == code.value)
        ).scalar_one_or_none()
        
        return _model_to_domain(model) if model else None
    
    def get_default_site(self) -> Optional[Site]:
        """
        الحصول على الموقع الافتراضي
        
        Returns:
            كيان Site الافتراضي أو None
        """
        model = self._session.execute(
            select(SiteModel).where(
                SiteModel.is_default == True,
                SiteModel.is_active == True,
                SiteModel.is_deleted == False
            )
        ).scalar_one_or_none()
        
        return _model_to_domain(model) if model else None
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Site]:
        """
        الحصول على جميع المواقع (طريقة مبسطة)
        
        Args:
            skip: عدد العناصر لتخطيها
            limit: الحد الأقصى للنتائج
        
        Returns:
            قائمة المواقع
        """
        return self.list_all(limit=limit, offset=skip)
    
    def list_all(
        self,
        site_type: Optional[SiteType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Site]:
        """
        قائمة جميع المواقع مع خيارات التصفية
        
        Args:
            site_type: نوع الموقع (فلترة)
            include_inactive: تضمين المواقع غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            قائمة المواقع
        """
        query = select(SiteModel).where(SiteModel.is_deleted == False)
        
        if site_type:
            query = query.where(SiteModel.site_type == site_type.value)
        
        if not include_inactive:
            query = query.where(SiteModel.is_active == True)
        
        # ترتيب: المواقع الافتراضية أولاً، ثم حسب الكود
        query = query.order_by(
            SiteModel.is_default.desc(),
            SiteModel.code
        ).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def list_active(self, limit: int = 100, offset: int = 0) -> List[Site]:
        """
        قائمة المواقع النشطة فقط
        
        Args:
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            قائمة المواقع النشطة
        """
        return self.list_all(include_inactive=False, limit=limit, offset=offset)
    
    def list_by_type(
        self,
        site_type: SiteType,
        include_inactive: bool = False,
        limit: int = 100
    ) -> List[Site]:
        """
        قائمة المواقع حسب النوع
        
        Args:
            site_type: نوع الموقع
            include_inactive: تضمين المواقع غير النشطة
            limit: الحد الأقصى للنتائج
        
        Returns:
            قائمة المواقع
        """
        return self.list_all(
            site_type=site_type,
            include_inactive=include_inactive,
            limit=limit
        )
    
    # ✅ إضافة دالة جديدة للتصفية حسب المسؤول
    def list_by_responsible(
        self,
        responsible_id: str,
        responsible_type: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Site]:
        """
        قائمة المواقع حسب المسؤول (عميل أو مورد)
        
        Args:
            responsible_id: معرف المسؤول
            responsible_type: نوع المسؤول (customer, supplier)
            include_inactive: تضمين المواقع غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            قائمة المواقع
        """
        query = select(SiteModel).where(
            SiteModel.is_deleted == False,
            SiteModel.responsible_id == responsible_id
        )
        
        if responsible_type:
            query = query.where(SiteModel.responsible_type == responsible_type)
        
        if not include_inactive:
            query = query.where(SiteModel.is_active == True)
        
        query = query.order_by(SiteModel.code).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    # ✅ إضافة دالة جديدة للتصفية حسب العملة
    def list_by_currency(
        self,
        currency_code: str,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Site]:
        """
        قائمة المواقع حسب العملة
        
        Args:
            currency_code: كود العملة (USD, LBP, إلخ)
            include_inactive: تضمين المواقع غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            قائمة المواقع
        """
        query = select(SiteModel).where(
            SiteModel.is_deleted == False,
            SiteModel.currency_code == currency_code.upper()
        )
        
        if not include_inactive:
            query = query.where(SiteModel.is_active == True)
        
        query = query.order_by(SiteModel.code).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    # ========== عمليات البحث ==========
    
    def search(
        self,
        search_text: str,
        site_type: Optional[SiteType] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Site]:
        """
        البحث عن المواقع بالكود أو الاسم أو المدينة أو اسم المسؤول
        
        Args:
            search_text: نص البحث
            site_type: نوع الموقع (فلترة)
            include_inactive: تضمين المواقع غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        
        Returns:
            قائمة المواقع المطابقة للبحث
        """
        search_pattern = f"%{search_text}%"
        
        conditions = [
            SiteModel.code.ilike(search_pattern),
            SiteModel.name.ilike(search_pattern),
            SiteModel.city.ilike(search_pattern),
            SiteModel.responsible_name.ilike(search_pattern),  # ✅ إضافة البحث في اسم المسؤول
        ]
        
        query = select(SiteModel).where(
            SiteModel.is_deleted == False,
            or_(*conditions)
        )
        
        if site_type:
            query = query.where(SiteModel.site_type == site_type.value)
        
        if not include_inactive:
            query = query.where(SiteModel.is_active == True)
        
        query = query.order_by(SiteModel.code).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def search_by_code(self, code: str, limit: int = 10) -> List[Site]:
        """
        البحث عن المواقع بالكود
        
        Args:
            code: كود الموقع (بحث جزئي)
            limit: الحد الأقصى للنتائج
        
        Returns:
            قائمة المواقع
        """
        search_pattern = f"%{code}%"
        
        models = self._session.execute(
            select(SiteModel)
            .where(
                SiteModel.is_deleted == False,
                SiteModel.is_active == True,
                SiteModel.code.ilike(search_pattern)
            )
            .order_by(SiteModel.code)
            .limit(limit)
        ).scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    # ========== عمليات الحذف ==========
    
    def delete(self, site_id: UUID, permanent: bool = False) -> bool:
        """
        حذف موقع (ناعم أو دائم)
        
        Args:
            site_id: معرف الموقع
            permanent: حذف دائم (True) أم حذف ناعم (False)
        
        Returns:
            True إذا تم الحذف بنجاح
        """
        model = self._session.execute(
            select(SiteModel).where(SiteModel.id == site_id)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        if permanent:
            # حذف دائم
            self._session.delete(model)
        else:
            # حذف ناعم
            model.is_deleted = True
            model.is_active = False
            model.deleted_at = utc_now()
            model.updated_at = utc_now()
            model.version += 1
        
        return True
    
    def soft_delete(self, site_id: UUID, deleted_by: str = "system") -> bool:
        """
        حذف ناعم (تعطيل) موقع
        
        Args:
            site_id: معرف الموقع
            deleted_by: من قام بالحذف
        
        Returns:
            True إذا تم الحذف بنجاح
        """
        model = self._session.execute(
            select(SiteModel).where(SiteModel.id == site_id)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        now = utc_now()
        model.is_deleted = True
        model.is_active = False
        model.deleted_at = now
        model.deleted_by = deleted_by
        model.updated_at = now
        model.updated_by = deleted_by
        model.version += 1
        
        return True
    
    def hard_delete(self, site_id: UUID) -> bool:
        """
        حذف دائم لموقع (استخدم بحذر)
        
        Args:
            site_id: معرف الموقع
        
        Returns:
            True إذا تم الحذف بنجاح
        """
        return self.delete(site_id, permanent=True)
    
    # ========== عمليات التحقق ==========
    
    def exists_by_code(self, code: SiteCode) -> bool:
        """
        التحقق من وجود موقع بالكود
        
        Args:
            code: كود الموقع
        
        Returns:
            True إذا كان الموقع موجوداً
        """
        result = self._session.execute(
            select(SiteModel.id).where(
                SiteModel.code == code.value,
                SiteModel.is_deleted == False
            )
        ).first()
        
        return result is not None
    
    def exists_by_id(self, site_id: UUID) -> bool:
        """
        التحقق من وجود موقع بالمعرف
        
        Args:
            site_id: معرف الموقع
        
        Returns:
            True إذا كان الموقع موجوداً
        """
        result = self._session.execute(
            select(SiteModel.id).where(
                SiteModel.id == site_id,
                SiteModel.is_deleted == False
            )
        ).first()
        
        return result is not None
    
    def count(
        self,
        site_type: Optional[SiteType] = None,
        responsible_type: Optional[str] = None,
        include_inactive: bool = False
    ) -> int:
        """
        حساب عدد المواقع
        
        Args:
            site_type: نوع الموقع (فلترة)
            responsible_type: نوع المسؤول (فلترة)
            include_inactive: تضمين المواقع غير النشطة
        
        Returns:
            عدد المواقع
        """
        query = select(func.count()).select_from(SiteModel).where(
            SiteModel.is_deleted == False
        )
        
        if site_type:
            query = query.where(SiteModel.site_type == site_type.value)
        
        if responsible_type:
            query = query.where(SiteModel.responsible_type == responsible_type)
        
        if not include_inactive:
            query = query.where(SiteModel.is_active == True)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def count_active(self) -> int:
        """
        حساب عدد المواقع النشطة
        
        Returns:
            عدد المواقع النشطة
        """
        return self.count(include_inactive=False)
    
    def count_by_type(self, site_type: SiteType) -> int:
        """
        حساب عدد المواقع حسب النوع
        
        Args:
            site_type: نوع الموقع
        
        Returns:
            عدد المواقع من هذا النوع
        """
        return self.count(site_type=site_type, include_inactive=False)
    
    def count_by_currency(self, currency_code: str) -> int:
        """
        حساب عدد المواقع حسب العملة
        
        Args:
            currency_code: كود العملة
        
        Returns:
            عدد المواقع بهذه العملة
        """
        result = self._session.execute(
            select(func.count()).select_from(SiteModel).where(
                SiteModel.is_deleted == False,
                SiteModel.is_active == True,
                SiteModel.currency_code == currency_code.upper()
            )
        ).scalar()
        return result or 0
    
    def count_by_responsible_type(self, responsible_type: str) -> int:
        """
        حساب عدد المواقع حسب نوع المسؤول
        
        Args:
            responsible_type: نوع المسؤول (customer, supplier)
        
        Returns:
            عدد المواقع
        """
        return self.count(responsible_type=responsible_type, include_inactive=False)
    
    # ========== عمليات إضافية ==========
    
    def get_next_code(self, prefix: str = "S") -> str:
        """
        توليد كود موقع تلقائي
        
        الصيغة: S + 5 أرقام (مثال: S-00001, S-00002)
        
        Args:
            prefix: بادئة الكود
        
        Returns:
            كود فريد للموقع
        """
        import re
        
        result = self._session.execute(
            select(SiteModel.code)
            .where(SiteModel.code.regexp_match(f'^{prefix}[0-9]+$'))
            .order_by(SiteModel.code.desc())
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
    
    def set_as_default(self, site_id: UUID, set_by: str = "system") -> bool:
        """
        تعيين موقع كموقع افتراضي (يتم إلغاء تعيين المواقع الأخرى تلقائياً)
        
        Args:
            site_id: معرف الموقع المراد جعله افتراضياً
            set_by: من قام بالتغيير
        
        Returns:
            True إذا تم التغيير بنجاح
        """
        now = utc_now()
        
        # إلغاء تعيين جميع المواقع الأخرى
        self._session.execute(
            update(SiteModel)
            .where(SiteModel.is_default == True)
            .values(
                is_default=False,
                updated_at=now,
                updated_by=set_by,
                version=SiteModel.version + 1
            )
        )
        
        # تعيين الموقع الجديد كافتراضي
        result = self._session.execute(
            update(SiteModel)
            .where(SiteModel.id == site_id)
            .values(
                is_default=True,
                updated_at=now,
                updated_by=set_by,
                version=SiteModel.version + 1
            )
        )
        
        return result.rowcount > 0
    
    def get_statistics(self) -> dict:
        """
        الحصول على إحصائيات المواقع
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        total = self.count()
        active = self.count_active()
        inactive = total - active
        
        # إحصائيات حسب النوع
        type_stats = {}
        for site_type in SiteType:
            count = self.count_by_type(site_type)
            if count > 0:
                type_stats[site_type.value] = count
        
        # إحصائيات حسب نوع المسؤول
        responsible_stats = {
            'customer': self.count_by_responsible_type('customer'),
            'supplier': self.count_by_responsible_type('supplier'),
        }
        
        # إحصائيات حسب العملة
        currency_stats = {}
        currencies = ['USD', 'LBP', 'EUR', 'GBP']
        for currency in currencies:
            count = self.count_by_currency(currency)
            if count > 0:
                currency_stats[currency] = count
        
        # عدد المدن الفريدة
        cities_result = self._session.execute(
            select(SiteModel.city, func.count(SiteModel.id))
            .where(
                SiteModel.is_deleted == False,
                SiteModel.city.isnot(None)
            )
            .group_by(SiteModel.city)
        ).all()
        
        cities_count = len(cities_result)
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'by_type': type_stats,
            'by_responsible_type': responsible_stats,
            'by_currency': currency_stats,
            'cities_count': cities_count,
            'has_default': self.get_default_site() is not None
        }
    
    def get_all_cities(self) -> List[str]:
        """
        الحصول على قائمة بجميع المدن المستخدمة في المواقع
        
        Returns:
            قائمة المدن
        """
        results = self._session.execute(
            select(SiteModel.city)
            .where(
                SiteModel.is_deleted == False,
                SiteModel.city.isnot(None),
                SiteModel.city != ''
            )
            .distinct()
            .order_by(SiteModel.city)
        ).all()
        
        return [r[0] for r in results if r[0]]
    
    def get_sites_for_combo(
        self,
        include_inactive: bool = False,
        include_default_first: bool = True
    ) -> List[dict]:
        """
        الحصول على قائمة المواقع لعرضها في ComboBox
        
        Args:
            include_inactive: تضمين المواقع غير النشطة
            include_default_first: عرض الموقع الافتراضي أولاً
        
        Returns:
            قائمة من القواميس تحتوي على id, code, name, display_name
        """
        sites = self.list_all(include_inactive=include_inactive, limit=500)
        
        if include_default_first:
            # ترتيب: الموقع الافتراضي أولاً، ثم الباقي
            sites.sort(key=lambda x: (not x.is_default, x.code))
        
        result = []
        for site in sites:
            result.append({
                'id': str(site.id.value),
                'code': site.code.value,
                'name': site.name,
                'display_name': site.display_name,
                'city': site.city,
                'site_type': site.site_type.value,
                'responsible_name': getattr(site, 'responsible_name', None),
                'currency_code': getattr(site, 'currency_code', 'USD'),
                'is_active': site.is_active,
                'is_default': site.is_default
            })
        
        return result
    
    def get_by_ids(self, site_ids: List[UUID]) -> List[Site]:
        """
        الحصول على مواقع متعددة بواسطة المعرفات
        
        Args:
            site_ids: قائمة معرفات المواقع
        
        Returns:
            قائمة المواقع
        """
        if not site_ids:
            return []
        
        models = self._session.execute(
            select(SiteModel).where(SiteModel.id.in_(site_ids))
        ).scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def bulk_save(self, sites: List[Site]) -> int:
        """
        حفظ عدة مواقع دفعة واحدة
        
        Args:
            sites: قائمة المواقع للحفظ
        
        Returns:
            عدد المواقع المحفوظة بنجاح
        """
        saved_count = 0
        for site in sites:
            try:
                self.save(site)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving site {site.code.value}: {e}")
        
        return saved_count


# ========== Exports ==========

__all__ = [
    "PostgresSiteRepository",
]