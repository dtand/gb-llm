"""
Project management endpoints (v2).
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import (
    CreateProjectRequest, CreateProjectResponse, TemplateInfo,
    ConversationTurnRequest, ConversationTurnResponse, BuildResponse
)

router = APIRouter(prefix="/api/v2/projects", tags=["projects"])


@router.get("/", tags=["templates"])
async def list_projects_v2(include_summary: bool = False):
    """
    List all projects with optional summaries.
    
    Set include_summary=true to get full context summaries (slower).
    """
    api = get_api()
    return api.list_projects(include_summary=include_summary)


@router.post("/", response_model=CreateProjectResponse, tags=["templates"])
async def create_project(request: CreateProjectRequest):
    """
    Create a new project, optionally forking from a template.
    
    If template_id is provided, the project will start with that
    sample's code as a base. Otherwise, an empty scaffold is created.
    """
    api = get_api()
    
    try:
        project = api.create_project(
            prompt=request.prompt,
            template_id=request.template_id,
            name=request.name
        )
        
        return CreateProjectResponse(
            project_id=project.id,
            name=project.name,
            template_source=project.template_source,
            message=f"Project created from template '{request.template_id}'" if request.template_id else "Empty project created"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}")
async def get_project_v2(project_id: str):
    """Get full project details including summary and conversation."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
        return project.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{project_id}")
async def delete_project_v2(project_id: str):
    """Delete a project and all its files."""
    api = get_api()
    
    try:
        api.delete_project(project_id)
        return {"message": "Project deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/summary")
async def get_project_summary(project_id: str):
    """Get the project's context summary."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
        if project.summary:
            return project.summary.to_dict()
        raise HTTPException(status_code=404, detail="Summary not generated")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project_id}/summary")
async def regenerate_summary(project_id: str):
    """Regenerate the project summary from current source files."""
    api = get_api()
    
    try:
        summary = api.update_summary(project_id)
        return summary.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/conversation")
async def get_conversation(project_id: str):
    """Get the project's conversation history."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
        return [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp,
                "metadata": turn.metadata
            }
            for turn in project.conversation
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project_id}/conversation", response_model=ConversationTurnResponse)
async def add_conversation_turn(project_id: str, request: ConversationTurnRequest):
    """Add a turn to the project's conversation history."""
    api = get_api()
    
    try:
        turn = api.add_conversation_turn(
            project_id=project_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata
        )
        return ConversationTurnResponse(
            role=turn.role,
            content=turn.content,
            timestamp=turn.timestamp
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project_id}/build", response_model=BuildResponse)
async def build_project(project_id: str):
    """
    Build the project (run make).
    
    Returns build success/failure, output, and ROM path if successful.
    """
    api = get_api()
    
    try:
        result = api.trigger_build(project_id)
        return BuildResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{project_id}/play")
async def play_project(project_id: str):
    """
    Launch the project ROM in SameBoy emulator.
    
    Opens the native SameBoy application with the built ROM file.
    Returns error if ROM doesn't exist (needs build first).
    """
    import subprocess
    import platform
    
    api = get_api()
    project = api.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find the ROM file
    project_dir = Path(project.path)
    build_dir = project_dir / "build"
    
    # Look for .gb files in build directory
    rom_files = list(build_dir.glob("*.gb"))
    if not rom_files:
        raise HTTPException(
            status_code=400, 
            detail="No ROM file found. Build the project first."
        )
    
    rom_path = rom_files[0]  # Use first ROM found
    
    # Launch SameBoy with the ROM
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", "SameBoy", str(rom_path)])
        elif platform.system() == "Linux":
            subprocess.Popen(["sameboy", str(rom_path)])
        elif platform.system() == "Windows":
            subprocess.Popen(["SameBoy.exe", str(rom_path)], shell=True)
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported platform: {platform.system()}"
            )
        
        return {
            "message": "Launched SameBoy",
            "rom_path": str(rom_path)
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="SameBoy emulator not found. Install it from https://sameboy.github.io/"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to launch emulator: {str(e)}"
        )
