"""
File content access endpoints.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from project_api import get_api

router = APIRouter(prefix="/api/v2/projects/{project_id}/files", tags=["files"])


@router.get("/rom")
async def get_rom(project_id: str):
    """Download the ROM file for a project."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Find ROM file in build directory
    build_dir = Path(project.path) / "build"
    rom_file = None
    
    # Check if rom_path is in metadata
    if project.rom_path:
        rom_file = Path(project.rom_path)
        if not rom_file.exists():
            rom_file = None
    
    # Fallback: search for .gb file in build
    if not rom_file and build_dir.exists():
        for f in build_dir.glob("*.gb"):
            rom_file = f
            break
    
    if not rom_file or not rom_file.exists():
        raise HTTPException(status_code=404, detail="ROM file not found. Build the project first.")
    
    return FileResponse(
        path=str(rom_file),
        filename=rom_file.name,
        media_type="application/octet-stream"
    )


@router.get("/{file_path:path}")
async def get_file_content(project_id: str, file_path: str):
    """Get the content of a file in the project."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Build full path and validate it's within project
    full_path = Path(project.path) / file_path
    
    # Security check - ensure path is within project
    try:
        full_path.resolve().relative_to(Path(project.path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    
    try:
        content = full_path.read_text()
        return {
            "path": file_path,
            "content": content,
            "size": len(content),
            "lines": content.count('\n') + 1
        }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file cannot be displayed")
