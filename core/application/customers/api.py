# core/application/customers/api.py
"""
API Router for the Customers module.
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from core.application.customers.commands import ListCustomersQuery
from core.application.customers.dtos import CustomerDTO
from core.bootstrap.startup import get_query_bus
from core.infrastructure.messaging.query_bus import QueryBus

router = APIRouter()

@router.get("/", response_model=List[CustomerDTO])
async def list_customers(
    status: Optional[str] = Query(None, description="Filter by customer status (e.g., 'active')."),
    include_deleted: bool = Query(False, description="Include deleted customers in the results."),
    limit: int = Query(100, ge=1, le=1000, description="The maximum number of customers to return."),
    offset: int = Query(0, ge=0, description="The starting offset for pagination."),
    query_bus: QueryBus = Depends(get_query_bus)
):
    """
    Retrieve a list of customers.
    
    This endpoint allows for filtering and pagination of customer data.
    """
    query = ListCustomersQuery(
        status=status,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset
    )
    # The query bus will find the registered handler and execute it.
    customers: List[CustomerDTO] = await query_bus.handle_async(query)
    return customers
