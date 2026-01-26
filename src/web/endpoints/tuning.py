"""
Tunable parameter endpoints.
"""
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import UpdateTunablesRequest
from endpoints.utils import parse_tunables_from_c

router = APIRouter(prefix="/api/v2/projects/{project_id}/tuning", tags=["tuning"])


@router.get("/")
async def get_project_tunables(project_id: str):
    """
    Parse and return all tunable parameters from the project.
    
    Scans .h and .c files for @tunable annotations.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    src_dir = Path(project.path) / "src"
    
    if not src_dir.exists():
        return {"tunables": [], "categories": []}
    
    all_tunables = []
    
    # Scan all .h and .c files
    for ext in ['*.h', '*.c']:
        for filepath in src_dir.glob(ext):
            try:
                content = filepath.read_text()
                relative_path = f"src/{filepath.name}"
                tunables = parse_tunables_from_c(content, relative_path)
                all_tunables.extend(tunables)
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
    
    # Extract unique categories
    categories = sorted(set(t["category"] for t in all_tunables))
    
    # Group by category for easier UI rendering
    by_category = {}
    for t in all_tunables:
        cat = t["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(t)
    
    return {
        "tunables": all_tunables,
        "categories": categories,
        "by_category": by_category,
        "total_count": len(all_tunables)
    }


@router.put("/")
async def update_project_tunables(project_id: str, request: UpdateTunablesRequest):
    """
    Update tunable parameter values and optionally rebuild.
    
    Modifies the #define values in the source files.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    
    # Group updates by file
    updates_by_file = {}
    for update in request.updates:
        if update.file not in updates_by_file:
            updates_by_file[update.file] = []
        updates_by_file[update.file].append(update)
    
    modified_files = []
    
    for file_path, updates in updates_by_file.items():
        full_path = project_path / file_path
        
        if not full_path.exists():
            continue
        
        content = full_path.read_text()
        
        for update in updates:
            # Replace the #define value
            pattern = rf'(#define\s+{re.escape(update.name)}\s+)\(?-?\d+\)?'
            
            # Preserve parentheses for negative values
            new_value = str(update.value)
            if update.value < 0:
                new_value = f'({update.value})'
            
            replacement = rf'\g<1>{new_value}'
            
            new_content, count = re.subn(pattern, replacement, content)
            
            if count > 0:
                content = new_content
        
        # Write back
        full_path.write_text(content)
        modified_files.append(file_path)
    
    return {
        "success": True,
        "modified_files": modified_files,
        "message": f"Updated {len(request.updates)} tunable(s)"
    }
