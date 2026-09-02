# core/domain/products/exceptions.py (محدث)

"""
Domain Exceptions for Products Context
استثناءات مجال المنتجات - تعبر عن انتهاكات قواعد العمل
"""


class ProductError(Exception):
    """الاستثناء الأساسي لجميع أخطاء المنتجات"""
    pass


class ProductNotFoundError(ProductError):
    """يُرفع عندما لا يتم العثور على المنتج"""
    def __init__(self, product_id: str):
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


class DuplicateCodeError(ProductError):
    """يُرفع عند محاولة إنشاء منتج بكود مكرر"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Product code already exists: {code}")


class InvalidProductCodeError(ProductError):
    """يُرفع عند استخدام كود منتج غير صالح"""
    def __init__(self, code: str, reason: str = ""):
        self.code = code
        super().__init__(f"Invalid product code '{code}': {reason}" if reason else f"Invalid product code: {code}")


class InvalidStockQuantityError(ProductError):
    """يُرفع عند استخدام كمية مخزون غير صالحة"""
    def __init__(self, quantity, reason: str = ""):
        self.quantity = quantity
        super().__init__(f"Invalid stock quantity {quantity}: {reason}" if reason else f"Invalid stock quantity: {quantity}")


class NegativeStockNotAllowedError(ProductError):
    """يُرفع عند محاولة خصم كمية أكبر من المتاح (المخزون السالب غير مسموح)"""
    def __init__(self, product_code: str, current_stock, requested_quantity):
        self.product_code = product_code
        self.current_stock = current_stock
        self.requested_quantity = requested_quantity
        super().__init__(
            f"Cannot reduce stock for product '{product_code}'. "
            f"Current stock: {current_stock}, Requested reduction: {requested_quantity}"
        )


class InsufficientStockError(ProductError):
    """يُرفع عند محاولة بيع كمية أكبر من المتاحة"""
    def __init__(self, product_code: str, available: int, requested: int):
        self.product_code = product_code
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock for product '{product_code}'. "
            f"Available: {available}, Requested: {requested}"
        )


class ProductAlreadyActiveError(ProductError):
    """يُرفع عند محاولة تنشيط منتج نشط بالفعل"""
    def __init__(self, product_code: str):
        self.product_code = product_code
        super().__init__(f"Product '{product_code}' is already active")


class ProductAlreadyInactiveError(ProductError):
    """يُرفع عند محاولة تعطيل منتج غير نشط بالفعل"""
    def __init__(self, product_code: str):
        self.product_code = product_code
        super().__init__(f"Product '{product_code}' is already inactive")


class CannotModifyInactiveProductError(ProductError):
    """يُرفع عند محاولة تعديل منتج غير نشط"""
    def __init__(self, product_code: str):
        self.product_code = product_code
        super().__init__(f"Cannot modify inactive product: {product_code}")


class ConcurrentModificationError(ProductError):
    """
    يُرفع عند فشل القفل التفاؤلي (تعديل متزامن من مستخدمين مختلفين)
    
    ✅ محدث: يدعم aggregate_type للتوافق مع جميع الـ Bounded Contexts
    """
    def __init__(
        self,
        aggregate_type: str,
        aggregate_id: str,
        expected_version: int,
        actual_version: int
    ):
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"{aggregate_type} {aggregate_id} was modified concurrently. "
            f"Expected version {expected_version}, but database has version {actual_version}"
        )