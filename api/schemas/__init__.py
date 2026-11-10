"""Pydantic schemas package."""

from api.schemas.health import HealthResponse
from api.schemas.scholarship import (
    ScholarshipDetail,
    ScholarshipFilterParams,
    ScholarshipRead,
)
from api.schemas.ingestion import (
    IngestionItem,
    IngestionItemResult,
    IngestionRequest,
    IngestionResponse,
)

__all__ = [
    "HealthResponse",
    "ScholarshipRead",
    "ScholarshipDetail",
    "ScholarshipFilterParams",
    "IngestionItem",
    "IngestionItemResult",
    "IngestionRequest",
    "IngestionResponse",
]
