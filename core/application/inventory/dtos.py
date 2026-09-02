from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class StockMovementDTO:
    id: str
    entity_type: str
    entity_id: str
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    currency: str = "USD"
    reference_type: str = ""
    reference_id: str = ""
    batch_number: Optional[str] = None
    location: Optional[str] = None
    notes: str = ""
    created_at: Optional[datetime] = None
    created_by: str = "system"


@dataclass
class StockBatchDTO:
    id: str
    entity_type: str
    entity_id: str
    batch_number: str
    initial_quantity: Decimal
    current_quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    currency: str = "USD"
    status: str = "active"
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""
    created_at: Optional[datetime] = None
    created_by: str = "system"


@dataclass
class StockTransferDTO:
    id: str
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    currency: str = "USD"
    from_location: str = ""
    to_location: str = ""
    status: str = "pending"
    reference_id: str = ""
    batch_number: Optional[str] = None
    notes: str = ""
    created_at: Optional[datetime] = None
    created_by: str = "system"


@dataclass
class StockValuationDTO:
    entity_type: str
    entity_id: str
    total_quantity: Decimal
    total_cost: Decimal
    average_cost: Decimal
    currency: str = "USD"
    valuation_method: str = "fifo"
    as_of_date: Optional[date] = None


@dataclass
class StockSummaryDTO:
    entity_type: str
    entity_id: str
    current_quantity: Decimal
    total_inbound: Decimal
    total_outbound: Decimal
    net_movement: Decimal
    total_cost: Decimal
    currency: str = "USD"
    last_movement_date: Optional[datetime] = None
    batch_count: int = 0


__all__ = [
    "StockMovementDTO",
    "StockBatchDTO",
    "StockTransferDTO",
    "StockValuationDTO",
    "StockSummaryDTO",
]