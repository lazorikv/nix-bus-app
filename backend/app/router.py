from fastapi import APIRouter

from app.modules.auth.routes import router as auth_router
from app.modules.buses.routes import router as buses_router
from app.modules.cities.routes import router as cities_router
from app.modules.orders.routes import router as orders_router
from app.modules.payment.routes import router as payment_router
from app.modules.trips.routes import router as trips_router


def create_router() -> APIRouter:
    router = APIRouter()
    for module_router in (
        auth_router,
        cities_router,
        buses_router,
        trips_router,
        orders_router,
        payment_router,
    ):
        router.include_router(module_router)
    return router
