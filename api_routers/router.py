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
from api_routers.workflows import router as workflows_router
from api_routers.reconciliation import router as reconciliation_router

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
app.include_router(workflows_router)
app.include_router(reconciliation_router)
