#!/usr/bin/env python3
"""
Data Generator - Converts JSON schema and data files to C code for Game Boy.

Usage:
    python data_generator.py <project_path>
    
Reads:
    <project_path>/_schema.json
    <project_path>/data/*.json
    
Outputs:
    <project_path>/build/data.h
    <project_path>/build/data.c
    <project_path>/build/rom_budget.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Size in bytes for each field type
TYPE_SIZES = {
    "uint8": 1,
    "int8": 1,
    "uint16": 2,
    "int16": 2,
    "bool": 1,
    "enum": 1,
    "ref": 1,
}

# C type mapping
TYPE_C_MAP = {
    "uint8": "uint8_t",
    "int8": "int8_t",
    "uint16": "uint16_t",
    "int16": "int16_t",
    "bool": "uint8_t",
    "enum": None,  # Uses generated enum type
    "ref": "uint8_t",
    "string": "char",
}

BANK_SIZE = 16384  # 16KB per ROM bank
WARNING_THRESHOLD = 0.8  # 80% warning


def snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def snake_to_upper(name: str) -> str:
    """Convert snake_case to UPPER_SNAKE_CASE."""
    return name.upper()


def load_schema(project_path: Path) -> dict:
    """Load and validate the schema file."""
    schema_path = project_path / "_schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    
    with open(schema_path) as f:
        return json.load(f)


def load_data(project_path: Path, table_name: str) -> list[dict]:
    """Load data for a specific table."""
    data_path = project_path / "data" / f"{table_name}.json"
    if not data_path.exists():
        return []
    
    with open(data_path) as f:
        return json.load(f)


def calculate_row_size(fields: dict) -> int:
    """Calculate the size in bytes of one row."""
    size = 0
    for field_name, field_def in fields.items():
        field_type = field_def["type"]
        if field_type == "string":
            # Add +1 for null terminator
            size += field_def.get("length", 16) + 1
        else:
            size += TYPE_SIZES.get(field_type, 1)
    return size


def collect_enums(schema: dict) -> dict[str, list[str]]:
    """Collect all unique enum definitions across tables."""
    enums = {}
    for table_name, table_def in schema.get("tables", {}).items():
        for field_name, field_def in table_def.get("fields", {}).items():
            if field_def["type"] == "enum":
                values = tuple(field_def["values"])
                # Create enum name from field name
                enum_name = snake_to_pascal(field_name)
                # Track unique enums by their values
                enums[enum_name] = list(values)
    return enums


def generate_enum_code(enum_name: str, values: list[str]) -> str:
    """Generate C enum definition."""
    lines = [f"typedef enum {{"]
    for i, value in enumerate(values):
        const_name = f"{snake_to_upper(enum_name)}_{snake_to_upper(value)}"
        lines.append(f"    {const_name} = {i},")
    lines.append(f"}} {enum_name};")
    return "\n".join(lines)


def generate_struct_code(table_name: str, fields: dict, enums: dict) -> str:
    """Generate C struct definition."""
    struct_name = snake_to_pascal(table_name)
    # Singularize (simple version - just remove trailing 's')
    if struct_name.endswith("ies"):
        struct_name = struct_name[:-3] + "y"
    elif struct_name.endswith("s") and not struct_name.endswith("ss"):
        struct_name = struct_name[:-1]
    
    lines = [f"typedef struct {{"]
    for field_name, field_def in fields.items():
        field_type = field_def["type"]
        
        if field_type == "string":
            # Add +1 for null terminator
            length = field_def.get("length", 16) + 1
            lines.append(f"    char {field_name}[{length}];")
        elif field_type == "enum":
            enum_type = snake_to_pascal(field_name)
            lines.append(f"    {enum_type} {field_name};")
        else:
            c_type = TYPE_C_MAP.get(field_type, "uint8_t")
            lines.append(f"    {c_type} {field_name};")
    
    lines.append(f"}} {struct_name};")
    return "\n".join(lines), struct_name


def format_value(value: Any, field_def: dict) -> str:
    """Format a value for C code."""
    field_type = field_def["type"]
    
    if value is None:
        if field_type == "ref":
            return "0"  # NULL ref
        elif field_type == "string":
            return '""'
        elif field_type == "bool":
            return "0"
        else:
            return "0"
    
    if field_type == "string":
        # Escape and truncate string
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif field_type == "bool":
        return "1" if value else "0"
    elif field_type == "enum":
        enum_name = snake_to_pascal(field_def.get("_field_name", ""))
        return f"{snake_to_upper(enum_name)}_{snake_to_upper(str(value))}"
    elif field_type == "ref":
        return str(value) if value else "0"
    else:
        return str(value)


def generate_data_array(table_name: str, struct_name: str, fields: dict, data: list[dict]) -> str:
    """Generate C array of data."""
    # Add field name to field_def for enum formatting
    fields_with_names = {}
    for name, fdef in fields.items():
        fields_with_names[name] = {**fdef, "_field_name": name}
    
    var_name = table_name.lower()
    lines = [f"const {struct_name} {var_name}[] = {{"]
    
    for row in data:
        values = []
        for field_name, field_def in fields_with_names.items():
            value = row.get(field_name, field_def.get("default"))
            values.append(format_value(value, field_def))
        
        lines.append(f"    {{{', '.join(values)}}},")
    
    lines.append("};")
    return "\n".join(lines)


def singularize(name: str) -> str:
    """Simple singularization for common patterns."""
    if name.endswith("ies"):
        return name[:-3] + "y"
    elif name.endswith("es") and name[-3] in "shxz":
        return name[:-2]
    elif name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def generate_accessor(table_name: str, struct_name: str) -> tuple[str, str]:
    """Generate accessor function declaration and definition."""
    var_name = table_name.lower()
    singular = singularize(var_name)
    func_name = f"get_{singular}"
    count_name = f"{snake_to_upper(struct_name)}_COUNT"
    
    decl = f"const {struct_name}* {func_name}(uint8_t id);"
    
    impl = f"""const {struct_name}* {func_name}(uint8_t id) {{
    for (uint8_t i = 0; i < {count_name}; i++) {{
        if ({var_name}[i].id == id) return &{var_name}[i];
    }}
    return 0;
}}"""
    
    return decl, impl


def generate_header(schema: dict, enums: dict, structs: list[tuple], counts: dict) -> str:
    """Generate the complete data.h file."""
    lines = [
        "#ifndef DATA_H",
        "#define DATA_H",
        "",
        "#include <gb/gb.h>",
        "",
        "// ============================================",
        "// AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY",
        "// Edit _schema.json and data/*.json instead",
        "// ============================================",
        "",
    ]
    
    # Enums
    if enums:
        lines.append("// --- Enums ---")
        for enum_name, values in enums.items():
            lines.append(generate_enum_code(enum_name, values))
            lines.append("")
    
    # Structs
    if structs:
        lines.append("// --- Data Structures ---")
        for struct_code, struct_name in structs:
            lines.append(struct_code)
            lines.append("")
    
    # Counts
    if counts:
        lines.append("// --- Table Counts ---")
        for struct_name, count in counts.items():
            lines.append(f"#define {snake_to_upper(struct_name)}_COUNT {count}")
        lines.append("")
    
    # Extern declarations and accessors
    lines.append("// --- Data Tables ---")
    for _, struct_name in structs:
        var_name = struct_name.lower() + "s"
        if struct_name.endswith("y"):
            var_name = struct_name[:-1].lower() + "ies"
        lines.append(f"extern const {struct_name} {var_name}[];")
    lines.append("")
    
    lines.append("// --- Accessors ---")
    for _, struct_name in structs:
        var_name = struct_name.lower() + "s"
        if struct_name.endswith("y"):
            var_name = struct_name[:-1].lower() + "ies"
        decl, _ = generate_accessor(var_name, struct_name)
        lines.append(decl)
    
    lines.extend(["", "#endif // DATA_H"])
    return "\n".join(lines)


def generate_source(schema: dict, structs: list[tuple], data_arrays: list[str], accessors: list[str]) -> str:
    """Generate the complete data.c file."""
    lines = [
        '#include "data.h"',
        "",
        "// ============================================",
        "// AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY",
        "// Edit _schema.json and data/*.json instead",
        "// ============================================",
        "",
    ]
    
    # Data arrays
    for array_code in data_arrays:
        lines.append(array_code)
        lines.append("")
    
    # Accessor implementations
    lines.append("// --- Accessors ---")
    for impl in accessors:
        lines.append(impl)
        lines.append("")
    
    return "\n".join(lines)


def calculate_budget(schema: dict, project_path: Path) -> dict:
    """Calculate ROM budget usage."""
    budget = {
        "total_bytes": 0,
        "bank_limit": BANK_SIZE,
        "usage_percent": 0.0,
        "warning_threshold": WARNING_THRESHOLD,
        "tables": {}
    }
    
    for table_name, table_def in schema.get("tables", {}).items():
        fields = table_def.get("fields", {})
        row_size = calculate_row_size(fields)
        data = load_data(project_path, table_name)
        row_count = len(data)
        total = row_size * row_count
        
        budget["tables"][table_name] = {
            "row_size": row_size,
            "row_count": row_count,
            "total_bytes": total
        }
        budget["total_bytes"] += total
    
    budget["usage_percent"] = round(budget["total_bytes"] / BANK_SIZE * 100, 2)
    
    return budget


def generate(project_path: Path) -> dict:
    """Main generation function. Returns budget info."""
    # Load schema
    schema = load_schema(project_path)
    
    # Ensure build directory exists
    build_path = project_path / "build"
    build_path.mkdir(exist_ok=True)
    
    # Collect enums
    enums = collect_enums(schema)
    
    # Process tables
    structs = []
    counts = {}
    data_arrays = []
    accessors = []
    
    for table_name, table_def in schema.get("tables", {}).items():
        fields = table_def.get("fields", {})
        data = load_data(project_path, table_name)
        
        # Generate struct
        struct_code, struct_name = generate_struct_code(table_name, fields, enums)
        structs.append((struct_code, struct_name))
        counts[struct_name] = len(data)
        
        # Generate data array
        array_code = generate_data_array(table_name, struct_name, fields, data)
        data_arrays.append(array_code)
        
        # Generate accessor
        var_name = table_name.lower()
        _, impl = generate_accessor(var_name, struct_name)
        accessors.append(impl)
    
    # Generate files
    header = generate_header(schema, enums, structs, counts)
    source = generate_source(schema, structs, data_arrays, accessors)
    
    # Write files
    with open(build_path / "data.h", "w") as f:
        f.write(header)
    
    with open(build_path / "data.c", "w") as f:
        f.write(source)
    
    # Calculate and write budget
    budget = calculate_budget(schema, project_path)
    with open(build_path / "rom_budget.json", "w") as f:
        json.dump(budget, f, indent=2)
    
    return budget


def main():
    if len(sys.argv) < 2:
        print("Usage: python data_generator.py <project_path>")
        sys.exit(1)
    
    project_path = Path(sys.argv[1])
    
    if not project_path.exists():
        print(f"Error: Project path not found: {project_path}")
        sys.exit(1)
    
    if not (project_path / "_schema.json").exists():
        print(f"No _schema.json found in {project_path}, skipping data generation.")
        sys.exit(0)
    
    try:
        budget = generate(project_path)
        
        print(f"Generated data.h and data.c in {project_path}/build/")
        print(f"ROM Budget: {budget['total_bytes']} bytes ({budget['usage_percent']}% of {BANK_SIZE})")
        
        for table, info in budget["tables"].items():
            print(f"  {table}: {info['row_count']} rows × {info['row_size']} bytes = {info['total_bytes']} bytes")
        
        if budget["usage_percent"] >= 100:
            print("ERROR: ROM budget exceeded!")
            sys.exit(1)
        elif budget["usage_percent"] >= WARNING_THRESHOLD * 100:
            print("WARNING: ROM budget over 80%")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
