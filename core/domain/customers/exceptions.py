# core/domain/customers/exceptions.py
"""Domain Exceptions for Customers Context"""


class CustomerError(Exception):
    pass


class CustomerNotFoundError(CustomerError):
    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        super().__init__(f"Customer not found: {customer_id}")


class DuplicateCustomerCodeError(CustomerError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Customer code already exists: {code}")


class InvalidCustomerStatusTransition(CustomerError):
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Cannot transition from {current_status} to {new_status}")