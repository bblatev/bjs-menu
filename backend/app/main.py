"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Inventory Management System")

    # Create tables if they don't exist (for SQLite dev)
    # In production with PostgreSQL, use Alembic migrations
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (SQLite mode)")

    yield

    logger.info("Shutting down Inventory Management System")


app = FastAPI(
    title="Inventory Management System",
    description="Backend API for inventory scanning and management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Inventory Management System API",
        "docs": "/docs",
        "health": "/health",
    }
