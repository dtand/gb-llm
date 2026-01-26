"""
Snapshot and rollback endpoints.
"""
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import SnapshotInfo, CreateSnapshotRequest, RollbackRequest
from endpoints.websocket import manager

router = APIRouter(prefix="/api/v2/projects/{project_id}", tags=["snapshots"])


@router.get("/snapshots", response_model=list[SnapshotInfo])
async def list_project_snapshots(project_id: str):
    """List all snapshots for a project."""
    api = get_api()
    
    try:
        snapshots = api.list_snapshots(project_id)
        return [SnapshotInfo(**s) for s in snapshots]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/snapshots", response_model=SnapshotInfo)
async def create_project_snapshot(project_id: str, request: CreateSnapshotRequest):
    """Create a snapshot of the current project state."""
    api = get_api()
    
    try:
        snapshot = api.create_snapshot(project_id, request.description)
        return SnapshotInfo(**snapshot)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rollback")
async def rollback_project(project_id: str, request: RollbackRequest):
    """Rollback project to a previous snapshot."""
    api = get_api()
    
    try:
        result = api.rollback_to_snapshot(project_id, request.snapshot_id)
        
        # Broadcast status update via WebSocket
        await manager.broadcast(project_id, {
            "type": "status",
            "status": "scaffolded"
        })
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
