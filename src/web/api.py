#!/usr/bin/env python3
"""
GB Game Studio - Web API

FastAPI server providing REST endpoints and WebSocket for real-time progress.

This is the main entry point that imports all endpoint routers from the
endpoints/ directory.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load environment
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add paths for imports
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "web"))  # For endpoints package
sys.path.insert(0, str(PROJECT_ROOT / "src" / "agents"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "agents" / "planner"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "agents" / "coder"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "agents" / "verifier"))

from project_api import PROJECTS_DIR

# Import all routers from local endpoints package
from endpoints.utils import active_tasks
from endpoints import pages, projects, templates, agents, files
from endpoints import sprites, tuning, data, budget, snapshots, feedback
from endpoints import pipeline, ws, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Ensure projects directory exists
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cancel any active tasks on shutdown
    for task in active_tasks.values():
        if hasattr(task, 'cancel'):
            task.cancel()


app = FastAPI(
    title="GB Game Studio API",
    description="Generate GameBoy ROMs from natural language descriptions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register all routers
app.include_router(pages.router)
app.include_router(templates.router)
app.include_router(projects.router)
app.include_router(agents.router)
app.include_router(files.router)
app.include_router(sprites.router)
app.include_router(tuning.router)
app.include_router(data.router)
app.include_router(config.router)
app.include_router(budget.router)
app.include_router(snapshots.router)
app.include_router(feedback.router)
app.include_router(pipeline.router)
app.include_router(pipeline.generate_router)  # /api/v2/generate
app.include_router(ws.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
