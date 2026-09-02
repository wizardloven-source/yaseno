class PurchasingError(Exception):
    """Base exception for purchasing domain"""
    pass


class PurchaseOrderNotFoundError(PurchasingError):
    def __init__(self, order_id: str):
        super().__init__(f"Purchase order not found: {order_id}")
        self.order_id = order_id


class CannotModifyPostedPurchaseOrderError(PurchasingError):
    def __init__(self, order_id: str):
        super().__init__(f"Cannot modify posted purchase order: {order_id}")
        self.order_id = order_id


class PurchaseOrderAlreadyPostedError(PurchasingError):
    def __init__(self, order_id: str):
        super().__init__(f"Purchase order already posted: {order_id}")
        self.order_id = order_id


class CannotReceiveUnpostedPurchaseOrderError(PurchasingError):
    def __init__(self, order_id: str):
        super().__init__(f"Cannot receive goods from unposted purchase order: {order_id}")
        self.order_id = order_id


class InvalidQuantityError(PurchasingError):
    def __init__(self, message: str):
        super().__init__(message)