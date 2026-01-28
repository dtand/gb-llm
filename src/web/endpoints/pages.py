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
    """Serve the main application (index.html)."""
    # Try index.html first (modular version), fallback to workspace.html
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text()
    
    workspace_path = STATIC_DIR / "workspace.html"
    if workspace_path.exists():
        return workspace_path.read_text()
    
    return """
    <html>
        <head><title>GB Game Studio</title></head>
        <body>
            <h1>GB Game Studio</h1>
            <p>Application not found. Visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
    </html>
    """


@router.get("/workspace", response_class=HTMLResponse)
@router.get("/workspace/{project_id}", response_class=HTMLResponse)
async def workspace(project_id: str = None):
    """Serve the workspace UI (redirects to main app for backwards compatibility)."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text()
    
    workspace_path = STATIC_DIR / "workspace.html"
    if workspace_path.exists():
        return workspace_path.read_text()
    
    return """
    <html>
        <head><title>GB Game Studio</title></head>
        <body>
            <h1>GB Game Studio</h1>
            <p>Workspace not found.</p>
        </body>
    </html>
    """
