from fastapi import APIRouter

from app.api.routes.analyse import router as analyse_router
from app.api.routes.categorize import router as categorize_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.orders import router as orders_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/api")
api_router.include_router(chat_router, prefix="/api")
api_router.include_router(categorize_router, prefix="/api")
api_router.include_router(analyse_router, prefix="/api")
api_router.include_router(orders_router, prefix="/api")