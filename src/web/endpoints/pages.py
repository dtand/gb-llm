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
    """Serve the workspace UI (main application)."""
    workspace_path = STATIC_DIR / "workspace.html"
    if workspace_path.exists():
        return workspace_path.read_text()
    return """
    <html>
        <head><title>GB Game Studio</title></head>
        <body>
            <h1>GB Game Studio</h1>
            <p>Workspace not found. Visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
    </html>
    """
