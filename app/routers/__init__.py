# Routers package

from .webhook import router as webhook_router
from .web import router as web_router
from .payments import router as payments_router
from .services import router as services_router
from .plans import router as plans_router
from .expenses import router as expenses_router
from .dashboard import router as dashboard_router

__all__ = [
    "webhook_router",
    "web_router",
    "payments_router",
    "services_router",
    "plans_router",
    "expenses_router",
    "dashboard_router"
]