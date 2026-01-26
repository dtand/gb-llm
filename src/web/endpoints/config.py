"""
Config schema endpoints - extracts schema from C code annotations.

This provides an alternative to _schema.json where the C code is the source of truth.
Schema is defined via @config/@field annotations in header files.
"""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.utils import parse_config_schema_from_c

router = APIRouter(prefix="/api/v2/projects/{project_id}/config", tags=["config"])


@router.get("/schema")
async def get_config_schema(project_id: str):
    """
    Extract schema from @config annotations in C code.
    
    Scans .h files for @config/@field annotations and returns
    the schema in the same format as _schema.json.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    src_dir = Path(project.path) / "src"
    
    if not src_dir.exists():
        return {
            "tables": {},
            "source": "annotations",
            "files_scanned": 0
        }
    
    all_tables = {}
    files_scanned = 0
    
    # Scan all .h files for @config annotations
    for filepath in src_dir.glob("*.h"):
        try:
            content = filepath.read_text()
            relative_path = f"src/{filepath.name}"
            tables = parse_config_schema_from_c(content, relative_path)
            
            for table in tables:
                table_name = table["name"]
                all_tables[table_name] = {
                    "description": table["description"],
                    "fields": table["fields"],
                    "field_order": table["field_order"],
                    "source_file": table["file"],
                    "source_line": table["line"]
                }
            
            files_scanned += 1
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
    
    # Also check for data files to get row counts
    data_dir = Path(project.path) / "data"
    stats = {}
    
    for table_name in all_tables:
        data_path = data_dir / f"{table_name}.json"
        if data_path.exists():
            try:
                with open(data_path) as f:
                    data = json.load(f)
                stats[table_name] = {
                    "row_count": len(data),
                    "has_data": True
                }
            except:
                stats[table_name] = {"row_count": 0, "has_data": True}
        else:
            stats[table_name] = {"row_count": 0, "has_data": False}
    
    return {
        "tables": all_tables,
        "table_names": list(all_tables.keys()),
        "stats": stats,
        "source": "annotations",
        "files_scanned": files_scanned
    }


@router.get("/data/{table_name}")
async def get_config_table_data(
    project_id: str,
    table_name: str,
    offset: int = 0,
    limit: int = 100
):
    """
    Get data rows for a config table.
    
    Schema comes from C annotations, data from data/{table}.json.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    src_dir = project_path / "src"
    data_path = project_path / "data" / f"{table_name}.json"
    
    # Find schema from C annotations
    table_schema = None
    for filepath in src_dir.glob("*.h"):
        try:
            content = filepath.read_text()
            tables = parse_config_schema_from_c(content, f"src/{filepath.name}")
            for table in tables:
                if table["name"] == table_name:
                    table_schema = table
                    break
            if table_schema:
                break
        except:
            continue
    
    if not table_schema:
        raise HTTPException(
            status_code=404, 
            detail=f"Table '{table_name}' not found in @config annotations"
        )
    
    # Load data
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = []
    
    total_count = len(data)
    paginated = data[offset:offset + limit]
    
    return {
        "table": table_name,
        "description": table_schema["description"],
        "fields": table_schema["fields"],
        "field_order": table_schema["field_order"],
        "rows": paginated,
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
        "source_file": table_schema["file"]
    }


@router.post("/data/{table_name}")
async def create_config_row(project_id: str, table_name: str, row: dict):
    """Create a new row in a config table."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    src_dir = project_path / "src"
    data_dir = project_path / "data"
    data_path = data_dir / f"{table_name}.json"
    
    # Find schema from C annotations
    table_schema = None
    for filepath in src_dir.glob("*.h"):
        try:
            content = filepath.read_text()
            tables = parse_config_schema_from_c(content, f"src/{filepath.name}")
            for table in tables:
                if table["name"] == table_name:
                    table_schema = table
                    break
            if table_schema:
                break
        except:
            continue
    
    if not table_schema:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' not found in @config annotations"
        )
    
    # Load existing data
    data_dir.mkdir(exist_ok=True)
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)
    else:
        data = []
    
    # Handle auto-increment ID
    fields = table_schema["fields"]
    if "id" in fields and fields["id"].get("auto"):
        max_id = max((r.get("id", 0) for r in data), default=0)
        row["id"] = max_id + 1
    
    # Apply defaults for missing fields
    for field_name, field_def in fields.items():
        if field_name not in row and "default" in field_def:
            row[field_name] = field_def["default"]
    
    # Validate against schema
    errors = validate_row(row, fields)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    
    data.append(row)
    
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "row": row}


@router.put("/data/{table_name}/{row_id}")
async def update_config_row(project_id: str, table_name: str, row_id: int, row: dict):
    """Update a row in a config table."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    project_path = Path(project.path)
    src_dir = project_path / "src"
    data_path = project_path / "data" / f"{table_name}.json"
    
    # Find schema
    table_schema = None
    for filepath in src_dir.glob("*.h"):
        try:
            content = filepath.read_text()
            tables = parse_config_schema_from_c(content, f"src/{filepath.name}")
            for table in tables:
                if table["name"] == table_name:
                    table_schema = table
                    break
            if table_schema:
                break
        except:
            continue
    
    if not table_schema:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"No data file for '{table_name}'")
    
    with open(data_path) as f:
        data = json.load(f)
    
    # Find and update row
    found = False
    for i, existing in enumerate(data):
        if existing.get("id") == row_id:
            row["id"] = row_id  # Preserve ID
            
            # Validate
            errors = validate_row(row, table_schema["fields"])
            if errors:
                raise HTTPException(status_code=400, detail={"errors": errors})
            
            data[i] = row
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found")
    
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "row": row}


@router.delete("/data/{table_name}/{row_id}")
async def delete_config_row(project_id: str, table_name: str, row_id: int):
    """Delete a row from a config table."""
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    data_path = Path(project.path) / "data" / f"{table_name}.json"
    
    if not data_path.exists():
        raise HTTPException(status_code=404, detail=f"No data file for '{table_name}'")
    
    with open(data_path) as f:
        data = json.load(f)
    
    original_len = len(data)
    data = [r for r in data if r.get("id") != row_id]
    
    if len(data) == original_len:
        raise HTTPException(status_code=404, detail=f"Row {row_id} not found")
    
    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "deleted_id": row_id}


def validate_row(row: dict, fields: dict) -> list[str]:
    """Validate a row against field definitions."""
    errors = []
    
    for field_name, field_def in fields.items():
        value = row.get(field_name)
        field_type = field_def.get("type")
        
        # Check required
        if field_def.get("required") and value is None:
            errors.append(f"{field_name}: required field is missing")
            continue
        
        if value is None:
            continue
        
        # Type-specific validation
        if field_type in ("uint8", "int8", "uint16", "int16"):
            if not isinstance(value, (int, float)):
                errors.append(f"{field_name}: expected number, got {type(value).__name__}")
            else:
                min_val = field_def.get("min")
                max_val = field_def.get("max")
                if min_val is not None and value < min_val:
                    errors.append(f"{field_name}: value {value} below minimum {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"{field_name}: value {value} above maximum {max_val}")
        
        elif field_type == "string":
            if not isinstance(value, str):
                errors.append(f"{field_name}: expected string, got {type(value).__name__}")
            else:
                max_len = field_def.get("length", 255)
                if len(value) > max_len:
                    errors.append(f"{field_name}: string too long ({len(value)} > {max_len})")
        
        elif field_type == "enum":
            allowed = field_def.get("values", [])
            if value not in allowed:
                errors.append(f"{field_name}: invalid value '{value}', must be one of {allowed}")
        
        elif field_type == "bool":
            if not isinstance(value, bool) and value not in (0, 1):
                errors.append(f"{field_name}: expected boolean")
    
    return errors
