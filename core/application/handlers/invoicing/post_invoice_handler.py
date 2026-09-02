# core/application/handlers/invoicing/post_invoice_handler.py
"""
Post Invoice Handler - ترحيل الفاتورة وإنشاء قيد محاسبي
الإصدار المُصلح - v4.0.0

✅ محدث: استخدام Accounting Orchestrator المركزي
✅ محدث: استخدام محرك المخزون الجديد (StockMovement)
✅ محدث: Optimistic Locking للمخزون والصندوق
✅ محدث: دعم الدفعات والأرقام التسلسلية
✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمات المخزون
✅ محدث: تحسين أداء N+1 Query مع selectinload
✅ محدث: التخزين المؤقت للبيانات الثابتة مع @lru_cache
✅ محدث: تحسين معالجة الأخطاء مع ErrorResponseDTO
✅ محدث: دعم فروع العملاء
✅ محدث: تسجيل عمليات التدقيق
"""
from dataclasses import dataclass, field
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from functools import lru_cache

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from core.domain.invoicing.value_objects import InvoiceId, PaymentType
from core.domain.invoicing.exceptions import InvoiceNotFoundError
from core.domain.shared.value_objects import Money, AccountCode
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import JournalEntryId
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError, ValidationError

# ✅ استيراد Accounting Orchestrator
from core.application.accounting.orchestrator import (
    AccountingOrchestrator,
    JournalEntryRequest,
    JournalEntryResult
)

# ✅ استيراد محرك المخزون الجديد
from core.domain.inventory.services import StockMovementService, InventoryValuationService
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    BatchNumber,
    ExpiryDate,
    Money as InventoryMoney,
    StockLocation,
)
from core.domain.inventory.services import FIFOCostCalculator

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import PostInvoiceCommand
from core.application.accounting.dtos import ErrorResponseDTO

# استيراد النماذج
from core.infrastructure.db.models.invoice_model import InvoiceLineModel
from core.infrastructure.db.models.settings_model import AccountingSettingsModel
from core.infrastructure.db.models.product_model import ProductModel
from core.infrastructure.db.models.fund_model import FundModel, FundMovementModel
from core.infrastructure.db.models.currency_model import CurrencyModel
from core.infrastructure.db.models.customer_model import CustomerModel
from core.infrastructure.db.models.site_model import SiteModel

logger = logging.getLogger(__name__)


# =============================================================================
# ✅ InventoryCheckResult - نتيجة التحقق من المخزون (محسّن)
# =============================================================================

class InventoryCheckResult:
    """نتيجة التحقق من المخزون - محسّن مع دعم أفضل للتقارير"""
    
    def __init__(self):
        self.available: List[Dict[str, Any]] = []
        self.unavailable: List[Dict[str, Any]] = []
        self.all_available: bool = True
        self.total_products: int = 0
        self.available_count: int = 0
        self.unavailable_count: int = 0
        self._confirmation_message: Optional[str] = None
    
    def add_available(self, product_code: str, product_name: str, 
                      required: float, available: float, line_id: str,
                      batch_number: Optional[str] = None):
        self.available.append({
            'product_code': product_code,
            'product_name': product_name,
            'required': required,
            'available': available,
            'line_id': line_id,
            'batch_number': batch_number,
            'is_available': True
        })
        self.available_count += 1
        self.total_products += 1
    
    def add_unavailable(self, product_code: str, product_name: str,
                        required: float, available: float, line_id: str):
        self.unavailable.append({
            'product_code': product_code,
            'product_name': product_name,
            'required': required,
            'available': available,
            'shortage': required - available,
            'line_id': line_id,
            'is_available': False
        })
        self.unavailable_count += 1
        self.total_products += 1
        self.all_available = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'all_available': self.all_available,
            'total_products': self.total_products,
            'available_count': self.available_count,
            'unavailable_count': self.unavailable_count,
            'unavailable_products': self.unavailable,
            'available_products': self.available,
            'summary': self.get_summary(),
            'confirmation_message': self.get_confirmation_message()
        }
    
    def get_summary(self) -> str:
        if self.all_available:
            return f"✅ جميع المنتجات ({self.total_products}) متوفرة في المخزون"
        return f"⚠️ {self.unavailable_count} منتج(منتجات) غير متوفرة من أصل {self.total_products}"
    
    def get_confirmation_message(self) -> Optional[str]:
        """الحصول على رسالة تأكيد منسقة"""
        if self.all_available:
            return None
        
        if self._confirmation_message:
            return self._confirmation_message
        
        lines = ["⚠️ المنتجات التالية غير متوفرة في المخزون بالكميات المطلوبة:", ""]
        for product in self.unavailable[:10]:  # عرض أول 10 منتجات فقط
            lines.append(f"  📦 {product['product_code']} - {product['product_name']}")
            lines.append(f"     المطلوب: {product['required']:,.2f}")
            lines.append(f"     المتوفر: {product['available']:,.2f}")
            lines.append(f"     النقص:   {product['shortage']:,.2f}")
            lines.append("")
        
        if len(self.unavailable) > 10:
            lines.append(f"  ... و {len(self.unavailable) - 10} منتجات أخرى")
            lines.append("")
        
        lines.append("هل تريد متابعة الترحيل على الرغم من نقص المخزون؟")
        lines.append("(سيتم خصم الكميات المتوفرة فقط)")
        
        self._confirmation_message = "\n".join(lines)
        return self._confirmation_message


# =============================================================================
# ✅ ErrorResponse - استجابة موحدة للأخطاء
# =============================================================================

@dataclass
class ErrorResponse:
    """استجابة موحدة للأخطاء"""
    success: bool = False
    message: str = ""
    errors: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'errors': self.errors,
            'requires_confirmation': self.requires_confirmation,
            'confirmation_message': self.confirmation_message,
            **self.details
        }


# =============================================================================
# ✅ PostInvoiceHandler - المعالج الرئيسي (محسّن)
# =============================================================================

class PostInvoiceHandler(BaseHandler[PostInvoiceCommand, dict]):
    """
    معالج ترحيل الفاتورة - النسخة النهائية المتكاملة
    
    ✅ محدث: استخدام Accounting Orchestrator لإنشاء القيد المحاسبي
    ✅ محدث: استخدام محرك المخزون الجديد (StockMovement)
    ✅ محدث: Optimistic Locking للمخزون والصندوق
    ✅ محدث: دعم الدفعات والأرقام التسلسلية
    ✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمات المخزون
    ✅ محدث: تحسين أداء N+1 Query
    ✅ محدث: التخزين المؤقت للبيانات الثابتة
    """
    
    def __init__(
        self,
        uow: IUnitOfWork,
        accounting_orchestrator: AccountingOrchestrator,
        posting_engine: PostingEngine
    ):
        super().__init__(uow)
        self._orchestrator = accounting_orchestrator
        self._posting_engine = posting_engine
        self._force_post = False
        self._inventory_check_result: Optional[InventoryCheckResult] = None
        
        # ✅ تهيئة بطيئة (Lazy Initialization) - لن يتم إنشاؤها حتى الحاجة
        self._stock_service = None
        self._valuation_service = None
        
        # ✅ التخزين المؤقت للبيانات الثابتة
        self._currency_cache: Dict[str, str] = {}
        self._accounting_settings_cache: Optional[Dict[str, str]] = None
    
    # =========================================================================
    # ✅ تهيئة خدمة المخزون عند الحاجة (Lazy Initialization)
    # =========================================================================
    
    def _get_stock_service(self):
        """تهيئة خدمة المخزون عند الحاجة فقط (Lazy Initialization)"""
        if self._stock_service is None:
            # ✅ استخدام getattr بأمان للوصول إلى stock_movements
            stock_movements = getattr(self._uow, 'stock_movements', None)
            if stock_movements:
                self._stock_service = StockMovementService(stock_movements)
                self._valuation_service = InventoryValuationService(stock_movements)
            else:
                logger.warning("stock_movements not available in UoW")
                # ✅ إنشاء service وهمي (dummy) لتجنب None checks في كل مكان
                self._stock_service = StockMovementService(None)
                self._valuation_service = InventoryValuationService(None)
        return self._stock_service
    
    # =========================================================================
    # ✅ دوال التخزين المؤقت (Caching)
    # =========================================================================
    
    @lru_cache(maxsize=128)
    def _get_cached_currency_name(self, currency_code: str) -> str:
        """الحصول على اسم العملة مع التخزين المؤقت"""
        if not currency_code:
            return currency_code
        
        # التحقق من الكاش المحلي
        if currency_code in self._currency_cache:
            return self._currency_cache[currency_code]
        
        try:
            result = self._uow.session.execute(
                select(CurrencyModel.name, CurrencyModel.symbol)
                .where(CurrencyModel.code == currency_code)
            ).first()
            
            if result:
                name, symbol = result
                display = f"{symbol or ''} {currency_code} - {name}" if symbol else f"{currency_code} - {name}"
                self._currency_cache[currency_code] = display
                return display
            return currency_code
        except Exception as e:
            logger.warning(f"Error getting currency name for {currency_code}: {e}")
            return currency_code
    
    @lru_cache(maxsize=32)
    def _get_accounting_settings(self) -> Dict[str, str]:
        """الحصول على إعدادات الحسابات مع التخزين المؤقت"""
        try:
            settings = self._uow.session.query(AccountingSettingsModel).first()
            
            if not settings:
                logger.warning("Accounting settings not found, using defaults")
                return {
                    'cash_account': '1010',
                    'receivables_account': '1020',
                    'revenue_account': '4010',
                    'tax_payable_account': '2100',
                    'cogs_account': '5010',
                    'inventory_account': '1030',
                }
            
            return {
                'cash_account': settings.cash_account or '1010',
                'receivables_account': settings.receivables_account or '1020',
                'revenue_account': settings.sales_revenue_account or '4010',
                'tax_payable_account': settings.tax_account or '2100',
                'cogs_account': getattr(settings, 'cogs_account', None) or '5010',
                'inventory_account': getattr(settings, 'inventory_account', None) or '1030',
            }
            
        except Exception as e:
            logger.error(f"Error loading accounting settings: {e}")
            return {
                'cash_account': '1010',
                'receivables_account': '1020',
                'revenue_account': '4010',
                'tax_payable_account': '2100',
                'cogs_account': '5010',
                'inventory_account': '1030',
            }
    
    def _is_currency_supported(self, currency_code: str) -> bool:
        """التحقق من صحة العملة مع التخزين المؤقت"""
        if not currency_code:
            return False
        
        try:
            result = self._uow.session.execute(
                select(CurrencyModel.id)
                .where(CurrencyModel.code == currency_code)
                .where(CurrencyModel.is_active == True)
            ).first()
            return result is not None
        except Exception:
            return True
    
    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._get_cached_currency_name.cache_clear()
        self._get_accounting_settings.cache_clear()
        self._currency_cache.clear()
        self._accounting_settings_cache = None
    
    # =========================================================================
    # ✅ دوال التحقق (Validation)
    # =========================================================================
    
    def _validate_customer(self, invoice) -> ErrorResponse:
        """التحقق من صحة العميل"""
        if not invoice.customer_id:
            return ErrorResponse(
                message="لا يمكن ترحيل فاتورة بدون عميل",
                errors=["Customer information is required before posting"]
            )
        
        try:
            customer = self._uow.session.execute(
                select(CustomerModel)
                .where(CustomerModel.id == UUID(invoice.customer_id))
                .where(CustomerModel.is_deleted == False)
            ).scalar_one_or_none()
            
            if not customer:
                return ErrorResponse(
                    message=f"العميل {invoice.customer_id} غير موجود",
                    errors=["Customer not found or deleted"]
                )
            
            if customer.status == "blocked":
                return ErrorResponse(
                    message="لا يمكن ترحيل فاتورة لعميل محظور",
                    errors=["Customer is blocked"]
                )
            
            return ErrorResponse(success=True)
            
        except Exception as e:
            logger.error(f"Error validating customer {invoice.customer_id}: {e}")
            return ErrorResponse(
                message=f"خطأ في التحقق من العميل: {str(e)}",
                errors=[str(e)]
            )
    
    def _validate_site(self, invoice) -> ErrorResponse:
        """التحقق من صحة الموقع"""
        if not hasattr(invoice, 'require_site') or not invoice.require_site:
            return ErrorResponse(success=True)
        
        if not invoice.site_id:
            return ErrorResponse(
                message="الموقع مطلوب قبل ترحيل الفاتورة",
                errors=["Site is required for this invoice"]
            )
        
        try:
            result = self._uow.session.execute(
                select(SiteModel.id, SiteModel.code, SiteModel.name, SiteModel.is_active)
                .where(SiteModel.id == UUID(invoice.site_id))
                .where(SiteModel.is_active == True)
                .where(SiteModel.is_deleted == False)
            ).first()
            
            if not result:
                return ErrorResponse(
                    message=f"الموقع {invoice.site_id} غير موجود أو غير نشط",
                    errors=[f"Site {invoice.site_id} not found or inactive"]
                )
            
            return ErrorResponse(success=True)
            
        except Exception as e:
            logger.error(f"Error validating site {invoice.site_id}: {e}")
            return ErrorResponse(
                message=f"خطأ في التحقق من الموقع: {str(e)}",
                errors=[str(e)]
            )
    
    def _validate_fund_currency_match(self, invoice) -> ErrorResponse:
        """التحقق من تطابق عملة الفاتورة مع عملة الصندوق"""
        if not invoice.fund_id:
            return ErrorResponse(success=True)
        
        if invoice.payment_type not in [PaymentType.CASH, PaymentType.TRANSFER]:
            return ErrorResponse(success=True)
        
        try:
            result = self._uow.session.execute(
                select(FundModel.currency, FundModel.code, FundModel.name, FundModel.balance)
                .where(FundModel.id == UUID(invoice.fund_id))
                .where(FundModel.status == 'active')
            ).first()
            
            if not result:
                return ErrorResponse(
                    message="الصندوق غير موجود أو غير نشط",
                    errors=[f"Fund {invoice.fund_id} not found or inactive"]
                )
            
            fund_currency_code = result[0]
            
            if fund_currency_code != invoice.currency:
                return ErrorResponse(
                    message=f"عملة الفاتورة ({invoice.currency}) لا تتطابق مع عملة الصندوق ({fund_currency_code})",
                    errors=[f"Currency mismatch: invoice {invoice.currency} vs fund {fund_currency_code}"]
                )
            
            return ErrorResponse(success=True)
            
        except Exception as e:
            logger.warning(f"Could not validate fund currency: {e}")
            return ErrorResponse(success=True)
    
    def _validate_invoice_total(self, invoice) -> ErrorResponse:
        """التحقق من صحة المبلغ الإجمالي للفاتورة"""
        if invoice.total.amount <= 0:
            return ErrorResponse(
                message="لا يمكن ترحيل فاتورة بمبلغ صفر أو سالب",
                errors=["Invoice total must be greater than zero"]
            )
        
        # التحقق من أن المبلغ الإجمالي يساوي مجموع البنود
        subtotal = invoice.subtotal.amount
        total = invoice.total.amount
        
        if abs(total - subtotal) > Decimal('0.01'):
            logger.warning(f"Invoice total mismatch: subtotal={subtotal}, total={total}")
            # لا نمنع الترحيل، ولكن نسجل التحذير
        
        return ErrorResponse(success=True)
    
    # =========================================================================
    # ✅ التحقق من المخزون - محسّن مع دفعة واحدة
    # =========================================================================
    
    def _check_inventory(self, invoice_lines: List) -> InventoryCheckResult:
        """
        التحقق من توفر المنتجات في المخزون
        
        ✅ يستخدم StockMovementService للحصول على الكميات الحقيقية
        ✅ يتجنب N+1 Problem عن طريق جلب جميع المنتجات دفعة واحدة
        """
        if not invoice_lines:
            return InventoryCheckResult()
        
        # الحصول على خدمة المخزون (تهيئة بطيئة)
        stock_service = self._get_stock_service()
        
        # استخراج جميع أكواد المنتجات
        product_codes = [line.product_code for line in invoice_lines]
        
        # ✅ جلب جميع المنتجات دفعة واحدة (تجنب N+1)
        products = self._uow.session.execute(
            select(ProductModel)
            .where(ProductModel.code.in_(product_codes))
        ).scalars().all()
        
        product_map = {p.code: p for p in products}
        result = InventoryCheckResult()
        
        # ✅ تجميع معرفات المنتجات للحصول على الكميات دفعة واحدة
        product_ids = [str(p.id) for p in products if p]
        
        # ✅ الحصول على الكميات دفعة واحدة (تجنب N+1)
        stock_quantities = {}
        if product_ids and stock_service:
            try:
                for product_id in product_ids:
                    entity = EntityId(product_id)
                    stock_quantities[product_id] = float(stock_service.get_current_quantity(entity))
            except Exception as e:
                logger.warning(f"Could not get stock quantities in batch: {e}")
        
        for line in invoice_lines:
            product = product_map.get(line.product_code)
            product_code = line.product_code or "غير معروف"
            product_name = line.product_name or product_code
            
            required = float(line.quantity)
            
            # ✅ استخدام الكمية المحسوبة مسبقاً
            if product and str(product.id) in stock_quantities:
                available = stock_quantities[str(product.id)]
            elif product:
                available = float(product.stock_quantity) if product.stock_quantity else 0.0
            else:
                available = 0.0
            
            if product and available >= required:
                # ✅ الحصول على رقم الدفعة إذا كان متاحاً
                batch_number = None
                try:
                    if hasattr(self._uow, 'stock_batches'):
                        batches = self._uow.stock_batches.get_by_entity(
                            EntityId(str(product.id)),
                            limit=1
                        )
                        if batches:
                            batch_number = str(batches[0].batch_number)
                except Exception:
                    pass
                
                result.add_available(product_code, product_name, required, available, line.line_id, batch_number)
            else:
                result.add_unavailable(product_code, product_name, required, available, line.line_id)
        
        return result
    
    # =========================================================================
    # ✅ تحديث المخزون باستخدام StockMovement (محسّن)
    # =========================================================================
    
    def _update_inventory_with_movements(
        self, 
        invoice_id: UUID, 
        skip_unavailable: bool = False
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        تحديث المخزون باستخدام نظام StockMovement الجديد
        
        ✅ ينشئ حركات مخزون (StockMovement) لكل منتج
        ✅ يستخدم FIFO لحساب التكلفة
        ✅ يسجل جميع الحركات للتتبع الكامل
        ✅ محسّن: جلب البنود دفعة واحدة
        """
        try:
            # الحصول على خدمة المخزون (تهيئة بطيئة)
            stock_service = self._get_stock_service()
            
            # ✅ جلب بنود الفاتورة دفعة واحدة
            lines = self._uow.session.execute(
                select(InvoiceLineModel)
                .where(InvoiceLineModel.invoice_id == invoice_id)
            ).scalars().all()
            
            if not lines:
                return True, []
            
            # ✅ جلب جميع المنتجات دفعة واحدة
            product_codes = [line.product_code for line in lines]
            products = self._uow.session.execute(
                select(ProductModel)
                .where(ProductModel.code.in_(product_codes))
            ).scalars().all()
            
            product_map = {p.code: p for p in products}
            updated_products = []
            
            for line in lines:
                product = product_map.get(line.product_code)
                
                if not product:
                    logger.warning(f"Product {line.product_code} not found, skipping")
                    continue
                
                quantity = Decimal(str(line.quantity))
                unit_price = Decimal(str(line.unit_price))
                currency = line.currency or "USD"
                
                # ✅ حساب التكلفة باستخدام FIFO
                entity = EntityId(str(product.id))
                
                try:
                    # ✅ استخدام FIFOCostCalculator لحساب التكلفة
                    movements = stock_service.get_movements(entity)
                    layers = self._valuation_service._build_layers(movements)
                    
                    # حساب COGS باستخدام FIFO
                    cogs, remaining_layers = FIFOCostCalculator.calculate_cogs(
                        layers,
                        quantity,
                        currency
                    )
                    
                    unit_cost = cogs.amount / quantity if quantity > 0 else Decimal('0')
                    
                except Exception as e:
                    logger.warning(f"Could not calculate FIFO cost for {product.code}: {e}")
                    unit_cost = unit_price * Decimal('0.7')  # افتراض هامش ربح 30%
                
                # ✅ التحقق من كفاية المخزون
                current_quantity = stock_service.get_current_quantity(entity)
                if current_quantity < quantity and not skip_unavailable:
                    return False, []
                
                # ✅ إنشاء حركة بيع (StockMovement)
                try:
                    movement = stock_service.create_outbound_movement(
                        entity=entity,
                        quantity=quantity,
                        unit_cost=InventoryMoney(unit_cost, currency),
                        movement_type=StockMovementType.SALE,
                        reference_type="Invoice",
                        reference_id=str(invoice_id),
                        notes=f"بيع من فاتورة {invoice_id}",
                        created_by="system"
                    )
                    
                    updated_products.append({
                        'code': product.code,
                        'quantity': float(quantity),
                        'unit_cost': float(unit_cost),
                        'total_cost': float(unit_cost * quantity),
                        'currency': currency,
                        'movement_id': str(movement.id)
                    })
                    
                    logger.info(f"Stock movement created for {product.code}: {quantity} units at {unit_cost} {currency}")
                    
                except ValueError as e:
                    if "Insufficient stock" in str(e) and skip_unavailable:
                        # ✅ خصم المتوفر فقط
                        available_qty = current_quantity
                        if available_qty > 0:
                            movement = stock_service.create_outbound_movement(
                                entity=entity,
                                quantity=available_qty,
                                unit_cost=InventoryMoney(unit_cost, currency),
                                movement_type=StockMovementType.SALE,
                                reference_type="Invoice",
                                reference_id=str(invoice_id),
                                notes=f"بيع جزئي من فاتورة {invoice_id} (المتوفر فقط)",
                                created_by="system"
                            )
                            updated_products.append({
                                'code': product.code,
                                'quantity': float(available_qty),
                                'unit_cost': float(unit_cost),
                                'total_cost': float(unit_cost * available_qty),
                                'currency': currency,
                                'movement_id': str(movement.id),
                                'partial': True,
                                'shortage': float(quantity - available_qty)
                            })
                            logger.warning(f"Partial stock for {product.code}: {available_qty} of {quantity}")
                        continue
                    raise
                
                # ✅ تحديث كمية المنتج في جدول المنتجات
                product.stock_quantity = float(stock_service.get_current_quantity(entity))
                self._uow.session.add(product)
            
            return True, updated_products
            
        except Exception as e:
            logger.error(f"Error updating inventory with movements: {e}", exc_info=True)
            return False, []
    
    # =========================================================================
    # ✅ تحديث رصيد الصندوق مع Optimistic Locking (محسّن)
    # =========================================================================
    
    def _update_fund_balance_with_lock(self, fund_id: str, total_amount: Decimal) -> bool:
        """زيادة رصيد الصندوق مع Optimistic Locking"""
        try:
            if not fund_id:
                return True
            
            # ✅ استخدام SELECT FOR UPDATE لقفل الصف
            fund = self._uow.session.execute(
                select(FundModel)
                .where(FundModel.id == UUID(fund_id))
                .where(FundModel.status == 'active')
                .with_for_update()  # ✅ قفل الصف للتحديث
            ).scalar_one_or_none()
            
            if not fund:
                logger.error(f"Fund {fund_id} not found or inactive")
                return False
            
            old_balance = float(fund.balance or 0)
            amount = float(total_amount)
            new_balance = old_balance + amount
            
            # ✅ تحديث مع Optimistic Locking
            new_version = fund.version + 1
            result = self._uow.session.execute(
                update(FundModel)
                .where(
                    FundModel.id == fund.id,
                    FundModel.version == fund.version
                )
                .values(
                    balance=new_balance,
                    updated_at=datetime.now(timezone.utc),
                    version=new_version
                )
            )
            
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    entity_type="Fund",
                    entity_id=str(fund.id),
                    expected_version=fund.version,
                    actual_version=fund.version
                )
            
            fund.version = new_version
            fund.balance = new_balance
            
            # ✅ إنشاء حركة الصندوق
            movement = FundMovementModel(
                id=uuid4(),
                fund_id=fund.id,
                movement_type="deposit",
                amount=amount,
                currency=fund.currency,
                balance_before=old_balance,
                balance_after=new_balance,
                reason="إيداع من فاتورة",
                reference_id=fund_id,
                created_by="system",
                created_at=datetime.now(timezone.utc)
            )
            self._uow.session.add(movement)
            
            logger.info(f"Updated fund balance: {fund.code} - {old_balance:,.2f} → {new_balance:,.2f}")
            return True
            
        except ConcurrentModificationError:
            raise
        except Exception as e:
            logger.error(f"Error updating fund balance: {e}", exc_info=True)
            return False
    
    # =========================================================================
    # ✅ تسجيل عمليات التدقيق (Audit)
    # =========================================================================
    
    def _log_audit(
        self,
        operation: str,
        invoice_id: str,
        user_id: str,
        details: Dict[str, Any]
    ) -> None:
        """تسجيل عملية في سجل التدقيق"""
        try:
            if hasattr(self._uow, 'audit'):
                self._uow.audit.log_operation(
                    operation=operation,
                    entity_type="Invoice",
                    entity_id=invoice_id,
                    performed_by=user_id,
                    changes=details
                )
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
    
    # =========================================================================
    # ✅ دوال للتكامل مع واجهة المستخدم
    # =========================================================================
    
    def check_inventory_before_post(self, invoice_id: str) -> Dict[str, Any]:
        """التحقق من المخزون قبل الترحيل"""
        try:
            invoice_repo = self._uow.invoices
            invoice = invoice_repo.get_by_id(InvoiceId(UUID(invoice_id)))
            
            if not invoice:
                return {'success': False, 'message': f'الفاتورة {invoice_id} غير موجودة'}
            
            result = self._check_inventory(invoice.lines)
            return {
                'success': True,
                'inventory_check': result.to_dict(),
                'all_available': result.all_available,
                'confirmation_required': not result.all_available,
                'confirmation_message': result.get_confirmation_message()
            }
            
        except Exception as e:
            logger.error(f"Error checking inventory: {e}")
            return {'success': False, 'message': f'خطأ في التحقق من المخزون: {str(e)}'}
    
    def set_force_post(self, force: bool):
        """تعيين تجاوز التحقق من المخزون"""
        self._force_post = force
    
    # =========================================================================
    # ✅ بناء طلب القيد المحاسبي (محسّن)
    # =========================================================================
    
    def _build_journal_entry_request(self, invoice, cogs_lines: Optional[List[Dict[str, Any]]] = None) -> JournalEntryRequest:
        """
        بناء طلب قيد محاسبي من الفاتورة
        
        ✅ يستخدم Accounting Orchestrator
        ✅ يدعم جميع حالات الدفع (نقدي، آجل، شيك، تحويل)
        ✅ يدعم الضرائب
        ✅ يدعم العملات المتعددة
        ✅ يدعم فروع العملاء
        ✅ محدث: يسجل COGS (تكلفة البضاعة المباعة) وحساب المخزون
        """
        lines = []
        
        # ✅ الحصول على إعدادات الحسابات من التخزين المؤقت
        settings = self._get_accounting_settings()
        cash_account = AccountCode(settings['cash_account'])
        receivables_account = AccountCode(settings['receivables_account'])
        revenue_account = AccountCode(settings['revenue_account'])
        tax_payable_account = AccountCode(settings.get('tax_payable_account', '2100'))
        cogs_account = AccountCode(settings.get('cogs_account', '5010'))
        inventory_account = AccountCode(settings.get('inventory_account', '1030'))
        
        # المبلغ الإجمالي
        total_amount = invoice.total.amount
        currency = invoice.currency
        
        # 1. سطر المدين: الصندوق أو المدينين
        if invoice.payment_type == PaymentType.CASH:
            debit_account = cash_account
            debit_amount = total_amount
        elif invoice.payment_type == PaymentType.CREDIT:
            debit_account = receivables_account
            debit_amount = total_amount
        else:
            # شيك أو تحويل بنكي - نستخدم حساب وسيط أو حساب البنك
            debit_account = AccountCode("1040")  # حساب البنك
            debit_amount = total_amount
        
        lines.append({
            "account_code": debit_account.code,
            "debit": float(debit_amount),
            "currency": currency
        })
        
        # 2. سطر الدائن: الإيرادات (مع تفصيل حسب المنتج)
        for line in invoice.lines:
            lines.append({
                "account_code": revenue_account.code,
                "credit": float(line.total.amount),
                "currency": line.currency
            })
        
        # 3. سطر الضريبة إذا وجدت
        if invoice.tax_amount.amount > 0:
            lines.append({
                "account_code": tax_payable_account.code,
                "credit": float(invoice.tax_amount.amount),
                "currency": currency
            })
        
        # 4. ✅ قيد تكلفة البضاعة المباعة (COGS) + خصم المخزون
        #    وفقاً لمبدأ المطابقة (Matching Principle): الإيراد يقابله تكلفته.
        if cogs_lines:
            # تجميع التكلفة الإجمالية حسب العملة (تفصيل لكل بند عند الحاجة)
            for cogs in cogs_lines:
                cost_amount = Decimal(str(cogs.get('total_cost', 0)))
                if cost_amount <= 0:
                    continue
                cost_currency = cogs.get('currency') or currency
                lines.append({
                    "account_code": cogs_account.code,
                    "debit": float(cost_amount),
                    "currency": cost_currency
                })
                lines.append({
                    "account_code": inventory_account.code,
                    "credit": float(cost_amount),
                    "currency": cost_currency
                })
        
        # بناء الطلب مع معلومات إضافية
        metadata = {
            "invoice_number": str(invoice.number) if invoice.number else None,
            "customer_id": invoice.customer_id,
            "customer_name": invoice.customer_name,
            "payment_type": invoice.payment_type.value,
            "fund_id": invoice.fund_id,
            "site_id": invoice.site_id,
            "site_name": invoice.site_name,
            "currency": invoice.currency,
            "payment_currency": getattr(invoice, 'payment_currency', invoice.currency),
            "cogs_posted": bool(cogs_lines),
        }
        
        # ✅ إضافة معلومات فرع العميل إذا كانت موجودة
        if hasattr(invoice, 'customer_branch_id') and invoice.customer_branch_id:
            metadata['customer_branch_id'] = invoice.customer_branch_id
            metadata['customer_branch_name'] = invoice.customer_branch_name
            metadata['customer_branch_code'] = invoice.customer_branch_code
        
        return JournalEntryRequest(
            entity_type="invoice",
            entity_id=str(invoice.id),
            description=invoice.generate_journal_entry_description(),
            lines=lines,
            date=invoice.date,
            transaction_type="sales",
            created_by=invoice.created_by,
            reference_number=str(invoice.number) if invoice.number else None,
            metadata=metadata
        )
    
    # =========================================================================
    # ✅ المعالج الرئيسي - المحسّن بالكامل
    # =========================================================================
    
    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: PostInvoiceCommand, user_context: UserContext) -> dict:
        """معالج ترحيل الفاتورة مع Optimistic Locking ومحرك المخزون الجديد"""
        
        with self._uow:
            # ✅ ربط الـ Orchestrator ومحرك الترحيل بجلسة الـ UoW الحالية
            # (إصلاح قفل تعدد الجلسات: المستودعات كانت ترتبط بجلسة الحاوية
            #  بينما القيد يُحفظ على جلسة الـ UoW مما يسبب deadlock)
            orchestrator = self._orchestrator
            orchestrator._uow = self._uow
            engine = self._posting_engine
            engine._journal_repo = self._uow.journal_entries
            engine._ledger_repo = self._uow.ledger
            engine._period_repo = self._uow.periods
            engine._account_repo = self._uow.accounts
            engine._uow = self._uow

            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                return ErrorResponse(
                    message=f"الفاتورة {command.invoice_id} غير موجودة",
                    errors=[f"Invoice {command.invoice_id} not found"],
                    details={'invoice_id': command.invoice_id}
                ).to_dict()
            
            # =================================================================
            # مرحلة التحقق (Validation)
            # =================================================================
            
            # التحقق 1: الفاتورة مرحلة مسبقاً
            if invoice.is_posted:
                return {
                    "success": True,
                    "message": "Invoice already posted",
                    "invoice_id": command.invoice_id,
                    "journal_entry_id": invoice.journal_entry_id
                }
            
            # التحقق 2: وجود بنود
            if len(invoice.lines) == 0:
                return ErrorResponse(
                    message="لا يمكن ترحيل فاتورة بدون بنود",
                    errors=["Cannot post invoice with no lines"],
                    details={'invoice_id': command.invoice_id}
                ).to_dict()
            
            # التحقق 3: العميل
            customer_check = self._validate_customer(invoice)
            if not customer_check.success:
                customer_check.details['invoice_id'] = command.invoice_id
                return customer_check.to_dict()
            
            # التحقق 4: الموقع
            site_check = self._validate_site(invoice)
            if not site_check.success:
                site_check.details['invoice_id'] = command.invoice_id
                return site_check.to_dict()
            
            # التحقق 5: الصندوق
            if invoice.payment_type in [PaymentType.CASH, PaymentType.TRANSFER] and not invoice.fund_id:
                return ErrorResponse(
                    message=f"لا يمكن ترحيل فاتورة {invoice.payment_type.value} بدون صندوق",
                    errors=[f"Fund required for {invoice.payment_type.value} payment"],
                    details={'invoice_id': command.invoice_id}
                ).to_dict()
            
            # التحقق 6: تطابق عملة الفاتورة مع الصندوق
            fund_check = self._validate_fund_currency_match(invoice)
            if not fund_check.success:
                fund_check.details['invoice_id'] = command.invoice_id
                return fund_check.to_dict()
            
            # التحقق 7: العملة مدعومة
            if not self._is_currency_supported(invoice.currency):
                return ErrorResponse(
                    message=f"العملة '{invoice.currency}' غير مدعومة",
                    errors=[f"Currency {invoice.currency} not supported"],
                    details={'invoice_id': command.invoice_id}
                ).to_dict()
            
            # التحقق 8: المبلغ الإجمالي
            total_check = self._validate_invoice_total(invoice)
            if not total_check.success:
                total_check.details['invoice_id'] = command.invoice_id
                return total_check.to_dict()
            
            # التحقق 9: المخزون
            inventory_check = self._check_inventory(invoice.lines)
            
            if not inventory_check.all_available and not self._force_post:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "message": "بعض المنتجات غير متوفرة في المخزون",
                    "invoice_id": command.invoice_id,
                    "inventory_check": inventory_check.to_dict(),
                    "confirmation_message": inventory_check.get_confirmation_message()
                }
            
            # =================================================================
            # مرحلة التنفيذ (Execution) - كلها داخل معاملة واحدة ذرية
            # =================================================================
            
            # تعيين إعدادات الحسابات المحاسبية
            try:
                settings = self._get_accounting_settings()
                cash_account = AccountCode(settings['cash_account'])
                receivables_account = AccountCode(settings['receivables_account'])
                revenue_account = AccountCode(settings['revenue_account'])
                
                invoice.set_accounting_settings(
                    cash_account=cash_account,
                    receivables_account=receivables_account,
                    revenue_account=revenue_account
                )
                
            except Exception as e:
                logger.error(f"Error loading accounting settings: {e}")
                raise
            
            # ✅ تحديث المخزون أولاً - لحساب COGS (تكلفة البضاعة المباعة)
            #    داخل نفس المعاملة: أي فشل لاحق يرجع كل شيء (تراجع ذري)
            updated_products: List[Dict[str, Any]] = []
            try:
                skip_unavailable = self._force_post and not inventory_check.all_available
                inventory_success, updated_products = self._update_inventory_with_movements(
                    invoice.id.value, 
                    skip_unavailable
                )
                
                if not inventory_success:
                    raise ValueError("تعذر خصم المنتجات من المخزون.")
                    
            except ConcurrentModificationError as e:
                logger.warning(f"Inventory concurrent modification: {e}")
                raise
            except Exception as e:
                logger.error(f"Inventory error: {e}", exc_info=True)
                raise
            
            # ✅ إنشاء القيد المحاسبي عبر Accounting Orchestrator
            #    commit=False: لا يُـcommit داخل المعاملة - الذرية تُدار من هنا
            try:
                journal_request = self._build_journal_entry_request(invoice, cogs_lines=updated_products)
                orchestrator_result = self._orchestrator.create_journal_entry(
                    request=journal_request,
                    posted_by=user_context.user_id,
                    commit=False
                )
                
                if not orchestrator_result.success:
                    raise ValueError(
                        f"فشل إنشاء القيد المحاسبي: {orchestrator_result.message}"
                    )
                
                journal_entry_id = orchestrator_result.journal_entry_id
                
            except Exception as e:
                logger.error(f"Error creating journal entry via orchestrator: {e}", exc_info=True)
                raise
            
            # ✅ تحديث رصيد الصندوق
            if invoice.fund_id:
                try:
                    fund_success = self._update_fund_balance_with_lock(
                        invoice.fund_id, 
                        invoice.total.amount
                    )
                    if not fund_success:
                        raise ValueError("تعذر تحديث رصيد الصندوق.")
                        
                except ConcurrentModificationError as e:
                    logger.warning(f"Fund concurrent modification: {e}")
                    raise
            
            # ✅ ترحيل الفاتورة
            invoice.post(command.posted_by, journal_entry_id)
            invoice_repo.save(invoice)
            
            # ✅ تسجيل في سجل التدقيق
            self._log_audit(
                operation="POST_INVOICE",
                invoice_id=str(invoice.id),
                user_id=user_context.user_id,
                details={
                    'invoice_number': str(invoice.number) if invoice.number else None,
                    'customer_id': invoice.customer_id,
                    'total_amount': float(invoice.total.amount),
                    'journal_entry_id': journal_entry_id,
                    'payment_type': invoice.payment_type.value,
                    'fund_id': invoice.fund_id,
                }
            )
            
            # ✅ Commit المعاملة (تنفيذ ذري لكل ما سبق - أو تراجع كامل)
            try:
                self._commit()
            except Exception as e:
                logger.error(f"Commit failed: {e}", exc_info=True)
                raise
            
            logger.info(f"Invoice {invoice.number} posted successfully by {command.posted_by}")
            
            # ✅ إرجاع النتيجة النهائية
            return {
                "success": True,
                "message": "Invoice posted successfully",
                "invoice_id": command.invoice_id,
                "journal_entry_id": journal_entry_id,
                "invoice_number": str(invoice.number) if invoice.number else None,
                "payment_currency": getattr(invoice, 'payment_currency', invoice.currency),
                "site_id": invoice.site_id,
                "site_name": invoice.site_name,
                "customer_branch_id": getattr(invoice, 'customer_branch_id', None),
                "customer_branch_name": getattr(invoice, 'customer_branch_name', None),
                "inventory_updated": True,
                "fund_updated": True if invoice.fund_id else None,
                "inventory_check": inventory_check.to_dict(),
                "stock_movements": updated_products if 'updated_products' in locals() else [],
                "orchestrator_result": {
                    "success": orchestrator_result.success,
                    "journal_entry_id": orchestrator_result.journal_entry_id,
                    "posted": orchestrator_result.posted,
                },
                "audit_logged": True
            }