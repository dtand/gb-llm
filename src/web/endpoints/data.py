"""
Data system (schema and table) endpoints.
"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import SchemaUpdateRequest, DataRowRequest

router = APIRouter(prefix="/api/v2/projects/{project_id}", tags=["data"])


@router.get("/schema")
async def get_project_schema(project_id: str):
    """
    Get the data schema for a project.
    
    Returns the _schema.json contents and data stats.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    schema_path = project_path / "_schema.json"
    
    if not schema_path.exists():
        return {
            "exists": False,
            "schema": None,
            "tables": [],
            "stats": {}
        }
    
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing schema: {e}")
    
    # Get table stats
    tables = list(schema.get("tables", {}).keys())
    stats = {}
    
    for table_name in tables:
        data_path = project_path / "data" / f"{table_name}.json"
        if data_path.exists():
            try:
                with open(data_path) as f:
                    data = json.load(f)
                stats[table_name] = {
                    "row_count": len(data),
                    "file_exists": True
                }
            except:
                stats[table_name] = {"row_count": 0, "file_exists": True}
        else:
            stats[table_name] = {"row_count": 0, "file_exists": False}
    
    return {
        "exists": True,
        "schema": schema,
        "tables": tables,
        "stats": stats
    }


@router.put("/schema")
async def update_project_schema(project_id: str, request: SchemaUpdateRequest):
    """Update the data schema for a project."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    schema_path = project_path / "_schema.json"
    
    # Validate schema structure
    if "tables" not in request.schema:
        raise HTTPException(status_code=400, detail="Schema must contain 'tables' key")
    
    if "version" not in request.schema:
        request.schema["version"] = 1
    
    # Write schema
    with open(schema_path, "w") as f:
        json.dump(request.schema, f, indent=2)
    
    return {"success": True, "message": "Schema updated"}


@router.get("/data/{table_name}")
async def get_table_data(
    project_id: str, 
    table_name: str,
    search: str = None,
    sort_by: str = None,
    sort_desc: bool = False,
    offset: int = 0,
    limit: int = 100
):
    """Get data rows for a specific table with optional search/sort."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    schema_path = project_path / "_schema.json"
    data_path = project_path / "data" / f"{table_name}.json"
    
    # Load schema for field info
    if not schema_path.exists():
        raise HTTPException(status_code=404, detail="No schema found")
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    if table_name not in schema.get("tables", {}):
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not in schema")
    
    table_schema = schema["tables"][table_name]
    
    # Load data (or empty list)
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = []
    
    total_count = len(data)
    
    # Apply search filter (search all string fields)
    if search:
        search_lower = search.lower()
        string_fields = [
            name for name, field in table_schema.get("fields", {}).items()
            if field.get("type") == "string"
        ]
        
        filtered = []
        for row in data:
            for field in string_fields:
                if field in row and search_lower in str(row[field]).lower():
                    filtered.append(row)
                    break
        data = filtered
    
    # Apply sort
    if sort_by and sort_by in table_schema.get("fields", {}):
        data = sorted(data, key=lambda x: x.get(sort_by, 0) or 0, reverse=sort_desc)
    
    # Apply pagination
    paginated = data[offset:offset + limit]
    
    return {
        "table": table_name,
        "fields": table_schema.get("fields", {}),
        "description": table_schema.get("description", ""),
        "rows": paginated,
        "total_count": total_count,
        "filtered_count": len(data),
        "offset": offset,
        "limit": limit
    }


@router.post("/data/{table_name}")
async def create_data_row(project_id: str, table_name: str, request: DataRowRequest):
    """Create a new row in a data table."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    schema_path = project_path / "_schema.json"
    data_dir = project_path / "data"
    data_path = data_dir / f"{table_name}.json"
    
    # Load schema
    if not schema_path.exists():
        raise HTTPException(status_code=404, detail="No schema found")
    
    with open(schema_path) as f:
        schema = json.load(f)
    
    if table_name not in schema.get("tables", {}):
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not in schema")
    
    table_schema = schema["tables"][table_name]
    fields = table_schema.get("fields", {})
    
    # Load existing data
    data_dir.mkdir(exist_ok=True)
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = []
    
    # Handle auto-increment ID
    if "id" in fields and fields["id"].get("auto"):
        max_id = max((row.get("id", 0) for row in data), default=0)
        request.row["id"] = max_id + 1
    
    # Apply defaults for missing fields
    for field_name, field_def in fields.items():
        if field_name not in request.row and "default" in field_def:
            request.row[field_name] = field_def["default"]
    
    # Add row
    data.append(request.row)
    
    # Save
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "row": request.row, "id": request.row.get("id")}


@router.put("/data/{table_name}/{row_id}")
async def update_data_row(project_id: str, table_name: str, row_id: int, request: DataRowRequest):
    """Update an existing row in a data table."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    data_path = project_path / "data" / f"{table_name}.json"
    
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"No data file for table '{table_name}'")
    
    with open(data_path) as f:
        data = json.load(f)
    
    # Find and update row
    found = False
    for i, row in enumerate(data):
        if row.get("id") == row_id:
            # Preserve ID
            request.row["id"] = row_id
            data[i] = request.row
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail=f"Row with id {row_id} not found")
    
    # Save
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "row": request.row}


@router.delete("/data/{table_name}/{row_id}")
async def delete_data_row(project_id: str, table_name: str, row_id: int):
    """Delete a row from a data table."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    data_path = project_path / "data" / f"{table_name}.json"
    
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"No data file for table '{table_name}'")
    
    with open(data_path) as f:
        data = json.load(f)
    
    # Find and remove row
    original_len = len(data)
    data = [row for row in data if row.get("id") != row_id]
    
    if len(data) == original_len:
        raise HTTPException(status_code=404, detail=f"Row with id {row_id} not found")
    
    # Save
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "deleted_id": row_id}
