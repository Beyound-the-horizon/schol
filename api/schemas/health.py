"""Health check response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status response payload."""

    status: str = Field(..., description="Overall service status (healthy, degraded, unhealthy)")
    environment: str = Field(..., description="Runtime environment name")
    database: str = Field(..., description="Database connectivity status (connected, disconnected)")
    version: str = Field(default="1.0.0", description="API version identifier")
