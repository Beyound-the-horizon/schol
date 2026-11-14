from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai.config import API_V1_PREFIX, PROJECT_NAME, ALLOWED_ORIGINS, GEMINI_MODEL
from ai.router import router
from core.tools.db import ensure_schema_compatibility


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is ready and columns exist on startup
    try:
        ensure_schema_compatibility()
        print("[AI Service] Database schema verified and ready.")
    except Exception as e:
        print(f"[AI Service] Warning: Schema initialization check: {e}")
    yield


app = FastAPI(
    title=PROJECT_NAME,
    description="""
API layer for transforming raw academic scholarship records into actionable, intelligent application roadmaps:
- **Active Nested Apply URLs**: Resolves deep account creation & portal URLs.
- **Adaptive Application Architecture**: Dynamically tailors workflows for single-portal, course-first, and dual-application schemes.
- **Intelligent Timelines**: Synthesizes rough intake windows and deadlines when official announcements are pending.
- **Motivation Letter Specifications**: Exact word counts, character limits, and scoring criteria.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for local Vite development and frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["System"])
def healthcheck():
    return {
        "status": "healthy",
        "service": PROJECT_NAME,
        "model": GEMINI_MODEL,
        "api_version": "v1",
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": f" {PROJECT_NAME}",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_prefix": API_V1_PREFIX,
    }

