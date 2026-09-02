# core/infrastructure/db/postgres/repositories_product.py (النسخة المصححة نهائياً)

"""
PostgreSQL Repository for Products
✅ محدث: Optimistic Locking حقيقي باستخدام UPDATE الشرطي
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
import re

from sqlalchemy import select, func, or_, and_, cast, String, update
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.exc import IntegrityError

from core.domain.products.entities import Product
from core.domain.products.value_objects import ProductId, ProductCode, ProductStatus, StockMovementType
from core.domain.products.exceptions import (
    ProductNotFoundError, 
    DuplicateCodeError, 
    ConcurrentModificationError
)
from core.domain.products.interfaces import IProductRepository
from core.domain.shared.value_objects import Money

from ..models.product_model import ProductModel


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# ========== دوال التحويل بين Domain و ORM ==========

def _domain_to_model(product: Product) -> ProductModel:
    """
    تحويل كيان Domain إلى ORM Model مع دعم الحقول الجديدة
    """
    return ProductModel(
        id=product.id.value,
        code=product.code.value,
        name=product.name,
        description=product.description,
        category=product.category,
        unit_price=product.unit_price.amount,
        currency=product.unit_price.currency,
        tax_rate=product.tax_rate,
        stock_quantity=Decimal(str(product.stock_quantity)),
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        version=product.version,
        # الحقول الجديدة
        barcode=getattr(product, 'barcode', None),
        base_unit=getattr(product, 'base_unit', 'قطعة (pc)'),
        min_stock=Decimal(str(getattr(product, 'min_stock', 0))),
        max_stock=Decimal(str(getattr(product, 'max_stock', 0))),
        main_location=getattr(product, 'main_location', None),
        tags=getattr(product, 'tags', []),
        weight=Decimal(str(getattr(product, 'weight', 0))),
        weight_unit=getattr(product, 'weight_unit', 'kg'),
        length=Decimal(str(getattr(product, 'length', 0))),
        width=Decimal(str(getattr(product, 'width', 0))),
        height=Decimal(str(getattr(product, 'height', 0))),
        is_featured=getattr(product, 'is_featured', False),
        allow_backorder=getattr(product, 'allow_backorder', False),
        batch_tracking=getattr(product, 'batch_tracking', False),
        low_stock_alert=getattr(product, 'low_stock_alert', True),
        purchase_price=Decimal(str(getattr(product, 'purchase_price', 0))),
        wholesale_price=Decimal(str(getattr(product, 'wholesale_price', 0))),
    )


def _model_to_domain(model: ProductModel) -> Product:
    """
    تحويل ORM Model إلى كيان Domain مع دعم الحقول الجديدة
    """
    # تحديد حالة المنتج
    if not model.is_active:
        status = ProductStatus.INACTIVE
    else:
        status = ProductStatus.ACTIVE
    
    # إنشاء المنتج
    product = Product(
        id=ProductId(model.id),
        code=ProductCode(model.code),
        name=model.name,
        unit_price=Money(model.unit_price, model.currency),
        description=model.description,
        category=model.category,
        tax_rate=model.tax_rate,
        stock_quantity=int(model.stock_quantity),
        status=status,
        created_at=model.created_at,
        created_by="",
        updated_at=model.updated_at,
        updated_by="",
        version=model.version,
    )
    
    # إضافة الحقول الإضافية
    product.barcode = model.barcode
    product.base_unit = model.base_unit
    product.min_stock = int(model.min_stock) if model.min_stock else 0
    product.max_stock = int(model.max_stock) if model.max_stock else 0
    product.main_location = model.main_location
    product.tags = model.tags or []
    product.weight = float(model.weight) if model.weight else 0
    product.weight_unit = model.weight_unit
    product.length = float(model.length) if model.length else 0
    product.width = float(model.width) if model.width else 0
    product.height = float(model.height) if model.height else 0
    product.is_featured = model.is_featured or False
    product.allow_backorder = model.allow_backorder or False
    product.batch_tracking = model.batch_tracking or False
    product.low_stock_alert = model.low_stock_alert if model.low_stock_alert is not None else True
    product.purchase_price = float(model.purchase_price) if model.purchase_price else 0
    product.wholesale_price = float(model.wholesale_price) if model.wholesale_price else 0
    
    return product


class PostgresProductRepository(IProductRepository):
    """
    تطبيق PostgreSQL لمستودع المنتجات
    ✅ محدث: Optimistic Locking حقيقي باستخدام UPDATE الشرطي
    """
    
    def __init__(self, session: Session):
        self._session = session
        self._model_class = ProductModel
    
    # ========== العمليات الأساسية ==========
    
    def save(self, product: Product) -> None:
        """
        حفظ المنتج (جديد أو محدث)
        ✅ Optimistic Locking حقيقي: UPDATE مع شرط الإصدار
        """
        existing = self._session.execute(
            select(ProductModel).where(ProductModel.id == product.id.value)
        ).scalar_one_or_none()
        
        if existing:
            # ✅ الطريقة الصحيحة: UPDATE مع شرط الإصدار
            # هذا يضمن atomicity ويمنع race conditions
            
            now = utc_now()
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(ProductModel)
                .where(
                    ProductModel.id == product.id.value,
                    ProductModel.version == product.version  # الشرط الأساسي
                )
                .values(
                    code=product.code.value,
                    name=product.name,
                    description=product.description,
                    category=product.category,
                    unit_price=product.unit_price.amount,
                    currency=product.unit_price.currency,
                    tax_rate=product.tax_rate,
                    stock_quantity=Decimal(str(product.stock_quantity)),
                    is_active=product.is_active,
                    updated_at=now,
                    version=new_version,
                    # الحقول الجديدة
                    barcode=getattr(product, 'barcode', None),
                    base_unit=getattr(product, 'base_unit', 'قطعة (pc)'),
                    min_stock=Decimal(str(getattr(product, 'min_stock', 0))),
                    max_stock=Decimal(str(getattr(product, 'max_stock', 0))),
                    main_location=getattr(product, 'main_location', None),
                    tags=getattr(product, 'tags', []),
                    weight=Decimal(str(getattr(product, 'weight', 0))),
                    weight_unit=getattr(product, 'weight_unit', 'kg'),
                    length=Decimal(str(getattr(product, 'length', 0))),
                    width=Decimal(str(getattr(product, 'width', 0))),
                    height=Decimal(str(getattr(product, 'height', 0))),
                    is_featured=getattr(product, 'is_featured', False),
                    allow_backorder=getattr(product, 'allow_backorder', False),
                    batch_tracking=getattr(product, 'batch_tracking', False),
                    low_stock_alert=getattr(product, 'low_stock_alert', True),
                    purchase_price=Decimal(str(getattr(product, 'purchase_price', 0))),
                    wholesale_price=Decimal(str(getattr(product, 'wholesale_price', 0))),
                )
            )
            
            # ✅ التحقق: إذا لم يتم تحديث أي صف، فهذا يعني تعارض في الإصدار
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Product",
                    str(product.id),
                    product.version,
                    existing.version
                )
            
            # تحديث الإصدار في الكائن المحلي
            product.version = new_version
            
        else:
            # التحقق من عدم وجود كود مكرر
            duplicate = self._session.execute(
                select(ProductModel).where(ProductModel.code == product.code.value)
            ).scalar_one_or_none()
            
            if duplicate:
                raise DuplicateCodeError(product.code.value)
            
            # التحقق من عدم وجود باركود مكرر (إذا تم توفيره)
            barcode = getattr(product, 'barcode', None)
            if barcode:
                duplicate_barcode = self._session.execute(
                    select(ProductModel).where(ProductModel.barcode == barcode)
                ).scalar_one_or_none()
                
                if duplicate_barcode:
                    raise DuplicateCodeError(f"الباركود {barcode} موجود مسبقاً")
            
            # إنشاء منتج جديد
            model = _domain_to_model(product)
            self._session.add(model)
            self._session.flush()
            product.version = 1  # الإصدار الأولي
    
    # ========== باقي الدوال بدون تغيير (get_by_id, get_by_code, etc.) ==========
    
    def get_by_id(self, product_id: ProductId) -> Optional[Product]:
        """الحصول على منتج بواسطة المعرف"""
        model = self._session.execute(
            select(ProductModel).where(ProductModel.id == product_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_code(self, code: ProductCode) -> Optional[Product]:
        """الحصول على منتج بواسطة الكود"""
        model = self._session.execute(
            select(ProductModel).where(ProductModel.code == code.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """الحصول على منتج بواسطة الباركود"""
        model = self._session.execute(
            select(ProductModel).where(ProductModel.barcode == barcode)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_ids(self, product_ids: List[ProductId]) -> List[Product]:
        """الحصول على منتجات متعددة بواسطة المعرفات"""
        ids = [pid.value for pid in product_ids]
        models = self._session.execute(
            select(ProductModel).where(ProductModel.id.in_(ids))
        ).scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    # ========== عمليات القوائم والفلترة ==========
    
    def list_all(
        self,
        include_inactive: bool = False,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        unit: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Product]:
        """قائمة جميع المنتجات مع خيارات التصفية والترقيم المتقدمة"""
        query = select(ProductModel)
        
        if not include_inactive:
            query = query.where(ProductModel.is_active == True)
        
        if category:
            query = query.where(ProductModel.category == category)
        
        if tag:
            query = query.where(ProductModel.tags.contains([tag]))
        
        if unit:
            query = query.where(ProductModel.base_unit == unit)
        
        if min_price is not None:
            query = query.where(ProductModel.unit_price >= min_price)
        
        if max_price is not None:
            query = query.where(ProductModel.unit_price <= max_price)
        
        query = query.order_by(ProductModel.code).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def list_active(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """قائمة المنتجات النشطة فقط"""
        return self.list_all(include_inactive=False, limit=limit, offset=offset)
    
    def list_by_category(self, category: str, limit: int = 100) -> List[Product]:
        """قائمة المنتجات حسب التصنيف"""
        return self.list_all(category=category, limit=limit)
    
    def list_by_tag(self, tag: str, limit: int = 100) -> List[Product]:
        """قائمة المنتجات حسب العلامة"""
        return self.list_all(tag=tag, limit=limit)
    
    def list_by_unit(self, unit: str, limit: int = 100) -> List[Product]:
        """قائمة المنتجات حسب وحدة القياس"""
        return self.list_all(unit=unit, limit=limit)
    
    def list_by_status(self, status: ProductStatus, limit: int = 100) -> List[Product]:
        """قائمة المنتجات حسب الحالة"""
        is_active = (status == ProductStatus.ACTIVE)
        return self.list_all(include_inactive=not is_active, limit=limit)
    
    def list_featured(self, limit: int = 100) -> List[Product]:
        """قائمة المنتجات المميزة"""
        query = select(ProductModel).where(
            and_(
                ProductModel.is_active == True,
                ProductModel.is_featured == True
            )
        ).order_by(ProductModel.name).limit(limit)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    # ========== عمليات المخزون ==========
    
    def get_low_stock(self, threshold: Optional[int] = None, limit: int = 100) -> List[Product]:
        """قائمة المنتجات ذات المخزون المنخفض"""
        if threshold is None:
            threshold = 10
        
        query = select(ProductModel).where(
            and_(
                ProductModel.is_active == True,
                ProductModel.stock_quantity > 0,
                ProductModel.stock_quantity <= threshold
            )
        ).order_by(ProductModel.stock_quantity).limit(limit)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def get_low_stock_by_min_stock(self, limit: int = 100) -> List[Product]:
        """قائمة المنتجات التي وصلت لحد الطلب"""
        query = select(ProductModel).where(
            and_(
                ProductModel.is_active == True,
                ProductModel.min_stock > 0,
                ProductModel.stock_quantity <= ProductModel.min_stock
            )
        ).order_by(ProductModel.stock_quantity).limit(limit)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def get_out_of_stock(self, limit: int = 100) -> List[Product]:
        """قائمة المنتجات التي نفد مخزونها"""
        query = select(ProductModel).where(
            and_(
                ProductModel.is_active == True,
                ProductModel.stock_quantity <= 0
            )
        ).order_by(ProductModel.code).limit(limit)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def get_overstock(self, threshold: int = 1000, limit: int = 100) -> List[Product]:
        """قائمة المنتجات ذات المخزون الزائد عن الحد"""
        query = select(ProductModel).where(
            and_(
                ProductModel.is_active == True,
                ProductModel.max_stock > 0,
                ProductModel.stock_quantity >= ProductModel.max_stock
            )
        ).order_by(ProductModel.stock_quantity.desc()).limit(limit)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    # ========== عمليات البحث ==========
    
    def search(
        self,
        search_text: str,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """البحث عن المنتجات بالكود أو الاسم أو الوصف أو الباركود أو العلامات"""
        search_pattern = f"%{search_text}%"
        
        conditions = [
            ProductModel.code.ilike(search_pattern),
            ProductModel.name.ilike(search_pattern),
            ProductModel.description.ilike(search_pattern),
            ProductModel.barcode.ilike(search_pattern),
        ]
        
        query = select(ProductModel).where(or_(*conditions))
        
        if not include_inactive:
            query = query.where(ProductModel.is_active == True)
        
        if category:
            query = query.where(ProductModel.category == category)
        
        if tag:
            query = query.where(ProductModel.tags.contains([tag]))
        
        query = query.order_by(ProductModel.code).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def search_by_barcode(self, barcode: str) -> Optional[Product]:
        """البحث عن منتج بالباركود"""
        model = self._session.execute(
            select(ProductModel).where(ProductModel.barcode == barcode)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    # ========== عمليات التصنيفات والعلامات ==========
    
    def get_all_categories(self) -> List[str]:
        """الحصول على قائمة بجميع التصنيفات المستخدمة"""
        results = self._session.execute(
            select(ProductModel.category)
            .where(ProductModel.category.isnot(None))
            .distinct()
            .order_by(ProductModel.category)
        ).all()
        
        return [r[0] for r in results if r[0]]
    
    def get_all_tags(self) -> List[str]:
        """الحصول على قائمة بجميع العلامات المستخدمة"""
        results = self._session.execute(
            select(func.unnest(ProductModel.tags)).distinct()
        ).all()
        
        return sorted([r[0] for r in results if r[0]])
    
    def get_all_units(self) -> List[str]:
        """الحصول على قائمة بجميع وحدات القياس المستخدمة"""
        results = self._session.execute(
            select(ProductModel.base_unit)
            .where(ProductModel.base_unit.isnot(None))
            .distinct()
            .order_by(ProductModel.base_unit)
        ).all()
        
        return [r[0] for r in results if r[0]]
    
    # ========== عمليات الإحصائيات ==========
    
    def count_all(self, include_inactive: bool = False, category: Optional[str] = None) -> int:
        """حساب عدد المنتجات"""
        query = select(func.count()).select_from(ProductModel)
        
        if not include_inactive:
            query = query.where(ProductModel.is_active == True)
        
        if category:
            query = query.where(ProductModel.category == category)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def count_by_category(self) -> Dict[str, int]:
        """حساب عدد المنتجات لكل تصنيف"""
        results = self._session.execute(
            select(ProductModel.category, func.count())
            .where(ProductModel.category.isnot(None))
            .group_by(ProductModel.category)
        ).all()
        
        return {r[0]: r[1] for r in results}
    
    def count_by_status(self) -> Dict[str, int]:
        """حساب عدد المنتجات حسب الحالة"""
        active_count = self._session.execute(
            select(func.count()).where(ProductModel.is_active == True)
        ).scalar() or 0
        
        inactive_count = self._session.execute(
            select(func.count()).where(ProductModel.is_active == False)
        ).scalar() or 0
        
        return {'active': active_count, 'inactive': inactive_count}
    
    def get_total_stock_value(self, currency: str = "USD") -> float:
        """حساب القيمة الإجمالية للمخزون"""
        result = self._session.execute(
            select(func.sum(ProductModel.stock_quantity * ProductModel.unit_price))
            .where(ProductModel.is_active == True)
            .where(ProductModel.currency == currency)
        ).scalar()
        
        return float(result) if result else 0
    
    # ========== عمليات التحقق ==========
    
    def exists_by_code(self, code: ProductCode) -> bool:
        """التحقق من وجود منتج بكود معين"""
        result = self._session.execute(
            select(ProductModel.id).where(ProductModel.code == code.value)
        ).first()
        
        return result is not None
    
    def exists_by_barcode(self, barcode: str) -> bool:
        """التحقق من وجود منتج بباركود معين"""
        if not barcode:
            return False
        
        result = self._session.execute(
            select(ProductModel.id).where(ProductModel.barcode == barcode)
        ).first()
        
        return result is not None
    
    # ========== عمليات الحذف ==========
    
    def delete(self, product_id: ProductId) -> bool:
        """حذف منتج (حذف فعلي - استخدم بحذر)"""
        model = self._session.execute(
            select(ProductModel).where(ProductModel.id == product_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        self._session.delete(model)
        return True
    
    def soft_delete(self, product_id: ProductId) -> bool:
        """حذف ناعم (تعطيل فقط)"""
        model = self._session.execute(
            select(ProductModel).where(ProductModel.id == product_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        model.is_active = False
        model.updated_at = utc_now()
        model.version += 1
        
        return True
    
    # ========== عمليات توليد الأكواد ==========
    
    def get_next_code(self, prefix: str = "P") -> str:
        """توليد كود منتج تلقائي"""
        result = self._session.execute(
            select(ProductModel.code)
            .where(ProductModel.code.regexp_match(f'^{prefix}[0-9]+$'))
            .order_by(ProductModel.code.desc())
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
    
    def get_next_barcode(self) -> str:
        """توليد باركود فريد"""
        import random
        import string
        
        while True:
            barcode = ''.join(random.choices(string.digits, k=13))
            if not self.exists_by_barcode(barcode):
                return barcode