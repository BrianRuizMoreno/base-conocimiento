"""
RAG System - FastAPI Application
Main entry point with lifespan events and middleware.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import subprocess

from app.api import auth, collections, documents, chat, analysis, settings, integration, admin
from app.core.config import settings as app_settings
from app.db.database import engine

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
    try:
        # Run migrations
        logger.info("Running database migrations...")
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd="/app",
            check=True,
            capture_output=True
        )
        logger.info("Migrations completed.")
        
        # Run seed
        logger.info("Running database seed...")
        subprocess.run(
            ["python", "-m", "app.db.seed"],
            cwd="/app",
            check=True,
            capture_output=True
        )
        logger.info("Seed completed.")
    except Exception as e:
        logger.warning(f"Migration/seed error (may already exist): {e}")
    
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
    """Health check endpoint."""
    try:
        # Check database connection
        from app.db.database import SessionLocal
        async with SessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        
        return {
            "status": "ok",
            "version": "1.0.0",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/")
async def root():
    return {"message": "RAG System API", "docs": "/docs", "version": "1.0.0"}
