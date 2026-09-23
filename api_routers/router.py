"""
YAseen ERP - Router Assembler
Includes all domain routers into the FastAPI app.
"""
from api_routers.shared.config import app

# Import all routers
from api_routers.health import router as health_router
from api_routers.auth import router as auth_router
from api_routers.accounting import router as accounting_router
from api_routers.customers import router as customers_router
from api_routers.products import router as products_router
from api_routers.suppliers import router as suppliers_router
from api_routers.invoices import router as invoices_router
from api_routers.purchasing import router as purchasing_router
from api_routers.payments import router as payments_router
from api_routers.funds import router as funds_router
from api_routers.inventory import router as inventory_router
from api_routers.reports import router as reports_router
from api_routers.settings import router as settings_router
from api_routers.projects import router as projects_router
from api_routers.workflows import router as workflows_router
from api_routers.reconciliation import router as reconciliation_router
from api_routers.sales_cycle.quotations_router import router as quotations_router
from api_routers.sales_cycle.orders_router import router as orders_router
from api_routers.sales_cycle.deliveries_router import router as deliveries_router
from api_routers.sales_cycle.picking_router import router as picking_router
from api_routers.sales_cycle.shipping_router import router as shipping_router
from api_routers.imports import router as imports_router
from api_routers.pos.sessions_router import router as pos_sessions_router
from api_routers.pos.receipts_router import router as pos_receipts_router
from api_routers.pos.sync_router import router as pos_sync_router

# Register all routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(accounting_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(suppliers_router)
app.include_router(invoices_router)
app.include_router(purchasing_router)
app.include_router(payments_router)
app.include_router(funds_router)
app.include_router(inventory_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(projects_router)
app.include_router(workflows_router)
app.include_router(reconciliation_router)
app.include_router(quotations_router)
app.include_router(orders_router)
app.include_router(deliveries_router)
app.include_router(picking_router)
app.include_router(shipping_router)
app.include_router(pos_sessions_router)
app.include_router(pos_receipts_router)
app.include_router(pos_sync_router)
app.include_router(imports_router)
