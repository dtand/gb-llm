"""
WebSocket connection manager for real-time progress updates.
"""
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections for real-time progress updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
    
    async def broadcast(self, project_id: str, message: dict):
        if project_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn, project_id)


# Singleton instance
manager = ConnectionManager()
