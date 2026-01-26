"""
Code chunking utilities for extracting meaningful pieces from C source files.

Provides functions to extract:
- Functions with their signatures and bodies
- Struct/type definitions
- Constant arrays (especially sprite data)
- #define blocks
- Documentation comments
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CodeChunk:
    """A meaningful piece of extracted code."""
    chunk_type: str  # 'function', 'sprite', 'struct', 'constant', 'comment'
    name: str
    code: str
    start_line: int
    end_line: int
    description: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def extract_functions(content: str) -> List[CodeChunk]:
    """
    Extract all function definitions from C source code.
    
    Args:
        content: C source code
        
    Returns:
        List of CodeChunk objects for each function
    """
    functions = []
    lines = content.split('\n')
    
    # Pattern to find function definitions
    # Matches: return_type function_name(params) {
    # Also handles multi-line signatures and pointer returns
    func_pattern = re.compile(
        r'^(\w[\w\s\*]*?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE
    )
    
    for match in func_pattern.finditer(content):
        return_type = match.group(1).strip()
        func_name = match.group(2)
        params = match.group(3).strip()
        
        # Skip if this looks like a control structure
        if func_name in ('if', 'while', 'for', 'switch'):
            continue
            
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1
        
        # Find matching closing brace
        brace_count = 0
        in_function = False
        end_pos = start_pos
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '{':
                brace_count += 1
                in_function = True
            elif char == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    end_pos = i + 1
                    break
        
        func_code = content[start_pos:end_pos]
        end_line = start_line + func_code.count('\n')
        
        # Extract preceding comment if any
        description = extract_preceding_comment(content, start_pos)
        
        # Categorize the function
        category = categorize_function(func_name, func_code)
        
        functions.append(CodeChunk(
            chunk_type='function',
            name=func_name,
            code=func_code,
            start_line=start_line,
            end_line=end_line,
            description=description or f"{return_type} {func_name}({params})",
            metadata={
                'return_type': return_type,
                'params': params,
                'category': category
            }
        ))
    
    return functions


def extract_sprite_arrays(content: str) -> List[CodeChunk]:
    """
    Extract sprite/tile data arrays from C source code.
    
    Looks for uint8_t arrays that contain sprite or tile data,
    identified by naming conventions or comments.
    
    Args:
        content: C source code
        
    Returns:
        List of CodeChunk objects for each sprite array
    """
    sprites = []
    
    # Pattern for const uint8_t arrays
    array_pattern = re.compile(
        r'((?:/\*[\s\S]*?\*/\s*|//[^\n]*\n\s*)*)'  # Preceding comments
        r'(const\s+uint8_t\s+(\w+)\s*\[\s*\]\s*=\s*\{)'  # Array declaration
        r'([\s\S]*?)'  # Array contents
        r'(\};)',  # Closing
        re.MULTILINE
    )
    
    for match in array_pattern.finditer(content):
        comments = match.group(1).strip()
        declaration = match.group(2)
        name = match.group(3)
        data = match.group(4)
        closing = match.group(5)
        
        # Check if this looks like sprite/tile data
        name_lower = name.lower()
        is_sprite = any(keyword in name_lower for keyword in 
                       ['sprite', 'tile', 'gfx', 'player', 'enemy', 'icon', 'font'])
        
        # Also check comments
        comments_lower = comments.lower()
        is_sprite = is_sprite or any(keyword in comments_lower for keyword in
                                     ['sprite', 'tile', 'animation', 'frame', 'pixel'])
        
        if not is_sprite:
            continue
        
        full_code = comments + declaration + data + closing
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1
        end_line = start_line + full_code.count('\n')
        
        # Parse the hex data
        hex_bytes = parse_hex_array(data)
        
        # Estimate sprite info
        num_bytes = len(hex_bytes)
        # 2bpp format: 2 bytes per row, 8 rows per 8x8 tile = 16 bytes per tile
        num_tiles = num_bytes // 16 if num_bytes >= 16 else 1
        
        # Extract frame info from comments
        frame_count = extract_frame_count(comments, name, num_tiles)
        
        sprites.append(CodeChunk(
            chunk_type='sprite',
            name=name,
            code=full_code,
            start_line=start_line,
            end_line=end_line,
            description=extract_sprite_description(comments, name, num_tiles),
            metadata={
                'num_bytes': num_bytes,
                'num_tiles': num_tiles,
                'frame_count': frame_count,
                'hex_bytes': hex_bytes[:64],  # First 4 tiles max for preview
                'raw_comments': comments
            }
        ))
    
    return sprites


def extract_structs(content: str) -> List[CodeChunk]:
    """
    Extract struct and typedef definitions.
    
    Args:
        content: C source code
        
    Returns:
        List of CodeChunk objects for each struct
    """
    structs = []
    
    # Pattern for struct definitions
    struct_pattern = re.compile(
        r'((?:/\*[\s\S]*?\*/\s*|//[^\n]*\n\s*)*)'  # Preceding comments
        r'(typedef\s+struct\s*\{[\s\S]*?\}\s*(\w+)\s*;'  # typedef struct
        r'|struct\s+(\w+)\s*\{[\s\S]*?\}\s*;)',  # Regular struct
        re.MULTILINE
    )
    
    for match in struct_pattern.finditer(content):
        comments = match.group(1).strip()
        full_match = match.group(0)
        name = match.group(3) or match.group(4)
        
        if not name:
            continue
            
        start_pos = match.start()
        start_line = content[:start_pos].count('\n') + 1
        end_line = start_line + full_match.count('\n')
        
        # Extract field names
        fields = re.findall(r'(\w+)\s*;', full_match)
        
        structs.append(CodeChunk(
            chunk_type='struct',
            name=name,
            code=full_match,
            start_line=start_line,
            end_line=end_line,
            description=extract_preceding_comment(content, start_pos) or f"struct {name}",
            metadata={
                'fields': fields
            }
        ))
    
    return structs


def extract_constants(content: str) -> List[CodeChunk]:
    """
    Extract #define constant blocks.
    
    Groups related #defines together based on proximity and comments.
    
    Args:
        content: C source code
        
    Returns:
        List of CodeChunk objects for constant groups
    """
    constants = []
    lines = content.split('\n')
    
    current_block = []
    current_names = []
    block_start = 0
    block_comment = ""
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for section comment
        if stripped.startswith('//') and '===' in stripped:
            # Save previous block if any
            if current_block:
                constants.append(CodeChunk(
                    chunk_type='constant',
                    name=', '.join(current_names[:3]) + ('...' if len(current_names) > 3 else ''),
                    code='\n'.join(current_block),
                    start_line=block_start,
                    end_line=i,
                    description=block_comment or f"Constants: {', '.join(current_names[:5])}",
                    metadata={'names': current_names}
                ))
            current_block = [line]
            current_names = []
            block_start = i + 1
            block_comment = stripped.strip('/ =').strip()
            
        elif stripped.startswith('#define'):
            if not current_block:
                block_start = i + 1
            current_block.append(line)
            # Extract define name
            parts = stripped.split()
            if len(parts) >= 2:
                current_names.append(parts[1].split('(')[0])
                
        elif stripped.startswith('//') and current_block:
            current_block.append(line)
            
        elif not stripped and current_block and len(current_block) > 1:
            # Empty line ends a block
            constants.append(CodeChunk(
                chunk_type='constant',
                name=', '.join(current_names[:3]) + ('...' if len(current_names) > 3 else ''),
                code='\n'.join(current_block),
                start_line=block_start,
                end_line=i,
                description=block_comment or f"Constants: {', '.join(current_names[:5])}",
                metadata={'names': current_names}
            ))
            current_block = []
            current_names = []
            block_comment = ""
    
    # Don't forget last block
    if current_block:
        constants.append(CodeChunk(
            chunk_type='constant',
            name=', '.join(current_names[:3]) + ('...' if len(current_names) > 3 else ''),
            code='\n'.join(current_block),
            start_line=block_start,
            end_line=len(lines),
            description=block_comment or f"Constants: {', '.join(current_names[:5])}",
            metadata={'names': current_names}
        ))
    
    return constants


def extract_all_chunks(content: str, file_path: str = "") -> List[CodeChunk]:
    """
    Extract all meaningful code chunks from a C source file.
    
    Args:
        content: C source code
        file_path: Path to file (for context)
        
    Returns:
        List of all extracted CodeChunk objects
    """
    chunks = []
    
    # Determine file type from path
    is_header = file_path.endswith('.h')
    is_sprites = 'sprite' in file_path.lower()
    
    # Extract based on file type
    if is_header:
        chunks.extend(extract_structs(content))
        chunks.extend(extract_constants(content))
    else:
        chunks.extend(extract_functions(content))
        chunks.extend(extract_sprite_arrays(content))
    
    # Always look for sprites in any file
    if not is_sprites:
        sprites = extract_sprite_arrays(content)
        # Avoid duplicates
        existing_names = {c.name for c in chunks}
        chunks.extend(s for s in sprites if s.name not in existing_names)
    
    return chunks


# ============================================================
# Helper Functions
# ============================================================

def extract_preceding_comment(content: str, pos: int) -> str:
    """Extract the comment block immediately preceding a position."""
    # Look backwards for comment
    before = content[:pos].rstrip()
    
    # Check for /** */ style comment
    if before.endswith('*/'):
        start = before.rfind('/**')
        if start == -1:
            start = before.rfind('/*')
        if start != -1:
            comment = before[start:]
            # Clean up the comment
            lines = comment.split('\n')
            cleaned = []
            for line in lines:
                line = line.strip()
                line = re.sub(r'^/\*\*?', '', line)
                line = re.sub(r'\*/$', '', line)
                line = re.sub(r'^\*\s?', '', line)
                if line:
                    cleaned.append(line)
            return ' '.join(cleaned)
    
    # Check for // style comments
    lines = before.split('\n')
    comment_lines = []
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith('//'):
            comment_lines.insert(0, stripped[2:].strip())
        elif stripped:
            break
    
    return ' '.join(comment_lines) if comment_lines else ""


def categorize_function(name: str, code: str) -> str:
    """Categorize a function by its likely purpose."""
    name_lower = name.lower()
    code_lower = code.lower()
    
    if 'init' in name_lower:
        return 'initialization'
    elif 'update' in name_lower:
        return 'game_logic'
    elif 'render' in name_lower or 'draw' in name_lower:
        return 'rendering'
    elif 'collision' in name_lower or 'check' in name_lower:
        return 'collision'
    elif 'input' in name_lower or 'joypad' in code_lower:
        return 'input'
    elif 'sprite' in name_lower:
        return 'sprites'
    elif 'sound' in name_lower or 'audio' in name_lower or 'music' in name_lower:
        return 'audio'
    elif 'save' in name_lower or 'load' in name_lower:
        return 'persistence'
    elif 'score' in name_lower:
        return 'ui'
    else:
        return 'other'


def parse_hex_array(data: str) -> List[int]:
    """Parse hex values from an array initializer."""
    hex_pattern = re.compile(r'0x([0-9A-Fa-f]{2})')
    return [int(m.group(1), 16) for m in hex_pattern.finditer(data)]


def extract_frame_count(comments: str, name: str, num_tiles: int) -> int:
    """Try to determine how many animation frames are in a sprite array."""
    # Look for explicit frame count in comments
    frame_match = re.search(r'(\d+)\s*frames?', comments.lower())
    if frame_match:
        return int(frame_match.group(1))
    
    # Look for tile descriptions
    tile_matches = re.findall(r'tile\s*(\d+)', comments.lower())
    if tile_matches:
        return len(set(tile_matches))
    
    # Guess based on number of tiles
    if num_tiles <= 1:
        return 1
    elif num_tiles <= 4:
        return num_tiles
    else:
        return num_tiles // 2  # Assume pairs for animation


def extract_sprite_description(comments: str, name: str, num_tiles: int) -> str:
    """Generate a description for a sprite array."""
    # Try to extract description from comments
    if comments:
        # Get first meaningful line
        for line in comments.split('\n'):
            line = line.strip()
            line = re.sub(r'^[/\*\s]+', '', line)
            line = re.sub(r'[\*\/\s]+$', '', line)
            if line and not line.startswith('@'):
                return f"{name}: {line}"
    
    # Generate from name
    readable_name = re.sub(r'_', ' ', name)
    return f"Sprite data '{readable_name}' with {num_tiles} tile(s)"


if __name__ == "__main__":
    # Test with a sample file
    import sys
    from pathlib import Path
    
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
        content = file_path.read_text()
        
        chunks = extract_all_chunks(content, str(file_path))
        
        print(f"Found {len(chunks)} chunks in {file_path.name}:\n")
        for chunk in chunks:
            print(f"[{chunk.chunk_type}] {chunk.name}")
            print(f"  Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"  Description: {chunk.description[:80]}...")
            print(f"  Metadata: {chunk.metadata}")
            print()
    else:
        print("Usage: python chunkers.py <file.c>")
