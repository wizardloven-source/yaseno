# C:\Users\MTC\Desktop\erpya\core\application\handlers\suppliers\delete_supplier_handler.py
"""Delete Supplier Handler - حذف مورد"""

import logging

from core.domain.suppliers.value_objects import SupplierId
from core.domain.suppliers.exceptions import SupplierNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.suppliers.commands import DeleteSupplierCommand

logger = logging.getLogger(__name__)


class DeleteSupplierHandler(BaseHandler[DeleteSupplierCommand, dict]):
    """Handler for deleting a supplier (soft or hard delete)"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteSupplierCommand, user_context: UserContext) -> dict:
        with self._uow:
            repo = self._uow.suppliers
            
            supplier_id = SupplierId.from_string(command.supplier_id)
            supplier = repo.get_by_id(supplier_id)
            if not supplier:
                raise SupplierNotFoundError(command.supplier_id)
            
            if command.permanent:
                # حذف دائم
                result = repo.delete(supplier_id, permanent=True)
                message = "Supplier permanently deleted"
                logger.info(f"Supplier permanently deleted: {supplier.code} by {user_context.user_id}")
            else:
                # حذف ناعم
                supplier.soft_delete(user_context.user_id)
                repo.save(supplier)
                result = True
                message = "Supplier soft deleted (deactivated)"
                logger.info(f"Supplier soft deleted: {supplier.code} by {user_context.user_id}")
            
            self._commit()
            
            return {
                "success": result,
                "supplier_id": command.supplier_id,
                "permanent": command.permanent,
                "message": message
            }