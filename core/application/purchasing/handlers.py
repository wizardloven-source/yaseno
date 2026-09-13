# core/application/purchasing/handlers.py
"""
Purchase Return Handlers - معالجات أوامر إرجاع المشتريات

✅ جديد: دعم كامل لدورة حياة إرجاع المشتريات
✅ جديد: تكامل مع Debit Note
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone

from .commands import (
    CreatePurchaseReturnCommand,
    SubmitPurchaseReturnCommand,
    ApprovePurchaseReturnCommand,
    RejectPurchaseReturnCommand,
    ShipPurchaseReturnCommand,
    ReceiveBySupplierCommand,
    CompletePurchaseReturnCommand,
    CancelPurchaseReturnCommand,
    PurchaseReturnItemCommand,
)

from core.domain.purchasing.entities import PurchaseReturn, PurchaseReturnItem
from core.domain.purchasing.value_objects import (
    PurchaseReturnId, PurchaseReturnNumber, PurchaseReturnStatus,
    DebitNoteId, DebitNoteNumber
)
from core.domain.purchasing.interfaces import IPurchaseReturnRepository
from core.domain.shared.value_objects import Money


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CreatePurchaseReturnHandler:
    """معالج إنشاء إرجاع مشتريات"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: CreatePurchaseReturnCommand) -> PurchaseReturn:
        """إنشاء إرجاع مشتريات جديد"""
        
        # إنشاء الأسطر
        lines = []
        for line_cmd in command.lines:
            line = PurchaseReturnItem(
                product_code=line_cmd.product_code,
                product_name=line_cmd.product_name,
                quantity=line_cmd.quantity,
                unit_price=Money(line_cmd.unit_price, command.currency),
                reason=line_cmd.reason,
                condition=line_cmd.condition,
                batch_number=line_cmd.batch_number,
                serial_numbers=line_cmd.serial_numbers,
                expiry_date=line_cmd.expiry_date,
                discount_percent=line_cmd.discount_percent,
                discount_amount=line_cmd.discount_amount,
                tax_rate=line_cmd.tax_rate,
            )
            lines.append(line)
        
        # إنشاء الإرجاع
        purchase_return = PurchaseReturn(
            purchase_order_id=command.purchase_order_id,
            purchase_order_number=command.purchase_order_number,
            supplier_id=command.supplier_id,
            supplier_name=command.supplier_name,
            site_id=command.site_id,
            site_name=command.site_name,
            warehouse_id=command.warehouse_id,
            currency=command.currency,
            notes=command.notes,
            reason=command.reason,
            shipping_method=command.shipping_method,
            created_by=command.created_by,
        )
        
        # إضافة الأسطر
        for line in lines:
            purchase_return.add_line(line)
        
        # حفظ الإرجاع
        self.return_repo.save(purchase_return)
        
        return purchase_return


class SubmitPurchaseReturnHandler:
    """معالج تقديم إرجاع المشتريات للموافقة"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: SubmitPurchaseReturnCommand) -> PurchaseReturn:
        """تقديم الإرجاع للموافقة"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.submit(submitted_by=command.submitted_by)
        self.return_repo.save(purchase_return)
        
        return purchase_return


class ApprovePurchaseReturnHandler:
    """معالج الموافقة على إرجاع المشتريات"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: ApprovePurchaseReturnCommand) -> PurchaseReturn:
        """الموافقة على الإرجاع"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.approve(approved_by=command.approved_by)
        self.return_repo.save(purchase_return)
        
        return purchase_return


class RejectPurchaseReturnHandler:
    """معالج رفض إرجاع المشتريات"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: RejectPurchaseReturnCommand) -> PurchaseReturn:
        """رفض الإرجاع"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.reject(rejected_by=command.rejected_by, reason=command.reason)
        self.return_repo.save(purchase_return)
        
        return purchase_return


class ShipPurchaseReturnHandler:
    """معالج شحن إرجاع المشتريات"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: ShipPurchaseReturnCommand) -> PurchaseReturn:
        """شحن الإرجاع للمورد"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.ship(
            shipped_by=command.shipped_by,
            shipping_method=command.shipping_method,
            tracking_number=command.tracking_number,
        )
        self.return_repo.save(purchase_return)
        
        return purchase_return


class ReceiveBySupplierHandler:
    """معالج تأكيد استلام المورد"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: ReceiveBySupplierCommand) -> PurchaseReturn:
        """تأكيد استلام المورد للإرجاع"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.receive_by_supplier(received_by=command.received_by)
        self.return_repo.save(purchase_return)
        
        return purchase_return


class CompletePurchaseReturnHandler:
    """معالج إكمال إرجاع المشتريات وإنشاء Debit Note"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: CompletePurchaseReturnCommand) -> PurchaseReturn:
        """إكمال الإرجاع وإنشاء Debit Note"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.complete(
            completed_by=command.completed_by,
            auto_create_debit_note=command.auto_create_debit_note,
        )
        self.return_repo.save(purchase_return)
        
        return purchase_return


class CancelPurchaseReturnHandler:
    """معالج إلغاء إرجاع المشتريات"""
    
    def __init__(self, return_repo: IPurchaseReturnRepository):
        self.return_repo = return_repo
    
    def handle(self, command: CancelPurchaseReturnCommand) -> PurchaseReturn:
        """إلغاء الإرجاع"""
        
        purchase_return = self.return_repo.get_by_id(command.return_id)
        if not purchase_return:
            from core.domain.purchasing.exceptions import PurchaseReturnNotFoundException
            raise PurchaseReturnNotFoundException(command.return_id)
        
        purchase_return.cancel(cancelled_by=command.cancelled_by, reason=command.reason)
        self.return_repo.save(purchase_return)
        
        return purchase_return
