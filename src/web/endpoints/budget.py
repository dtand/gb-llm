"""
ROM budget analysis endpoints.
"""
import json
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

from project_api import get_api

router = APIRouter(prefix="/api/v2/projects/{project_id}/budget", tags=["budget"])

# For budget generation
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@router.get("/")
async def get_rom_budget(project_id: str):
    """
    Get the ROM budget report for a project.
    
    Returns the rom_budget.json if it exists (generated during build).
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    budget_path = project_path / "build" / "rom_budget.json"
    
    if not budget_path.exists():
        # Try to generate it
        schema_path = project_path / "_schema.json"
        if schema_path.exists():
            try:
                # Import and run generator
                sys.path.insert(0, str(PROJECT_ROOT / "src" / "generator"))
                from data_generator import calculate_budget, load_schema
                
                schema = load_schema(project_path)
                budget = calculate_budget(schema, project_path)
                
                return budget
            except Exception as e:
                return {
                    "exists": False,
                    "error": str(e),
                    "message": "Budget not yet generated. Build the project first."
                }
        else:
            return {
                "exists": False,
                "message": "No schema found for this project"
            }
    
    with open(budget_path) as f:
        budget = json.load(f)
    
    budget["exists"] = True
    return budget
