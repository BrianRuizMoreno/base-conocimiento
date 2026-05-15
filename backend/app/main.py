"""
RAG System - FastAPI Application
Main entry point with lifespan events and middleware.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.api import auth, collections, documents, chat, analysis, settings, integration, admin
from app.core.config import settings as app_settings
from app.db.database import engine
from app.db.models import Base

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting RAG System...")
    async with engine.begin() as conn:
        # Create tables if they don't exist (dev only)
        # In production, use alembic migrations
        pass
    yield
    # Shutdown
    logger.info("Shutting down RAG System...")
    await engine.dispose()


app = FastAPI(
    title="RAG System API",
    description="Multi-document RAG system with knowledge graph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "code": "INTERNAL_ERROR"}
    )


# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(collections.router, prefix="/api/v1/collections", tags=["Collections"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(integration.router, prefix="/api/v1/integration", tags=["Integration"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "RAG System API", "docs": "/docs"}
