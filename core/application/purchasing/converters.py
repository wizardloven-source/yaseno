from typing import List, Dict, Any
from decimal import Decimal

from core.domain.purchasing.entities import PurchaseOrder, PurchaseLine
from core.domain.shared.value_objects import Money, AccountCode
from core.domain.accounting.entities import JournalLine

from .dtos import PurchaseOrderDTO, PurchaseLineDTO


def order_to_dto(order: PurchaseOrder) -> PurchaseOrderDTO:
    if not order:
        return None
    
    return PurchaseOrderDTO(
        id=str(order.id.value),
        number=str(order.number) if order.number else None,
        date=order.date,
        expected_delivery_date=order.expected_delivery_date,
        supplier_id=order.supplier_id,
        supplier_name=order.supplier_name,
        site_id=order.site_id,
        site_name=order.site_name,
        currency=order.currency,
        payment_terms=order.payment_terms.value,
        notes=order.notes,
        lines=[line_to_dto(line) for line in order.lines],
        journal_entry_id=order.journal_entry_id,
        created_at=order.created_at,
        created_by=order.created_by,
        posted_at=order.posted_at,
        posted_by=order.posted_by,
        received_at=order.received_at,
        received_by=order.received_by,
        status=order.status.value
    )


def line_to_dto(line: PurchaseLine) -> PurchaseLineDTO:
    return PurchaseLineDTO(
        line_id=line.line_id,
        product_code=line.product_code,
        product_name=line.product_name,
        quantity=line.quantity,
        unit_price=line.unit_price.amount,
        total=line.total.amount,
        currency=line.unit_price.currency,
        notes=line.notes,
        received_quantity=line.received_quantity
    )


def lines_to_journal_lines(lines_data: List[Dict[str, Any]]) -> List[JournalLine]:
    journal_lines = []
    for line_data in lines_data:
        journal_lines.append(
            JournalLine(
                account_code=AccountCode(line_data["account_code"]),
                debit=Money(Decimal(str(line_data["debit"])), line_data["currency"]),
                credit=Money(Decimal(str(line_data["credit"])), line_data["currency"])
            )
        )
    return journal_lines


def dto_to_order(dto: PurchaseOrderDTO) -> Dict[str, Any]:
    if not dto:
        return None
    
    return {
        'id': dto.id,
        'number': dto.number,
        'date': dto.date,
        'supplier_id': dto.supplier_id,
        'supplier_name': dto.supplier_name,
        'site_id': dto.site_id,
        'site_name': dto.site_name,
        'currency': dto.currency,
        'payment_terms': dto.payment_terms,
        'notes': dto.notes,
        'lines': [
            {
                'line_id': line.line_id,
                'product_code': line.product_code,
                'product_name': line.product_name,
                'quantity': float(line.quantity),
                'unit_price': float(line.unit_price),
                'total': float(line.total),
                'currency': line.currency,
                'notes': line.notes,
                'received_quantity': float(line.received_quantity)
            }
            for line in dto.lines
        ],
        'journal_entry_id': dto.journal_entry_id,
        'created_at': dto.created_at,
        'created_by': dto.created_by,
        'posted_at': dto.posted_at,
        'posted_by': dto.posted_by,
        'status': dto.status
    }