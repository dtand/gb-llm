"""
Feedback submission endpoints.
"""
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import FeedbackRequest

router = APIRouter(prefix="/api/v2/projects/{project_id}/feedback", tags=["feedback"])


@router.post("/")
async def add_project_feedback(project_id: str, request: FeedbackRequest):
    """
    Add human feedback to the project.
    
    This updates both the metadata and regenerates the summary
    to include the feedback as a known issue.
    """
    api = get_api()
    
    try:
        api.add_feedback(
            project_id=project_id,
            feedback=request.feedback,
            rating=request.rating
        )
        return {"message": "Feedback added", "rating": request.rating}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
