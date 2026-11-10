"""Health check endpoint router."""

from fastapi import APIRouter, Response, status
from api.config import settings
from api.db import check_db_health
from api.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application & Database Health Check",
    description="Reports the service status and checks database connection health separately.",
    responses={
        200: {"description": "Service is healthy or degraded"},
        503: {"description": "Database connectivity failure / service degraded"},
    },
)
async def get_health(response: Response) -> HealthResponse:
    """Check application status and database connectivity."""
    db_ok, db_status = await check_db_health()

    if db_ok:
        return HealthResponse(
            status="healthy",
            environment=settings.environment,
            database=db_status,
            version="1.0.0",
        )

    # If database is unavailable, return degraded status with 503 HTTP status
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="degraded",
        environment=settings.environment,
        database=db_status,
        version="1.0.0",
    )
