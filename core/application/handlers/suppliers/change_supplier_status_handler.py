# C:\Users\MTC\Desktop\erpya\core\application\handlers\suppliers\change_supplier_status_handler.py
"""Change Supplier Status Handler - تغيير حالة المورد"""

import logging

from core.domain.suppliers.value_objects import SupplierId, SupplierStatus
from core.domain.suppliers.exceptions import SupplierNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.suppliers.commands import ChangeSupplierStatusCommand

logger = logging.getLogger(__name__)


class ChangeSupplierStatusHandler(BaseHandler[ChangeSupplierStatusCommand, dict]):
    """Handler for changing supplier status"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ChangeSupplierStatusCommand, user_context: UserContext) -> dict:
        with self._uow:
            repo = self._uow.suppliers
            
            supplier_id = SupplierId.from_string(command.supplier_id)
            supplier = repo.get_by_id(supplier_id)
            if not supplier:
                raise SupplierNotFoundError(command.supplier_id)
            
            # تحويل الحالة
            status_map = {
                "active": SupplierStatus.ACTIVE,
                "inactive": SupplierStatus.INACTIVE,
                "suspended": SupplierStatus.SUSPENDED,
                "blocked": SupplierStatus.BLOCKED,
            }
            new_status = status_map.get(command.new_status, SupplierStatus.ACTIVE)
            
            # تغيير الحالة
            old_status = supplier.status.value
            supplier.change_status(new_status, command.reason, user_context.user_id)
            
            repo.save(supplier)
            self._commit()
            
            logger.info(f"Supplier status changed: {supplier.code} from {old_status} to {new_status.value} by {user_context.user_id}")
            
            return {
                "success": True,
                "supplier_id": command.supplier_id,
                "old_status": old_status,
                "new_status": new_status.value,
                "message": f"Supplier status changed to {new_status.value}"
            }