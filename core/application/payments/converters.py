# core/application/payments/converters.py
"""
Converters for Payments - تحويل بين Domain Entities و DTOs
"""

from typing import List, Dict, Any
from decimal import Decimal

from core.domain.payments.entities import Payment, PaymentLine
from core.domain.payments.value_objects import (
    PaymentType,
    PaymentMethod,
    PaymentStatus,
    PaymentReference,
)
from .dtos import PaymentDTO, PaymentLineDTO


def payment_to_dto(payment: Payment) -> PaymentDTO:
    """تحويل كيان الدفعة إلى DTO"""
    if not payment:
        return None

    lines = []
    for line in payment.lines:
        lines.append(PaymentLineDTO(
            line_id=line.line_id,
            reference_type=line.reference_type,
            reference_id=line.reference_id,
            amount=line.amount.amount,
            currency=line.amount.currency,
            total=line.total.amount,
            notes=line.notes,
        ))

    return PaymentDTO(
        id=str(payment.id),
        code=str(payment.code),
        date=payment.date,
        payment_type=payment.payment_type.value,
        payment_method=payment.payment_method.value,
        amount=payment.amount.amount,
        currency=payment.currency,
        customer_id=payment.customer_id,
        customer_name=payment.customer_name,
        supplier_id=payment.supplier_id,
        supplier_name=payment.supplier_name,
        fund_id=payment.fund_id,
        fund_code=payment.fund_code,
        status=payment.status.value,
        lines=lines,
        notes=payment.notes,
        reference_type=payment.reference.reference_type if payment.reference else None,
        reference_id=payment.reference.reference_id if payment.reference else None,
        approved_by=payment.approved_by,
        approved_at=payment.approved_at,
        completed_by=payment.completed_by,
        completed_at=payment.completed_at,
        created_at=payment.created_at,
        created_by=payment.created_by,
        updated_at=payment.updated_at,
        updated_by=payment.updated_by,
        version=payment.version,
    )


def payment_line_to_dto(line: PaymentLine) -> PaymentLineDTO:
    """تحويل سطر دفعة إلى DTO"""
    return PaymentLineDTO(
        line_id=line.line_id,
        reference_type=line.reference_type,
        reference_id=line.reference_id,
        amount=line.amount.amount,
        currency=line.amount.currency,
        total=line.total.amount,
        notes=line.notes,
    )


def dto_to_payment(dto: PaymentDTO) -> Dict[str, Any]:
    """تحويل DTO إلى قاموس (للاستخدام في Service Layer)"""
    return {
        'id': dto.id,
        'code': dto.code,
        'date': dto.date,
        'payment_type': dto.payment_type,
        'payment_method': dto.payment_method,
        'amount': float(dto.amount),
        'currency': dto.currency,
        'customer_id': dto.customer_id,
        'customer_name': dto.customer_name,
        'supplier_id': dto.supplier_id,
        'supplier_name': dto.supplier_name,
        'fund_id': dto.fund_id,
        'fund_code': dto.fund_code,
        'status': dto.status,
        'lines': [
            {
                'line_id': line.line_id,
                'reference_type': line.reference_type,
                'reference_id': line.reference_id,
                'amount': float(line.amount),
                'currency': line.currency,
                'total': float(line.total),
                'notes': line.notes,
            }
            for line in dto.lines
        ],
        'notes': dto.notes,
        'reference_type': dto.reference_type,
        'reference_id': dto.reference_id,
        'approved_by': dto.approved_by,
        'approved_at': dto.approved_at,
        'completed_by': dto.completed_by,
        'completed_at': dto.completed_at,
        'created_at': dto.created_at,
        'created_by': dto.created_by,
        'updated_at': dto.updated_at,
        'updated_by': dto.updated_by,
        'version': dto.version,
    }