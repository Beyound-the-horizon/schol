"""Authenticated crawler ingestion endpoint router."""

import secrets
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.config import settings
from api.db import get_db_session
from api.schemas.ingestion import IngestionRequest, IngestionResponse
from api.services.ingestion_service import IngestionService

router = APIRouter(prefix="/scholarships", tags=["Ingestion"])


async def verify_ingestion_token(
    x_ingestion_token: Annotated[Optional[str], Header(alias="X-Ingestion-Token")] = None,
    authorization: Annotated[Optional[str], Header()] = None,
) -> None:
    """Validate crawler ingestion authorization token securely.
    
    Checks X-Ingestion-Token header first, then Authorization: Bearer <token>.
    Uses constant-time comparison to prevent timing side-channel attacks.
    """
    token_to_verify = x_ingestion_token

    if not token_to_verify and authorization and authorization.startswith("Bearer "):
        token_to_verify = authorization[7:].strip()

    if not token_to_verify:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing crawler ingestion token. Supply X-Ingestion-Token header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_token = settings.ingestion_token
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server ingestion token is not configured.",
        )

    is_valid = secrets.compare_digest(token_to_verify, expected_token)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid crawler ingestion token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest Crawler Scholarship Batch",
    description=(
        "Authenticated ingestion endpoint for crawler teammates to submit discovered "
        "and structured scholarships. Deduplicates based on official_url."
    ),
    responses={
        401: {"description": "Missing or invalid ingestion token"},
        422: {"description": "Payload validation error"},
    },
)
async def ingest_scholarships(
    request: IngestionRequest,
    _auth: None = Depends(verify_ingestion_token),
    session: AsyncSession = Depends(get_db_session),
) -> IngestionResponse:
    """Process incoming batch of scraped scholarship records."""
    return await IngestionService.ingest_batch(session, request)
