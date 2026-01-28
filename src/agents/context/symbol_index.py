"""
Symbol Index Generator - Creates a compact representation of project code.

Instead of sending full file contents to the Coder, we generate a symbol index
that contains:
- File metadata (lines, type)
- Struct/enum definitions (names and fields)
- Function declarations and implementations
- Constants (filtered to exclude sprite tile indices)
- Call graph (which functions call which)
- Dependency graph (which files depend on which)

This allows the Coder to understand the codebase structure and request
only the specific files needed for a given step.
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class StructSymbol:
    """A struct or enum definition."""
    name: str
    kind: str  # "struct" or "enum"
    fields: list[str]  # field names only for brevity
    line: int


@dataclass 
class FunctionSymbol:
    """A function declaration or implementation."""
    name: str
    return_type: str
    params: str  # Parameter signature
    line: int
    is_definition: bool  # True if has body, False if just declaration
    calls: list[str] = field(default_factory=list)  # Functions this calls
    

@dataclass
class ConstantSymbol:
    """A #define constant."""
    name: str
    value: str
    line: int


@dataclass
class FileSymbols:
    """Symbols extracted from a single file."""
    path: str
    file_type: str  # "header" or "implementation"
    lines: int
    includes: list[str] = field(default_factory=list)
    structs: list[StructSymbol] = field(default_factory=list)
    functions: list[FunctionSymbol] = field(default_factory=list)
    constants: list[ConstantSymbol] = field(default_factory=list)
    
    def to_compact_dict(self) -> dict:
        """Convert to a compact dict representation for JSON."""
        result = {
            "type": self.file_type,
            "lines": self.lines,
        }
        
        if self.includes:
            # Just the filenames, not full paths
            result["includes"] = [inc.split("/")[-1].strip('"<>') for inc in self.includes]
        
        if self.structs:
            result["structs"] = {
                s.name: {"kind": s.kind, "fields": s.fields}
                for s in self.structs
            }
        
        if self.functions:
            # Separate declarations from implementations
            decls = [f.name for f in self.functions if not f.is_definition]
            impls = [f.name for f in self.functions if f.is_definition]
            
            if decls:
                result["declares"] = decls
            if impls:
                result["implements"] = impls
        
        if self.constants:
            # Group by prefix for compactness
            result["constants"] = [c.name for c in self.constants]
        
        return result


@dataclass
class CallGraphEntry:
    """Call graph entry for a function."""
    defined_in: str
    calls: list[str]
    called_by: list[str] = field(default_factory=list)


@dataclass
class SymbolIndex:
    """Complete symbol index for a project."""
    files: dict[str, FileSymbols] = field(default_factory=dict)
    call_graph: dict[str, CallGraphEntry] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "files": {
                path: symbols.to_compact_dict()
                for path, symbols in self.files.items()
            },
            "call_graph": {
                func: {
                    "in": entry.defined_in.replace("src/", ""),
                    "calls": entry.calls,
                    "called_by": entry.called_by
                }
                for func, entry in self.call_graph.items()
                if entry.calls or entry.called_by  # Only include if has relationships
            },
            "dependencies": self._build_dependency_graph()
        }
    
    def _build_dependency_graph(self) -> dict[str, list[str]]:
        """Build file dependency graph from includes."""
        deps = {}
        for path, symbols in self.files.items():
            # Find which local files this file includes
            local_deps = []
            for inc in symbols.includes:
                # Match against our known files
                inc_name = inc.strip('"<>').split("/")[-1]
                for other_path in self.files.keys():
                    if other_path.endswith(inc_name):
                        local_deps.append(other_path)
                        break
            if local_deps:
                deps[path] = local_deps
        return deps
    
    def to_prompt_format(self) -> str:
        """Format symbol index for LLM prompt - compact but readable."""
        lines = ["## Project Symbol Index", ""]
        
        # Group by file type
        headers = {p: s for p, s in self.files.items() if s.file_type == "header"}
        impls = {p: s for p, s in self.files.items() if s.file_type == "implementation"}
        
        # Headers first
        if headers:
            lines.append("### Headers")
            for path, symbols in sorted(headers.items()):
                lines.append(self._format_file_symbols(path, symbols))
            lines.append("")
        
        # Implementations
        if impls:
            lines.append("### Implementation Files")
            for path, symbols in sorted(impls.items()):
                lines.append(self._format_file_symbols(path, symbols))
            lines.append("")
        
        # Call graph (abbreviated)
        if self.call_graph:
            lines.append("### Key Function Relationships")
            for func, entry in sorted(self.call_graph.items()):
                if entry.calls:
                    calls_str = ", ".join(entry.calls[:5])
                    if len(entry.calls) > 5:
                        calls_str += f" +{len(entry.calls)-5} more"
                    lines.append(f"- {func}() → {calls_str}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_file_symbols(self, path: str, symbols: FileSymbols) -> str:
        """Format a single file's symbols."""
        parts = [f"**{path}** ({symbols.lines} lines)"]
        
        details = []
        
        if symbols.structs:
            struct_names = [s.name for s in symbols.structs]
            details.append(f"structs: {', '.join(struct_names)}")
        
        if symbols.functions:
            func_names = [f.name for f in symbols.functions if f.is_definition]
            decl_names = [f.name for f in symbols.functions if not f.is_definition]
            
            if func_names:
                details.append(f"implements: {', '.join(func_names[:8])}")
                if len(func_names) > 8:
                    details[-1] += f" +{len(func_names)-8} more"
            if decl_names:
                details.append(f"declares: {', '.join(decl_names[:8])}")
        
        if symbols.constants:
            # Filter and abbreviate constants
            const_names = [c.name for c in symbols.constants 
                          if not c.name.startswith("TILE_")]  # Skip tile indices
            if const_names:
                details.append(f"constants: {', '.join(const_names[:6])}")
                if len(const_names) > 6:
                    details[-1] += f" +{len(const_names)-6} more"
        
        if details:
            parts.append(f"  {'; '.join(details)}")
        
        return "\n".join(parts)
    
    def get_files_for_function(self, func_name: str) -> list[str]:
        """Get files related to a function (where it's defined and called)."""
        files = set()
        
        if func_name in self.call_graph:
            entry = self.call_graph[func_name]
            files.add(entry.defined_in)
            
            # Add files that call this function
            for caller in entry.called_by:
                if caller in self.call_graph:
                    files.add(self.call_graph[caller].defined_in)
        
        return list(files)
    
    def get_dependent_files(self, file_path: str) -> list[str]:
        """Get files that depend on or are depended by the given file."""
        deps = self._build_dependency_graph()
        result = set()
        
        # Files this one depends on
        if file_path in deps:
            result.update(deps[file_path])
        
        # Files that depend on this one
        for other_file, other_deps in deps.items():
            if file_path in other_deps:
                result.add(other_file)
        
        return list(result)


class SymbolIndexGenerator:
    """Generates symbol index by parsing C source files."""
    
    # Regex patterns for parsing
    INCLUDE_PATTERN = re.compile(r'#include\s*([<"][^>"]+[>"])')
    DEFINE_PATTERN = re.compile(r'#define\s+(\w+)\s+(.+?)(?:\s*//.*)?$', re.MULTILINE)
    
    STRUCT_PATTERN = re.compile(
        r'typedef\s+struct\s*(?:\w+)?\s*\{([^}]+)\}\s*(\w+);',
        re.DOTALL
    )
    ENUM_PATTERN = re.compile(
        r'typedef\s+enum\s*(?:\w+)?\s*\{([^}]+)\}\s*(\w+);',
        re.DOTALL
    )
    
    # Function with body
    FUNC_DEF_PATTERN = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE
    )
    # Function declaration (no body)
    FUNC_DECL_PATTERN = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*;',
        re.MULTILINE
    )
    
    # Function calls within code
    FUNC_CALL_PATTERN = re.compile(r'\b(\w+)\s*\(')
    
    # C keywords and common names to exclude from call detection
    C_KEYWORDS = {
        'if', 'else', 'while', 'for', 'switch', 'case', 'return', 'break',
        'continue', 'sizeof', 'typedef', 'struct', 'enum', 'union', 'void',
        'static', 'extern', 'const', 'volatile', 'register', 'inline',
        'uint8_t', 'uint16_t', 'int8_t', 'int16_t', 'UINT8', 'UINT16',
        'INT8', 'INT16', 'TRUE', 'FALSE', 'NULL'
    }
    
    def generate(self, project_path: Path) -> SymbolIndex:
        """Generate symbol index for a project."""
        index = SymbolIndex()
        src_path = project_path / "src"
        
        if not src_path.exists():
            return index
        
        # Parse all source files
        for f in sorted(src_path.glob("*.h")):
            symbols = self._parse_file(f, "header")
            index.files[f"src/{f.name}"] = symbols
        
        for f in sorted(src_path.glob("*.c")):
            symbols = self._parse_file(f, "implementation")
            index.files[f"src/{f.name}"] = symbols
        
        # Build call graph
        index.call_graph = self._build_call_graph(index.files)
        
        return index
    
    def _parse_file(self, filepath: Path, file_type: str) -> FileSymbols:
        """Parse a single C file for symbols."""
        try:
            content = filepath.read_text()
        except Exception:
            return FileSymbols(
                path=f"src/{filepath.name}",
                file_type=file_type,
                lines=0
            )
        
        lines = content.split('\n')
        
        return FileSymbols(
            path=f"src/{filepath.name}",
            file_type=file_type,
            lines=len(lines),
            includes=self._extract_includes(content),
            structs=self._extract_structs(content),
            functions=self._extract_functions(content, lines),
            constants=self._extract_constants(content)
        )
    
    def _extract_includes(self, content: str) -> list[str]:
        """Extract #include directives."""
        return self.INCLUDE_PATTERN.findall(content)
    
    def _extract_constants(self, content: str) -> list[ConstantSymbol]:
        """Extract #define constants, filtering out noise."""
        constants = []
        
        for i, line in enumerate(content.split('\n'), 1):
            match = self.DEFINE_PATTERN.match(line)
            if match:
                name, value = match.groups()
                # Skip include guards, function-like macros, and tile indices
                if (name.endswith('_H') or 
                    '(' in name or 
                    name.startswith('TILE_') or
                    name.startswith('_')):
                    continue
                    
                constants.append(ConstantSymbol(
                    name=name,
                    value=value.strip()[:50],  # Truncate long values
                    line=i
                ))
        
        return constants
    
    def _extract_structs(self, content: str) -> list[StructSymbol]:
        """Extract struct and enum definitions."""
        structs = []
        
        # Structs
        for match in self.STRUCT_PATTERN.finditer(content):
            body, name = match.groups()
            fields = self._parse_struct_fields(body)
            line = content[:match.start()].count('\n') + 1
            structs.append(StructSymbol(
                name=name,
                kind="struct",
                fields=fields,
                line=line
            ))
        
        # Enums
        for match in self.ENUM_PATTERN.finditer(content):
            body, name = match.groups()
            # Extract enum values
            values = [v.strip().split('=')[0].strip() 
                     for v in body.split(',') if v.strip()]
            values = [v for v in values if v and not v.startswith('//')]
            line = content[:match.start()].count('\n') + 1
            structs.append(StructSymbol(
                name=name,
                kind="enum",
                fields=values[:10],  # Limit to first 10 values
                line=line
            ))
        
        return structs
    
    def _parse_struct_fields(self, body: str) -> list[str]:
        """Extract field names from struct body."""
        fields = []
        field_pattern = re.compile(r'(\w+)\s*(?:\[[^\]]*\])?\s*;')
        for match in field_pattern.finditer(body):
            fields.append(match.group(1))
        return fields
    
    def _extract_functions(self, content: str, lines: list[str]) -> list[FunctionSymbol]:
        """Extract function declarations and definitions."""
        functions = []
        seen_names = set()
        
        # Function definitions (with body)
        for match in self.FUNC_DEF_PATTERN.finditer(content):
            ret_type, name, params = match.groups()
            if name in seen_names:
                continue
            seen_names.add(name)
            
            # Skip if return type looks like a keyword/control statement
            if ret_type.strip() in self.C_KEYWORDS:
                continue
            
            line = content[:match.start()].count('\n') + 1
            
            # Extract function body to find calls
            body = self._extract_function_body(content, match.end() - 1)
            calls = self._extract_function_calls(body)
            
            functions.append(FunctionSymbol(
                name=name,
                return_type=ret_type.strip(),
                params=params.strip(),
                line=line,
                is_definition=True,
                calls=calls
            ))
        
        # Function declarations (no body) - typically in headers
        for match in self.FUNC_DECL_PATTERN.finditer(content):
            ret_type, name, params = match.groups()
            if name in seen_names:
                continue
            seen_names.add(name)
            
            if ret_type.strip() in self.C_KEYWORDS:
                continue
            
            line = content[:match.start()].count('\n') + 1
            functions.append(FunctionSymbol(
                name=name,
                return_type=ret_type.strip(),
                params=params.strip(),
                line=line,
                is_definition=False
            ))
        
        return functions
    
    def _extract_function_body(self, content: str, start_brace: int) -> str:
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
    
    def _extract_function_calls(self, body: str) -> list[str]:
        """Extract function calls from a function body."""
        calls = set()
        
        for match in self.FUNC_CALL_PATTERN.finditer(body):
            name = match.group(1)
            # Filter out keywords and common non-function identifiers
            if name not in self.C_KEYWORDS and not name.isupper():
                calls.add(name)
        
        return sorted(calls)
    
    def _build_call_graph(self, files: dict[str, FileSymbols]) -> dict[str, CallGraphEntry]:
        """Build a call graph from parsed function symbols."""
        call_graph = {}
        
        # First pass: record where each function is defined
        for path, symbols in files.items():
            for func in symbols.functions:
                if func.is_definition:
                    call_graph[func.name] = CallGraphEntry(
                        defined_in=path,
                        calls=func.calls
                    )
        
        # Second pass: build called_by relationships
        for func_name, entry in call_graph.items():
            for called_func in entry.calls:
                if called_func in call_graph:
                    call_graph[called_func].called_by.append(func_name)
        
        return call_graph


def generate_symbol_index(project_path: Path) -> SymbolIndex:
    """Convenience function to generate symbol index for a project."""
    generator = SymbolIndexGenerator()
    return generator.generate(project_path)


def load_symbol_index(project_path: Path) -> dict:
    """
    Load symbol index from JSON file (generated by Makefile).
    
    Falls back to generating on-the-fly if file doesn't exist.
    
    Returns:
        dict with 'files', 'call_graph', 'dependencies' keys
    """
    symbols_file = project_path / "context" / "symbols.json"
    
    if symbols_file.exists():
        try:
            return json.loads(symbols_file.read_text())
        except json.JSONDecodeError:
            pass
    
    # Fallback: generate on-the-fly
    index = generate_symbol_index(project_path)
    return index.to_dict()


def symbols_to_prompt(symbols: dict) -> str:
    """
    Convert loaded symbols dict to prompt-friendly format.
    
    Args:
        symbols: Dict loaded from symbols.json
        
    Returns:
        Formatted string for LLM prompt
    """
    lines = ["## Project Symbol Index", ""]
    
    files = symbols.get("files", {})
    
    # Group by type
    headers = {p: f for p, f in files.items() if f.get("type") == "header"}
    impls = {p: f for p, f in files.items() if f.get("type") == "implementation"}
    
    # Headers
    if headers:
        lines.append("### Headers")
        for path, info in sorted(headers.items()):
            lines.append(_format_file_info(path, info))
        lines.append("")
    
    # Implementations
    if impls:
        lines.append("### Implementation Files")
        for path, info in sorted(impls.items()):
            lines.append(_format_file_info(path, info))
        lines.append("")
    
    # Call graph (abbreviated)
    call_graph = symbols.get("call_graph", {})
    if call_graph:
        lines.append("### Key Function Relationships")
        for func, info in sorted(call_graph.items()):
            calls = info.get("calls", [])
            if calls:
                calls_str = ", ".join(calls[:5])
                if len(calls) > 5:
                    calls_str += f" +{len(calls)-5} more"
                lines.append(f"- {func}() → {calls_str}")
        lines.append("")
    
    return "\n".join(lines)


def _format_file_info(path: str, info: dict) -> str:
    """Format a single file's symbol info."""
    parts = [f"**{path}** ({info.get('lines', 0)} lines)"]
    
    details = []
    
    structs = info.get("structs", {})
    if structs:
        details.append(f"structs: {', '.join(structs.keys())}")
    
    impls = info.get("implements", [])
    decls = info.get("declares", [])
    
    if impls:
        impl_str = ", ".join(impls[:8])
        if len(impls) > 8:
            impl_str += f" +{len(impls)-8} more"
        details.append(f"implements: {impl_str}")
    
    if decls:
        details.append(f"declares: {', '.join(decls[:8])}")
    
    consts = info.get("constants", [])
    if consts:
        # Filter out TILE_ prefixed constants
        consts = [c for c in consts if not c.startswith("TILE_")]
        if consts:
            const_str = ", ".join(consts[:6])
            if len(consts) > 6:
                const_str += f" +{len(consts)-6} more"
            details.append(f"constants: {const_str}")
    
    if details:
        parts.append(f"  {'; '.join(details)}")
    
    return "\n".join(parts)

