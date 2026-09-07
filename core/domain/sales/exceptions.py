# core/domain/sales/exceptions.py
"""
Sales Domain Exceptions - استثناءات مجال المبيعات
"""

from core.shared.exceptions import BaseError


class SalesDomainException(BaseError):
    """استثناء أساسي لوحدة المبيعات"""
    pass


class QuotationNotFoundException(SalesDomainException):
    """عرض السعر غير موجود"""
    def __init__(self, quotation_id: str):
        super().__init__(f"Sales quotation not found with ID: {quotation_id}")


class QuotationExpiredError(SalesDomainException):
    """انتهت صلاحية عرض السعر"""
    def __init__(self, quotation_number: str):
        super().__init__(f"Sales quotation {quotation_number} has expired")


class InvalidQuotationStatusError(SalesDomainException):
    """حالة عرض السعر غير صالحة للعملية المطلوبة"""
    def __init__(self, current_status: str, required_status: str, operation: str):
        super().__init__(
            f"Cannot perform {operation} on quotation with status {current_status}. "
            f"Required status: {required_status}"
        )


class OrderNotFoundException(SalesDomainException):
    """أمر البيع غير موجود"""
    def __init__(self, order_id: str):
        super().__init__(f"Sales order not found with ID: {quotation_id}")


class InvalidOrderStatusError(SalesDomainException):
    """حالة أمر البيع غير صالحة للعملية المطلوبة"""
    def __init__(self, current_status: str, required_status: str, operation: str):
        super().__init__(
            f"Cannot perform {operation} on order with status {current_status}. "
            f"Required status: {required_status}"
        )


class DeliveryNotFoundException(SalesDomainException):
    """إشعار التسليم غير موجود"""
    def __init__(self, delivery_id: str):
        super().__init__(f"Delivery note not found with ID: {delivery_id}")


class InvalidDeliveryStatusError(SalesDomainException):
    """حالة إشعار التسليم غير صالحة للعملية المطلوبة"""
    def __init__(self, current_status: str, required_status: str, operation: str):
        super().__init__(
            f"Cannot perform {operation} on delivery with status {current_status}. "
            f"Required status: {required_status}"
        )


class InsufficientStockForOrderError(SalesDomainException):
    """المخزون غير كافٍ لتنفيذ أمر البيع"""
    def __init__(self, product_code: str, required_quantity: float, available_quantity: float):
        super().__init__(
            f"Insufficient stock for product {product_code}. "
            f"Required: {required_quantity}, Available: {available_quantity}"
        )


class CannotModifyCompletedOrderError(SalesDomainException):
    """لا يمكن تعديل أمر بيع مكتمل"""
    def __init__(self, order_number: str):
        super().__init__(f"Cannot modify completed order {order_number}")


class DuplicateQuotationNumberError(SalesDomainException):
    """رقم عرض السعر مكرر"""
    def __init__(self, quotation_number: str):
        super().__init__(f"Duplicate quotation number: {quotation_number}")


class DuplicateOrderNumberError(SalesDomainException):
    """رقم أمر البيع مكرر"""
    def __init__(self, order_number: str):
        super().__init__(f"Duplicate order number: {order_number}")
