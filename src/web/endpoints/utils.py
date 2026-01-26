"""
Utility functions and shared resources for endpoints.
"""
import asyncio
import queue
import re
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from project_api import PROJECTS_DIR

# Thread pool for running synchronous code
executor = ThreadPoolExecutor(max_workers=4)

# Track active generation tasks
active_tasks: dict[str, asyncio.Task] = {}

# Store for pipeline logs (per project)
pipeline_logs: dict[str, list[dict]] = {}


def parse_sprites_from_c(content: str) -> list[dict]:
    """
    Parse sprite tile data from a C source file.
    
    Looks for patterns like:
        const uint8_t sprite_name[] = { 0xHH, 0xHH, ... };
        const unsigned char sprite_name[] = { ... };
    
    Returns list of sprites with name, data bytes, and dimensions.
    """
    sprites = []
    
    # Pattern to match const array declarations
    # Handles: const uint8_t name[] = { ... }; and const unsigned char name[] = { ... };
    pattern = r'(?:const\s+)?(?:uint8_t|unsigned\s+char)\s+(\w+)\s*\[\s*\]\s*=\s*\{([^}]+)\}'
    
    for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
        name = match.group(1)
        data_str = match.group(2)
        
        # Extract hex bytes
        hex_pattern = r'0x([0-9A-Fa-f]{2})'
        hex_bytes = re.findall(hex_pattern, data_str)
        
        if not hex_bytes:
            continue
        
        # Convert to integers
        data = [int(b, 16) for b in hex_bytes]
        
        # Determine dimensions based on data length
        # GB tiles are 16 bytes for 8x8 (2 bits per pixel, 2 bytes per row)
        # 8x16 sprites are 32 bytes
        byte_count = len(data)
        
        if byte_count == 16:
            width, height = 8, 8
        elif byte_count == 32:
            width, height = 8, 16
        elif byte_count == 64:
            width, height = 16, 16
        elif byte_count % 16 == 0:
            tile_count = byte_count // 16
            if tile_count == 4:
                width, height = 16, 16
            elif tile_count == 2:
                width, height = 8, 16
            else:
                width = 8
                height = 8 * tile_count
        else:
            continue
        
        sprites.append({
            "name": name,
            "width": width,
            "height": height,
            "data": data,
            "byte_count": byte_count
        })
    
    return sprites


def generate_sprite_c_code(name: str, width: int, height: int, data: list[int]) -> str:
    """Generate C code for a sprite tile array."""
    
    # Generate visual comment
    visual_lines = []
    byte_idx = 0
    for tile_y in range(0, height, 8):
        for row in range(8):
            if tile_y + row >= height:
                break
            line = ""
            for tile_x in range(0, width, 8):
                if byte_idx + 1 < len(data):
                    low_byte = data[byte_idx]
                    high_byte = data[byte_idx + 1]
                    for bit in range(7, -1, -1):
                        if tile_x + (7 - bit) >= width:
                            break
                        low_bit = (low_byte >> bit) & 1
                        high_bit = (high_byte >> bit) & 1
                        color = (high_bit << 1) | low_bit
                        line += ['·', '░', '▒', '█'][color]
                    byte_idx += 2
            visual_lines.append(f" *   {line}")
    
    visual_comment = "\n".join(visual_lines)
    
    # Generate hex data
    hex_lines = []
    for i in range(0, len(data), 8):
        chunk = data[i:i+8]
        hex_str = ", ".join(f"0x{b:02X}" for b in chunk)
        hex_lines.append(f"    {hex_str},")
    
    hex_data = "\n".join(hex_lines)
    # Remove trailing comma from last line
    if hex_data.endswith(","):
        hex_data = hex_data[:-1]
    
    return f"""/**
 * {name}: {width}x{height} sprite
 * 
 * Visual representation:
{visual_comment}
 */
const uint8_t {name}[] = {{
{hex_data}
}};"""


def parse_tunables_from_c(content: str, filename: str) -> list[dict]:
    """
    Parse @tunable/@tuneable annotated #define statements from C code.
    
    Supports two formats:
    
    Format 1 (comment before):
        // @tunable category range:MIN-MAX Description
        #define NAME value
    
    Format 2 (comment after):
        #define NAME value  // @tuneable range:MIN-MAX step:N desc:"Description"
    
    Returns list of tunable parameters with metadata.
    """
    tunables = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Format 1: @tunable comment on line before #define
        if ('@tuneable' in line or '@tunable' in line) and line.startswith('//'):
            match = re.match(
                r'//\s*@tune?able\s+(\w+)\s+range:(-?\d+)-(-?\d+)\s*(.*)',
                line
            )
            
            if match and i + 1 < len(lines):
                category = match.group(1)
                min_val = int(match.group(2))
                max_val = int(match.group(3))
                description = match.group(4).strip()
                
                # Next line should be the #define
                define_line = lines[i + 1].strip()
                define_match = re.match(
                    r'#define\s+(\w+)\s+\(?(-?\d+)\)?',
                    define_line
                )
                
                if define_match:
                    name = define_match.group(1)
                    value = int(define_match.group(2))
                    
                    tunables.append({
                        "name": name,
                        "value": value,
                        "min": min_val,
                        "max": max_val,
                        "category": category,
                        "description": description or name,
                        "file": filename,
                        "line": i + 2  # 1-indexed, pointing to #define line
                    })
                    i += 1  # Skip the #define line
        
        # Format 2: #define with @tuneable comment on same line
        elif line.startswith('#define') and ('@tuneable' in line or '@tunable' in line):
            match = re.match(
                r'#define\s+(\w+)\s+\(?(-?\d+)\)?\s+//\s*@tune?able\s+range:(-?\d+)-(-?\d+)(?:\s+step:\d+)?(?:\s+desc:"([^"]*)")?',
                line
            )
            
            if match:
                name = match.group(1)
                value = int(match.group(2))
                min_val = int(match.group(3))
                max_val = int(match.group(4))
                description = match.group(5) or name
                
                # Derive category from filename or use generic
                category = filename.replace('src/', '').replace('.h', '').replace('.c', '')
                
                tunables.append({
                    "name": name,
                    "value": value,
                    "min": min_val,
                    "max": max_val,
                    "category": category,
                    "description": description,
                    "file": filename,
                    "line": i + 1  # 1-indexed
                })
        
        i += 1
    
    return tunables


def parse_config_schema_from_c(content: str, filename: str) -> list[dict]:
    """
    Parse @config table definitions from C code.
    
    Extracts schema information from annotated structs/arrays.
    
    Format:
        // @config table:enemies description:"Enemy definitions"
        // @field id uint8 auto description:"Unique ID"
        // @field name string length:12 description:"Display name"
        // @field hp uint8 min:1 max:255 description:"Hit points"
        typedef struct { ... } Enemy;
    
    Returns list of table schemas with field definitions.
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
                
                # Stop at non-comment or @config (next table)
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
                    "file": filename,
                    "line": i + 1
                })
            
            i = j
        else:
            i += 1
    
    return tables

