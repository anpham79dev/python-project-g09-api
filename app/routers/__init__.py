from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.orders import router as orders_router
from app.routers.users import router as users_router
from app.routers.dashboard import router as dashboard_router
from app.routers.shifts import router as shifts_router
from app.routers.branches import router as branches_router
from app.routers.settings import router as settings_router
from app.routers.accounting import router as accounting_router
from app.routers.landing_config import router as landing_config_router
from app.routers.roles import router as roles_router

__all__ = [
    "auth_router",
    "products_router",
    "orders_router",
    "users_router",
    "dashboard_router",
    "shifts_router",
    "branches_router",
    "settings_router",
    "accounting_router",
    "landing_config_router",
    "roles_router",
]
