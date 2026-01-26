"""
Frontend page serving endpoints.
"""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STATIC_DIR = Path(__file__).parent.parent / "static"


@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return """
    <html>
        <head><title>GB Game Studio</title></head>
        <body>
            <h1>GB Game Studio API</h1>
            <p>Frontend not found. Visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
    </html>
    """


@router.get("/workspace", response_class=HTMLResponse)
async def workspace():
    """Serve the workspace UI."""
    workspace_path = STATIC_DIR / "workspace.html"
    if workspace_path.exists():
        return workspace_path.read_text()
    return """
    <html>
        <head><title>GB Game Studio - Workspace</title></head>
        <body>
            <h1>Workspace not found</h1>
            <p>Visit <a href="/">/</a> for the main interface.</p>
        </body>
    </html>
    """
