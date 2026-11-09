"""API Routers package."""

from api.routers.health import router as health_router
from api.routers.scholarships import router as scholarships_router
from api.routers.ingestion import router as ingestion_router

__all__ = ["health_router", "scholarships_router", "ingestion_router"]
