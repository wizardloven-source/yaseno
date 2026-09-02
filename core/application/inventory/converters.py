from typing import Iterable, List

from core.domain.inventory.entities import StockMovement, StockBatch, StockTransfer
from core.application.inventory.dtos import (
    StockMovementDTO,
    StockBatchDTO,
    StockTransferDTO,
)


def movement_to_dto(movement: StockMovement) -> StockMovementDTO:
    return StockMovementDTO(
        id=str(movement.id),
        entity_type=movement.entity.entity_type if hasattr(movement.entity, "entity_type") else "",
        entity_id=str(movement.entity.entity_id) if hasattr(movement.entity, "entity_id") else str(movement.entity),
        movement_type=movement.movement_type.value,
        quantity=movement.quantity,
        unit_cost=movement.unit_cost.amount,
        total_cost=movement.total_cost.amount,
        currency=movement.unit_cost.currency,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        batch_number=str(movement.batch_number) if movement.batch_number else None,
        location=str(movement.location) if movement.location else None,
        notes=movement.notes,
        created_at=movement.created_at,
        created_by=movement.created_by,
    )


def batch_to_dto(batch: StockBatch) -> StockBatchDTO:
    return StockBatchDTO(
        id=str(batch.id),
        entity_type=batch.entity.entity_type if hasattr(batch.entity, "entity_type") else "",
        entity_id=str(batch.entity.entity_id) if hasattr(batch.entity, "entity_id") else str(batch.entity),
        batch_number=str(batch.batch_number),
        initial_quantity=batch.initial_quantity,
        current_quantity=batch.current_quantity,
        unit_cost=batch.unit_cost.amount,
        total_cost=batch.total_cost.amount,
        currency=batch.unit_cost.currency,
        status=batch.status.value if hasattr(batch.status, "value") else str(batch.status),
        production_date=batch.production_date,
        expiry_date=batch.expiry_date,
        location=str(batch.location) if batch.location else None,
        notes=batch.notes,
        created_at=batch.created_at,
        created_by=batch.created_by,
    )


def transfer_to_dto(transfer: StockTransfer) -> StockTransferDTO:
    return StockTransferDTO(
        id=str(transfer.id),
        entity_type=transfer.entity.entity_type if hasattr(transfer.entity, "entity_type") else "",
        entity_id=str(transfer.entity.entity_id) if hasattr(transfer.entity, "entity_id") else str(transfer.entity),
        quantity=transfer.quantity,
        unit_cost=transfer.unit_cost.amount,
        total_cost=transfer.total_cost.amount,
        currency=transfer.unit_cost.currency,
        from_location=str(transfer.from_location) if transfer.from_location else "",
        to_location=str(transfer.to_location) if transfer.to_location else "",
        status=transfer.status,
        reference_id=transfer.reference_id,
        batch_number=str(transfer.batch_number) if transfer.batch_number else None,
        notes=transfer.notes,
        created_at=transfer.created_at,
        created_by=transfer.created_by,
    )


def movements_to_dto_list(movements: Iterable[StockMovement]) -> List[StockMovementDTO]:
    return [movement_to_dto(m) for m in movements]


def batches_to_dto_list(batches: Iterable[StockBatch]) -> List[StockBatchDTO]:
    return [batch_to_dto(b) for b in batches]


def transfers_to_dto_list(transfers: Iterable[StockTransfer]) -> List[StockTransferDTO]:
    return [transfer_to_dto(t) for t in transfers]
