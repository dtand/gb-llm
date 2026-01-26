"""
WebSocket endpoint for real-time progress updates.
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from project_api import get_api, PROJECTS_DIR
from endpoints.websocket import manager

router = APIRouter()


@router.websocket("/ws/projects/{project_id}")
async def websocket_progress(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await manager.connect(websocket, project_id)
    try:
        # Send current status immediately
        project_dir = PROJECTS_DIR / project_id
        if project_dir.exists():
            metadata_path = project_dir / "metadata.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())
                await websocket.send_json({
                    "type": "status",
                    "status": metadata.get("status", "unknown"),
                })
        
        # Keep connection alive
        while True:
            try:
                # Wait for any message (ping/pong or close)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )
                # Echo back pings
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send ping to keep alive
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, project_id)
