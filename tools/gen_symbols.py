#!/usr/bin/env python3
"""
Symbol Index Generator - Creates a compact JSON representation of project code.

Usage: python3 gen_symbols.py <src_directory> [output_file]

If output_file is not specified, outputs to stdout.

The generated symbols.json contains:
- File metadata (lines, type)
- Struct/enum definitions (names and fields)
- Function declarations and implementations
- Constants (filtered to exclude sprite tile indices)
- Call graph (which functions call which)
- Dependency graph (which files depend on which)
"""

import sys
import re
import json
from pathlib import Path


def extract_includes(content):
    """Extract #include directives."""
    pattern = re.compile(r'#include\s*([<"][^>"]+[>"])')
    return pattern.findall(content)


def extract_constants(content):
    """Extract #define constants, filtering out noise."""
    constants = []
    pattern = re.compile(r'#define\s+(\w+)\s+(.+?)(?:\s*//.*)?$', re.MULTILINE)
    
    for i, line in enumerate(content.split('\n'), 1):
        match = pattern.match(line)
        if match:
            name, value = match.groups()
            # Skip include guards, function-like macros, and tile indices
            if (name.endswith('_H') or 
                '(' in name or 
                name.startswith('TILE_') or
                name.startswith('_')):
                continue
            constants.append({
                "name": name,
                "value": value.strip()[:50],
                "line": i
            })
    
    return constants


def extract_structs(content):
    """Extract struct and enum definitions."""
    structs = []
    
    # Structs: typedef struct { ... } Name;
    struct_pattern = re.compile(
        r'typedef\s+struct\s*(?:\w+)?\s*\{([^}]+)\}\s*(\w+);',
        re.DOTALL
    )
    for match in struct_pattern.finditer(content):
        body, name = match.groups()
        fields = parse_struct_fields(body)
        line = content[:match.start()].count('\n') + 1
        structs.append({
            "name": name,
            "kind": "struct",
            "fields": fields,
            "line": line
        })
    
    # Enums: typedef enum { ... } Name;
    enum_pattern = re.compile(
        r'typedef\s+enum\s*(?:\w+)?\s*\{([^}]+)\}\s*(\w+);',
        re.DOTALL
    )
    for match in enum_pattern.finditer(content):
        body, name = match.groups()
        values = [v.strip().split('=')[0].strip() 
                 for v in body.split(',') if v.strip()]
        values = [v for v in values if v and not v.startswith('//')]
        line = content[:match.start()].count('\n') + 1
        structs.append({
            "name": name,
            "kind": "enum",
            "fields": values[:10],
            "line": line
        })
    
    return structs


def parse_struct_fields(body):
    """Extract field names from struct body."""
    fields = []
    field_pattern = re.compile(r'(\w+)\s*(?:\[[^\]]*\])?\s*;')
    for match in field_pattern.finditer(body):
        fields.append(match.group(1))
    return fields


def extract_function_body(content, start_brace):
    """Extract function body from opening brace to matching close."""
    depth = 1
    i = start_brace + 1
    
    while i < len(content) and depth > 0:
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
        i += 1
    
    return content[start_brace:i]


def extract_function_calls(body):
    """Extract function calls from a function body."""
    C_KEYWORDS = {
        'if', 'else', 'while', 'for', 'switch', 'case', 'return', 'break',
        'continue', 'sizeof', 'typedef', 'struct', 'enum', 'union', 'void',
        'static', 'extern', 'const', 'volatile', 'register', 'inline',
        'uint8_t', 'uint16_t', 'int8_t', 'int16_t', 'UINT8', 'UINT16',
        'INT8', 'INT16', 'TRUE', 'FALSE', 'NULL'
    }
    
    calls = set()
    pattern = re.compile(r'\b(\w+)\s*\(')
    
    for match in pattern.finditer(body):
        name = match.group(1)
        if name not in C_KEYWORDS and not name.isupper():
            calls.add(name)
    
    return sorted(calls)


def extract_functions(content):
    """Extract function declarations and definitions."""
    C_KEYWORDS = {
        'if', 'else', 'while', 'for', 'switch', 'case', 'return', 'break',
        'continue', 'sizeof', 'typedef', 'struct', 'enum', 'union', 'void',
        'static', 'extern', 'const', 'volatile', 'register', 'inline'
    }
    
    functions = []
    seen_names = set()
    
    # Function definitions (with body)
    func_def_pattern = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE
    )
    for match in func_def_pattern.finditer(content):
        ret_type, name, params = match.groups()
        if name in seen_names:
            continue
        seen_names.add(name)
        
        if ret_type.strip() in C_KEYWORDS:
            continue
        
        line = content[:match.start()].count('\n') + 1
        body = extract_function_body(content, match.end() - 1)
        calls = extract_function_calls(body)
        
        functions.append({
            "name": name,
            "return_type": ret_type.strip(),
            "params": params.strip(),
            "line": line,
            "is_definition": True,
            "calls": calls
        })
    
    # Function declarations (no body)
    func_decl_pattern = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*;',
        re.MULTILINE
    )
    for match in func_decl_pattern.finditer(content):
        ret_type, name, params = match.groups()
        if name in seen_names:
            continue
        seen_names.add(name)
        
        if ret_type.strip() in C_KEYWORDS:
            continue
        
        line = content[:match.start()].count('\n') + 1
        functions.append({
            "name": name,
            "return_type": ret_type.strip(),
            "params": params.strip(),
            "line": line,
            "is_definition": False,
            "calls": []
        })
    
    return functions


def parse_file(filepath):
    """Parse a single C file for symbols."""
    try:
        content = filepath.read_text()
    except Exception:
        return None
    
    lines = content.split('\n')
    file_type = "header" if filepath.suffix == '.h' else "implementation"
    
    return {
        "path": f"src/{filepath.name}",
        "type": file_type,
        "lines": len(lines),
        "includes": extract_includes(content),
        "structs": extract_structs(content),
        "functions": extract_functions(content),
        "constants": extract_constants(content)
    }


def build_call_graph(files):
    """Build a call graph from parsed function symbols."""
    call_graph = {}
    
    # First pass: record where each function is defined
    for file_info in files.values():
        for func in file_info.get("functions", []):
            if func.get("is_definition"):
                call_graph[func["name"]] = {
                    "defined_in": file_info["path"],
                    "calls": func.get("calls", []),
                    "called_by": []
                }
    
    # Second pass: build called_by relationships
    for func_name, entry in call_graph.items():
        for called_func in entry["calls"]:
            if called_func in call_graph:
                call_graph[called_func]["called_by"].append(func_name)
    
    # Compact format for output
    compact = {}
    for func_name, entry in call_graph.items():
        if entry["calls"] or entry["called_by"]:
            compact[func_name] = {
                "in": entry["defined_in"].replace("src/", ""),
                "calls": entry["calls"],
                "called_by": entry["called_by"]
            }
    
    return compact


def build_dependency_graph(files):
    """Build file dependency graph from includes."""
    deps = {}
    file_paths = set(files.keys())
    
    for path, file_info in files.items():
        local_deps = []
        for inc in file_info.get("includes", []):
            inc_name = inc.strip('"<>').split("/")[-1]
            for other_path in file_paths:
                if other_path.endswith(inc_name):
                    local_deps.append(other_path)
                    break
        if local_deps:
            deps[path] = local_deps
    
    return deps


def to_compact_format(files, call_graph, dependencies):
    """Convert to compact format for JSON output."""
    compact_files = {}
    
    for path, info in files.items():
        compact = {
            "type": info["type"],
            "lines": info["lines"]
        }
        
        # Includes (just filenames)
        if info.get("includes"):
            compact["includes"] = [
                inc.split("/")[-1].strip('"<>') 
                for inc in info["includes"]
            ]
        
        # Structs
        if info.get("structs"):
            compact["structs"] = {
                s["name"]: {"kind": s["kind"], "fields": s["fields"]}
                for s in info["structs"]
            }
        
        # Functions - separate declares vs implements
        if info.get("functions"):
            decls = [f["name"] for f in info["functions"] if not f.get("is_definition")]
            impls = [f["name"] for f in info["functions"] if f.get("is_definition")]
            if decls:
                compact["declares"] = decls
            if impls:
                compact["implements"] = impls
        
        # Constants (excluding TILE_ prefixed)
        if info.get("constants"):
            const_names = [c["name"] for c in info["constants"]]
            if const_names:
                compact["constants"] = const_names
        
        compact_files[path] = compact
    
    return {
        "files": compact_files,
        "call_graph": call_graph,
        "dependencies": dependencies
    }


def generate_symbols(src_dir):
    """Generate symbol index for a source directory."""
    src_path = Path(src_dir)
    
    if not src_path.exists():
        return {"error": f"Source directory not found: {src_dir}"}
    
    files = {}
    
    # Parse all header files
    for f in sorted(src_path.glob("*.h")):
        info = parse_file(f)
        if info:
            files[info["path"]] = info
    
    # Parse all implementation files
    for f in sorted(src_path.glob("*.c")):
        info = parse_file(f)
        if info:
            files[info["path"]] = info
    
    # Build graphs
    call_graph = build_call_graph(files)
    dependencies = build_dependency_graph(files)
    
    # Convert to compact format
    return to_compact_format(files, call_graph, dependencies)


def main():
    if len(sys.argv) < 2:
        print("Usage: gen_symbols.py <src_directory> [output_file]", file=sys.stderr)
        sys.exit(1)
    
    src_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    symbols = generate_symbols(src_dir)
    json_output = json.dumps(symbols, indent=2)
    
    if output_file:
        Path(output_file).write_text(json_output)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
