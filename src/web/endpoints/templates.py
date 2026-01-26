"""
Template/sample listing endpoints.
"""
from fastapi import APIRouter

from project_api import get_api
from endpoints.models import TemplateInfo

router = APIRouter(prefix="/api/v2/templates", tags=["templates"])


@router.get("/", response_model=list[TemplateInfo])
async def list_templates():
    """List all available templates (samples) for forking."""
    api = get_api()
    templates = api.list_templates()
    return [TemplateInfo(**t) for t in templates]
