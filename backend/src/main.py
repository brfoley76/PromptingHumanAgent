"""
Main FastAPI application for the Agentic Learning Platform.
Provides REST API and WebSocket endpoints for frontend integration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import config
from .database.database import init_db
from .api import routes, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    # Startup
    print("🚀 Starting Agentic Learning Platform...")
    print(f"📚 Learning Module Path: {config.LEARNING_MODULE_PATH}")
    print(f"🤖 Agent Type: {config.AGENT_TYPE}")
    print(f"🔧 LLM Provider: {config.LLM_PROVIDER}")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Agentic Learning Platform...")


# Create FastAPI app
app = FastAPI(
    title="Agentic Learning Platform API",
    description="AI-powered tutoring and adaptive difficulty for learning modules",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api")
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Agentic Learning Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agent_type": config.AGENT_TYPE,
        "llm_configured": config.has_llm_configured()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG
    )
