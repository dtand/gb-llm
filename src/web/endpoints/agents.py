"""
Agent configuration endpoints.
"""
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import AgentConfigUpdate

router = APIRouter(prefix="/api/v2/projects/{project_id}/agents", tags=["agents"])


@router.get("/")
async def get_agent_config(project_id: str):
    """
    Get agent configuration for this project.
    
    Returns merged config (project overrides on top of defaults)
    plus available models list.
    """
    api = get_api()
    
    try:
        return api.get_agent_config(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{agent_name}")
async def update_agent_config(project_id: str, agent_name: str, request: AgentConfigUpdate):
    """
    Update configuration for a specific agent.
    
    Args:
        agent_name: One of "designer", "coder", "reviewer"
        
    Body:
        enabled: Whether this agent is active
        model: Claude model to use
    """
    api = get_api()
    
    try:
        config = {}
        if request.enabled is not None:
            config["enabled"] = request.enabled
        if request.model is not None:
            config["model"] = request.model
        
        return api.update_agent_config(project_id, agent_name, config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
