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


# ========== ✅ Purchase Return Exceptions ==========

class PurchaseReturnNotFoundException(PurchasingError):
    def __init__(self, return_id: str):
        super().__init__(f"Purchase return not found: {return_id}")
        self.return_id = return_id


class InvalidPurchaseReturnStatusError(PurchasingError):
    def __init__(self, return_id: str, current_status: str, required_action: str):
        super().__init__(
            f"Invalid status for purchase return {return_id}. "
            f"Current status: {current_status}, Required for: {required_action}"
        )
        self.return_id = return_id
        self.current_status = current_status
        self.required_action = required_action


class CannotModifyCompletedReturnError(PurchasingError):
    def __init__(self, return_id: str):
        super().__init__(f"Cannot modify completed purchase return: {return_id}")
        self.return_id = return_id


class DuplicatePurchaseReturnNumberError(PurchasingError):
    def __init__(self, number: str):
        super().__init__(f"Duplicate purchase return number: {number}")
        self.number = number


class PurchaseReturnWithoutOriginalOrderError(PurchasingError):
    def __init__(self, return_id: str):
        super().__init__(f"Purchase return must reference original purchase order: {return_id}")
        self.return_id = return_id


class CannotReturnMoreThanReceivedError(PurchasingError):
    def __init__(self, product_code: str, return_qty, received_qty):
        super().__init__(
            f"Cannot return more than received. Product: {product_code}, "
            f"Return quantity: {return_qty}, Received quantity: {received_qty}"
        )
        self.product_code = product_code
        self.return_qty = return_qty
        self.received_qty = received_qty


# ========== ✅ Debit Note Exceptions ==========

class DebitNoteNotFoundException(PurchasingError):
    def __init__(self, debit_note_id: str):
        super().__init__(f"Debit note not found: {debit_note_id}")
        self.debit_note_id = debit_note_id


class InvalidDebitNoteStatusError(PurchasingError):
    def __init__(self, debit_note_id: str, current_status: str, required_action: str):
        super().__init__(
            f"Invalid status for debit note {debit_note_id}. "
            f"Current status: {current_status}, Required for: {required_action}"
        )
        self.debit_note_id = debit_note_id
        self.current_status = current_status
        self.required_action = required_action


class CannotModifyPostedDebitNoteError(PurchasingError):
    def __init__(self, debit_note_id: str):
        super().__init__(f"Cannot modify posted debit note: {debit_note_id}")
        self.debit_note_id = debit_note_id


class DebitNoteAlreadyPostedError(PurchasingError):
    def __init__(self, debit_note_id: str):
        super().__init__(f"Debit note already posted: {debit_note_id}")
        self.debit_note_id = debit_note_id


class CannotCancelPostedDebitNoteError(PurchasingError):
    def __init__(self, debit_note_id: str):
        super().__init__(f"Cannot cancel posted debit note: {debit_note_id}")
        self.debit_note_id = debit_note_id


class DebitNoteAlreadyCancelledError(PurchasingError):
    def __init__(self, debit_note_id: str):
        super().__init__(f"Debit note already cancelled: {debit_note_id}")
        self.debit_note_id = debit_note_id


class DebitNoteAmountMismatchError(PurchasingError):
    def __init__(self, debit_note_id: str, expected_amount, actual_amount):
        super().__init__(
            f"Debit note amount mismatch. ID: {debit_note_id}, "
            f"Expected: {expected_amount}, Actual: {actual_amount}"
        )
        self.debit_note_id = debit_note_id
        self.expected_amount = expected_amount
        self.actual_amount = actual_amount