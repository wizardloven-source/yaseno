# core/domain/suppliers/exceptions.py
"""Domain Exceptions for Suppliers Context"""


class SupplierError(Exception):
    pass


class SupplierNotFoundError(SupplierError):
    def __init__(self, supplier_id: str):
        self.supplier_id = supplier_id
        super().__init__(f"Supplier not found: {supplier_id}")


class DuplicateSupplierCodeError(SupplierError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Supplier code already exists: {code}")


class InvalidSupplierStatusTransition(SupplierError):
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Cannot transition from {current_status} to {new_status}")