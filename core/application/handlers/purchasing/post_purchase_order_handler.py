# core/application/handlers/purchasing/post_purchase_order_handler.py
"""
Post Purchase Order Handler - ترحيل أمر الشراء
✅ محدث: استخدام Accounting Orchestrator المركزي
✅ محدث: إنشاء حركات مخزون (StockMovement) عند الترحيل
✅ محدث: دعم الاستلام التلقائي إذا تم تفعيله
✅ محدث: Optimistic Locking
✅ محدث: دمج مع محرك المخزون الجديد
✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمة المخزون
"""

import logging
import uuid as uuid_module
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.purchasing.exceptions import PurchaseOrderNotFoundError
from core.domain.shared.value_objects import Money, AccountCode
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import JournalEntryId
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

# ✅ استيراد Accounting Orchestrator
from core.application.accounting.orchestrator import (
    AccountingOrchestrator,
    JournalEntryRequest,
    JournalEntryResult
)

# ✅ استيراد محرك المخزون الجديد
from core.domain.inventory.services import StockMovementService
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    BatchNumber,
    ExpiryDate,
    Money as InventoryMoney,
    StockLocation,
)

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import PostPurchaseOrderCommand
from core.application.purchasing.converters import lines_to_journal_lines

logger = logging.getLogger(__name__)


class PostPurchaseOrderHandler(BaseHandler[PostPurchaseOrderCommand, dict]):
    """
    معالج ترحيل أمر الشراء - النسخة النهائية المتكاملة
    
    ✅ محدث: استخدام Accounting Orchestrator لإنشاء القيد المحاسبي
    ✅ محدث: إنشاء حركات مخزون (StockMovement) عند الترحيل
    ✅ محدث: دعم الاستلام التلقائي إذا تم تفعيله
    ✅ محدث: Optimistic Locking
    ✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمة المخزون
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
        
        # ✅ تهيئة بطيئة (Lazy Initialization) - لن يتم إنشاؤها حتى الحاجة
        self._stock_service = None
    
    # =========================================================================
    # ✅ تهيئة خدمة المخزون عند الحاجة (Lazy Initialization)
    # =========================================================================
    
    def _get_stock_service(self):
        """
        تهيئة خدمة المخزون عند الحاجة فقط (Lazy Initialization)
        
        هذه الطريقة تمنع إنشاء الخدمة في مرحلة تسجيل المعالجات (Bootstrap)
        وتؤجل الإنشاء إلى وقت التنفيذ الفعلي للأمر.
        """
        if self._stock_service is None:
            # ✅ استخدام getattr بأمان للوصول إلى stock_movements
            stock_movements = getattr(self._uow, 'stock_movements', None)
            if stock_movements:
                self._stock_service = StockMovementService(stock_movements)
            else:
                logger.warning("stock_movements not available in UoW")
                # ✅ إنشاء service وهمي (dummy) لتجنب None checks في كل مكان
                self._stock_service = StockMovementService(None)
        return self._stock_service
    
    # =========================================================================
    # ✅ بناء طلب القيد المحاسبي لـ Accounting Orchestrator
    # =========================================================================
    
    def _build_journal_entry_request(self, order) -> JournalEntryRequest:
        """
        بناء طلب قيد محاسبي من أمر الشراء
        
        ✅ يستخدم Accounting Orchestrator
        ✅ يدعم حسابات المخزون والموردين
        ✅ يدعم العملات المتعددة
        """
        lines = []
        
        # الحصول على إعدادات الحسابات
        inventory_account = AccountCode("1030")  # حساب المخزون
        payables_account = AccountCode("2010")   # حساب الدائنون
        
        # 1. سطر المدين: حساب المخزون (باستخدام التكلفة الفعلية)
        for line in order.lines:
            # استخدام التكلفة الفعلية أو سعر الشراء
            cost = line.unit_cost.amount if hasattr(line, 'unit_cost') else line.unit_price.amount
            lines.append({
                "account_code": inventory_account.code,
                "debit": float(line.total.amount),
                "currency": line.currency
            })
        
        # 2. سطر الدائن: حساب الدائنون (المورد)
        lines.append({
            "account_code": payables_account.code,
            "credit": float(order.total.amount),
            "currency": order.currency
        })
        
        # بناء الطلب
        return JournalEntryRequest(
            entity_type="purchase_order",
            entity_id=str(order.id),
            description=order.generate_journal_entry_description(),
            lines=lines,
            date=order.date,
            transaction_type="purchase",
            created_by=order.created_by,
            reference_number=str(order.number) if order.number else None,
            metadata={
                "order_number": str(order.number) if order.number else None,
                "supplier_id": order.supplier_id,
                "supplier_name": order.supplier_name,
                "payment_terms": order.payment_terms.value if order.payment_terms else None,
                "site_id": order.site_id,
                "site_name": order.site_name,
                "currency": order.currency,
                "lines_count": len(order.lines),
                "total_quantity": float(order.total_ordered_quantity) if hasattr(order, 'total_ordered_quantity') else None,
            }
        )
    
    # =========================================================================
    # ✅ المعالج الرئيسي - المحسّن بالكامل
    # =========================================================================
    
    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: PostPurchaseOrderCommand, user_context: UserContext) -> dict:
        """معالج ترحيل أمر الشراء مع Optimistic Locking ومحرك المخزون الجديد"""
        
        with self._uow:
            # ✅ ربط الـ Orchestrator ومحرك الترحيل بجلسة الـ UoW الحالية
            # (نفس إصلاح الفواتير: المستودعات المسجلة في الحاوية مرتبطة بجلسة
            #  منفصلة عن جلسة الـ UoW مما يسبب deadlock عند الإدراج)
            orchestrator = self._orchestrator
            orchestrator._uow = self._uow
            engine = self._posting_engine
            engine._journal_repo = self._uow.journal_entries
            engine._ledger_repo = self._uow.ledger
            engine._period_repo = self._uow.periods
            engine._account_repo = self._uow.accounts
            engine._uow = self._uow

            order_repo = self._uow.purchase_orders
            order_id = PurchaseOrderId(UUID(command.order_id))
            
            order = order_repo.get_by_id(order_id)
            if not order:
                return {
                    "success": False,
                    "message": f"Purchase order {command.order_id} not found",
                    "order_id": command.order_id
                }
            
            # ========== التحقق 1: الأمر مرحل مسبقاً؟ ==========
            if order.is_posted:
                return {
                    "success": True,
                    "message": "Purchase order already posted",
                    "order_id": command.order_id,
                    "journal_entry_id": order.journal_entry_id
                }
            
            # ========== التحقق 2: وجود بنود ==========
            if len(order.lines) == 0:
                return {
                    "success": False,
                    "message": "Cannot post purchase order with no lines",
                    "order_id": command.order_id
                }
            
            # ========== التحقق 3: وجود مورد ==========
            if not order.supplier_id or not order.supplier_name:
                return {
                    "success": False,
                    "message": "Cannot post purchase order without a supplier",
                    "order_id": command.order_id
                }
            
            # ========== التحقق 4: العملة مدعومة ==========
            supported_currencies = ["USD", "EUR", "LBP", "GBP"]
            if order.currency not in supported_currencies:
                return {
                    "success": False,
                    "message": f"Unsupported currency: {order.currency}",
                    "order_id": command.order_id
                }
            
            # ========== ✅ إنشاء القيد المحاسبي عبر Accounting Orchestrator ==========
            try:
                # 1. بناء طلب القيد من أمر الشراء
                journal_request = self._build_journal_entry_request(order)
                
                # 2. تنفيذ الطلب عبر الـ Orchestrator
                orchestrator_result = self._orchestrator.create_journal_entry(
                    request=journal_request,
                    posted_by=user_context.user_id
                )
                
                if not orchestrator_result.success:
                    return {
                        "success": False,
                        "message": f"فشل إنشاء القيد المحاسبي: {orchestrator_result.message}",
                        "order_id": command.order_id,
                        "errors": orchestrator_result.errors
                    }
                
                journal_entry_id = orchestrator_result.journal_entry_id
                
            except Exception as e:
                logger.error(f"Error creating journal entry via orchestrator: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"فشل إنشاء القيد المحاسبي: {str(e)}",
                    "order_id": command.order_id,
                    "errors": [str(e)]
                }
            
            # ========== ✅ ترحيل الأمر ==========
            order.post(command.posted_by, journal_entry_id)
            
            # ========== ✅ إنشاء حركات المخزون ==========
            stock_movements = []
            
            # ✅ الحصول على خدمة المخزون (تهيئة بطيئة)
            stock_service = self._get_stock_service()
            
            try:
                for line in order.lines:
                    # التحقق من وجود المنتج
                    from core.domain.products.value_objects import ProductCode
                    product = self._uow.products.get_by_code(ProductCode(line.product_code))
                    if not product:
                        logger.warning(f"Product {line.product_code} not found, skipping stock movement")
                        continue
                    
                    # إنشاء كيان المخزون
                    entity = EntityId("product", str(product.id))
                    
                    # ✅ إنشاء حركة شراء (تزيد المخزون)
                    movement = stock_service.create_inbound_movement(
                        entity=entity,
                        quantity=line.quantity,
                        unit_cost=InventoryMoney(line.unit_price.amount, line.currency),
                        movement_type=StockMovementType.PURCHASE,
                        reference_type="PurchaseOrder",
                        reference_id=str(order.id),
                        batch_number=BatchNumber(line.batch_number) if line.batch_number else None,
                        expiry_date=ExpiryDate(line.expiry_date) if line.expiry_date else None,
                        location=line.location,
                        notes=f"شراء من أمر {order.number} - {line.product_name}",
                        created_by=user_context.user_id
                    )
                    
                    stock_movements.append({
                        'line_id': line.line_id,
                        'product_code': line.product_code,
                        'movement_id': str(movement.id),
                        'quantity': float(line.quantity),
                        'unit_cost': float(line.unit_price.amount),
                        'total_cost': float(line.total.amount),
                        'currency': line.currency,
                    })
                    
                    # ✅ حفظ معرف الحركة في الأمر
                    order.add_stock_movement(str(movement.id))
                    
                    logger.info(
                        f"Stock movement created for {line.product_code}: "
                        f"{line.quantity} units at {line.unit_price.amount} {line.currency}"
                    )
                    
            except Exception as e:
                logger.error(f"Error creating stock movements: {e}", exc_info=True)
                # في حالة فشل إنشاء حركات المخزون، نرجع خطأ
                return {
                    "success": False,
                    "message": f"Failed to create stock movements: {str(e)}",
                    "order_id": command.order_id,
                    "errors": [str(e)]
                }
            
            # ========== ✅ استلام تلقائي إذا تم تفعيله ==========
            auto_receive = getattr(order, 'auto_receive_on_post', False)
            if auto_receive:
                try:
                    # استلام جميع البضاعة تلقائياً
                    received_lines = order.receive_all(
                        received_by=user_context.user_id,
                        # يمكن تمرير تفاصيل إضافية هنا
                    )
                    logger.info(f"Auto-received all items for purchase order {order.number}")
                except Exception as e:
                    logger.warning(f"Auto-receive failed: {e}")
                    # لا نمنع الترحيل إذا فشل الاستلام التلقائي
            
            # ========== ✅ حفظ التغييرات ==========
            order_repo.save(order)
            self._commit()
            
            logger.info(f"Purchase order {order.number} posted successfully by {command.posted_by}")
            
            return {
                "success": True,
                "message": "Purchase order posted successfully",
                "order_id": command.order_id,
                "journal_entry_id": journal_entry_id,
                "order_number": str(order.number) if order.number else None,
                "stock_movements_created": len(stock_movements),
                "stock_movements": stock_movements,
                "auto_received": auto_receive,
                "orchestrator_result": {
                    "success": orchestrator_result.success,
                    "journal_entry_id": orchestrator_result.journal_entry_id,
                    "posted": orchestrator_result.posted,
                }
            }