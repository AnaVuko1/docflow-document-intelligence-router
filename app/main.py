"""
DocFlow - Document Intelligence Router
FastAPI application with CORS, static files, and API endpoints.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import logging

from app.config import settings
from app.database import init_db, close_db
from app.routes import pipelines, documents, jobs, connectors, dashboard
from app.schemas import ErrorResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting DocFlow v{settings.app_version} in {settings.app_env} mode")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Ensure upload and output directories exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.csv_output_dir, exist_ok=True)
    os.makedirs(settings.json_output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(settings.sqlite_output_db), exist_ok=True)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DocFlow...")
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Declarative document pipelines. Define. Route. Transform.",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount templates directory for potential future use
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if os.path.exists(templates_dir):
    app.mount("/templates", StaticFiles(directory=templates_dir), name="templates")

# Include routers
app.include_router(pipelines.router, prefix="/api/v1", tags=["pipelines"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(connectors.router, prefix="/api/v1", tags=["connectors"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint redirects to dashboard or API docs.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DocFlow - Document Intelligence Router</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                margin: 0;
                padding: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
            }
            .container {
                max-width: 800px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            }
            h1 {
                font-size: 3em;
                margin-bottom: 10px;
                background: linear-gradient(90deg, #fff, #e0e0e0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .tagline {
                font-size: 1.2em;
                margin-bottom: 30px;
                opacity: 0.9;
            }
            .buttons {
                display: flex;
                gap: 20px;
                justify-content: center;
                flex-wrap: wrap;
                margin-top: 30px;
            }
            .btn {
                padding: 15px 30px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                transition: all 0.3s ease;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            .btn:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            }
            .btn-primary {
                background: #4CAF50;
                border-color: #4CAF50;
            }
            .btn-primary:hover {
                background: #45a049;
            }
            .features {
                text-align: left;
                margin-top: 40px;
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 10px;
            }
            .features h3 {
                margin-top: 0;
            }
            .features ul {
                padding-left: 20px;
            }
            .features li {
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>DocFlow</h1>
            <div class="tagline">Declarative document pipelines. Define. Route. Transform.</div>
            
            <p>Open-source infrastructure for document workflows.</p>
            
            <div class="buttons">
                <a href="/docs" class="btn btn-primary">API Documentation</a>
                <a href="/api/v1/dashboard" class="btn">Dashboard</a>
                <a href="https://github.com/docflow-dev/docflow" class="btn">GitHub</a>
            </div>
            
            <div class="features">
                <h3>✨ Key Features</h3>
                <ul>
                    <li><strong>Declarative Pipelines</strong>: Define workflows in clean YAML</li>
                    <li><strong>Smart Classification</strong>: Auto-detect document types</li>
                    <li><strong>Multiple Extractors</strong>: Regex, templates, and extensible LLM support</li>
                    <li><strong>Schema Validation</strong>: Business rules and type checking</li>
                    <li><strong>Data Transformation</strong>: Field mapping and format conversion</li>
                    <li><strong>Output Connectors</strong>: CSV, JSON, SQLite, webhooks, and more</li>
                </ul>
            </div>
            
            <div style="margin-top: 40px; font-size: 0.9em; opacity: 0.8;">
                <p>Version: """ + settings.app_version + """ | Environment: """ + settings.app_env + """</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    Returns application status and version.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "debug": settings.debug,
    }


@app.get("/api/v1", tags=["api"])
async def api_root():
    """
    API root endpoint with available resources.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "pipelines": "/api/v1/pipelines",
            "documents": "/api/v1/documents",
            "jobs": "/api/v1/jobs",
            "connectors": "/api/v1/connectors",
            "dashboard": "/api/v1/dashboard",
            "docs": "/docs",
        },
        "description": "Document Intelligence Router API",
    }


# Global exception handler
from fastapi.responses import JSONResponse

# ... then fix handlers:
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "details": {"status_code": exc.status_code},
            "code": "HTTP_ERROR"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": {"exception": str(exc)} if settings.debug else {},
            "code": "INTERNAL_ERROR"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
    )