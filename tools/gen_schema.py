#!/usr/bin/env python3
"""
Schema Generator - Extracts @config annotations from C headers to _schema.json.

This tool scans all .h files in a source directory for @config/@field annotations
and generates a _schema.json file compatible with data_generator.py.

Usage:
    python3 gen_schema.py <src_dir> <output_file>
    python3 gen_schema.py src/ _schema.json

Annotation Format:
    // @config table:enemies description:"Enemy definitions"
    // @field id uint8 auto description:"Unique ID"
    // @field name string length:12 description:"Display name"
    // @field hp uint8 min:1 max:255 default:10 description:"Hit points"
    // @field type enum values:["normal","boss","elite"] description:"Enemy type"
    typedef struct { ... } Enemy;

Output Format (_schema.json):
    {
      "tables": {
        "enemies": {
          "description": "Enemy definitions",
          "fields": {
            "id": {"type": "uint8", "auto": true, "description": "Unique ID"},
            ...
          },
          "field_order": ["id", "name", "hp", "type"]
        }
      }
    }
"""

import json
import re
import sys
from pathlib import Path


def parse_config_annotations(content: str, filename: str) -> list[dict]:
    """
    Parse @config table definitions from C header content.
    
    Args:
        content: C header file content
        filename: Source filename for reference
        
    Returns:
        List of table definitions with fields
    """
    tables = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for @config table definition
        if line.startswith('//') and '@config' in line:
            # Parse table metadata
            table_match = re.search(r'@config\s+table:(\w+)', line)
            if not table_match:
                i += 1
                continue
            
            table_name = table_match.group(1)
            
            # Extract description if present
            desc_match = re.search(r'description:"([^"]*)"', line)
            table_desc = desc_match.group(1) if desc_match else table_name
            
            # Collect fields from subsequent @field lines
            fields = {}
            field_order = []
            j = i + 1
            
            while j < len(lines):
                field_line = lines[j].strip()
                
                # Stop at non-comment or next @config
                if not field_line.startswith('//'):
                    break
                if '@config' in field_line:
                    break
                
                # Parse @field annotation
                if '@field' in field_line:
                    field_match = re.match(
                        r'//\s*@field\s+(\w+)\s+(\w+)(.*)',
                        field_line
                    )
                    
                    if field_match:
                        field_name = field_match.group(1)
                        field_type = field_match.group(2)
                        field_attrs = field_match.group(3)
                        
                        field_def = {
                            "type": field_type,
                        }
                        
                        # Parse optional attributes
                        if 'auto' in field_attrs:
                            field_def["auto"] = True
                        
                        length_match = re.search(r'length:(\d+)', field_attrs)
                        if length_match:
                            field_def["length"] = int(length_match.group(1))
                        
                        min_match = re.search(r'min:(-?\d+)', field_attrs)
                        if min_match:
                            field_def["min"] = int(min_match.group(1))
                        
                        max_match = re.search(r'max:(-?\d+)', field_attrs)
                        if max_match:
                            field_def["max"] = int(max_match.group(1))
                        
                        # Parse enum values: values:["a","b","c"]
                        values_match = re.search(r'values:\[([^\]]+)\]', field_attrs)
                        if values_match:
                            values_str = values_match.group(1)
                            values = [v.strip().strip('"\'') for v in values_str.split(',')]
                            field_def["values"] = values
                        
                        # Parse target for refs: target:items
                        target_match = re.search(r'target:(\w+)', field_attrs)
                        if target_match:
                            field_def["target"] = target_match.group(1)
                        
                        if 'nullable' in field_attrs:
                            field_def["nullable"] = True
                        
                        if 'required' in field_attrs:
                            field_def["required"] = True
                        
                        # Parse description
                        fdesc_match = re.search(r'description:"([^"]*)"', field_attrs)
                        if fdesc_match:
                            field_def["description"] = fdesc_match.group(1)
                        
                        # Parse default value
                        default_match = re.search(r'default:(\S+)', field_attrs)
                        if default_match:
                            default_val = default_match.group(1).strip('"\'')
                            # Try to convert to int if numeric
                            try:
                                default_val = int(default_val)
                            except ValueError:
                                pass
                            field_def["default"] = default_val
                        
                        fields[field_name] = field_def
                        field_order.append(field_name)
                
                j += 1
            
            if fields:
                tables.append({
                    "name": table_name,
                    "description": table_desc,
                    "fields": fields,
                    "field_order": field_order,
                    "source_file": filename,
                    "source_line": i + 1
                })
            
            i = j
        else:
            i += 1
    
    return tables


def generate_schema(src_dir: Path) -> dict:
    """
    Scan all .h files in src_dir and generate schema.
    
    Args:
        src_dir: Directory containing .h files
        
    Returns:
        Schema dict compatible with data_generator.py
    """
    all_tables = {}
    
    # Scan all .h files
    for filepath in sorted(src_dir.glob("*.h")):
        try:
            content = filepath.read_text()
            relative_path = f"src/{filepath.name}"
            tables = parse_config_annotations(content, relative_path)
            
            for table in tables:
                table_name = table["name"]
                all_tables[table_name] = {
                    "description": table["description"],
                    "fields": table["fields"],
                    "field_order": table["field_order"],
                    # Metadata for debugging
                    "_source_file": table["source_file"],
                    "_source_line": table["source_line"]
                }
        except Exception as e:
            print(f"Warning: Error parsing {filepath}: {e}", file=sys.stderr)
    
    return {
        "tables": all_tables,
        "_generated": True,
        "_source": "gen_schema.py"
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 gen_schema.py <src_dir> <output_file>")
        print("Example: python3 gen_schema.py src/ _schema.json")
        sys.exit(1)
    
    src_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Generate schema
    schema = generate_schema(src_dir)
    
    table_count = len(schema["tables"])
    
    if table_count == 0:
        print("No @config annotations found in headers", file=sys.stderr)
        # Still write empty schema so datagen knows there's nothing to do
        output_file.write_text(json.dumps({"tables": {}}, indent=2))
        sys.exit(0)
    
    # Write output
    output_file.write_text(json.dumps(schema, indent=2))
    
    # Summary
    print(f"Generated {output_file}: {table_count} table(s)")
    for name, table in schema["tables"].items():
        field_count = len(table["fields"])
        print(f"  - {name}: {field_count} fields ({table.get('_source_file', 'unknown')})")


if __name__ == "__main__":
    main()
