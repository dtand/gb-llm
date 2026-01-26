"""
Sprite visualization utilities.

Converts GameBoy 2bpp sprite data to ASCII art for human-readable
previews and better LLM understanding.
"""

from typing import List, Tuple, Optional


# ASCII characters for different pixel intensities (2bpp = 4 colors)
ASCII_CHARS = ['.', '░', '▒', '█']  # 0=transparent, 1=light, 2=medium, 3=dark
ASCII_CHARS_SIMPLE = ['.', '+', '#', '@']  # Fallback for terminals without unicode


def hex_to_2bpp_pixels(hex_bytes: List[int], width: int = 8) -> List[List[int]]:
    """
    Convert 2bpp hex data to a 2D pixel array.
    
    GameBoy 2bpp format:
    - Each row is 2 bytes
    - Byte 1: low bits of each pixel
    - Byte 2: high bits of each pixel
    - Pixels are MSB first (left to right)
    
    Args:
        hex_bytes: List of bytes (should be even number)
        width: Sprite width in pixels (default 8)
        
    Returns:
        2D list of pixel values (0-3)
    """
    pixels = []
    
    # Process 2 bytes at a time (one row)
    for i in range(0, len(hex_bytes) - 1, 2):
        low_byte = hex_bytes[i]
        high_byte = hex_bytes[i + 1]
        
        row = []
        for bit in range(7, -1, -1):  # MSB first
            low_bit = (low_byte >> bit) & 1
            high_bit = (high_byte >> bit) & 1
            pixel = low_bit | (high_bit << 1)
            row.append(pixel)
        
        pixels.append(row)
    
    return pixels


def pixels_to_ascii(pixels: List[List[int]], use_unicode: bool = True) -> str:
    """
    Convert a pixel array to ASCII art.
    
    Args:
        pixels: 2D list of pixel values (0-3)
        use_unicode: Whether to use unicode block characters
        
    Returns:
        ASCII art string
    """
    chars = ASCII_CHARS if use_unicode else ASCII_CHARS_SIMPLE
    
    lines = []
    for row in pixels:
        line = ''.join(chars[min(p, 3)] for p in row)
        lines.append(line)
    
    return '\n'.join(lines)


def sprite_to_ascii(hex_bytes: List[int], 
                    width: int = 8, 
                    height: int = 8,
                    use_unicode: bool = True) -> str:
    """
    Convert sprite hex data directly to ASCII art.
    
    Args:
        hex_bytes: Sprite data bytes
        width: Sprite width (default 8)
        height: Sprite height (default 8)
        use_unicode: Whether to use unicode characters
        
    Returns:
        ASCII art representation
    """
    # Calculate how many bytes we need
    bytes_needed = (width // 8) * height * 2
    
    if len(hex_bytes) < bytes_needed:
        # Pad with zeros if needed
        hex_bytes = list(hex_bytes) + [0] * (bytes_needed - len(hex_bytes))
    
    pixels = hex_to_2bpp_pixels(hex_bytes[:bytes_needed], width)
    return pixels_to_ascii(pixels, use_unicode)


def sprite_array_to_ascii(hex_bytes: List[int],
                          tiles_per_row: int = 1,
                          max_tiles: int = 8,
                          use_unicode: bool = True,
                          tile_labels: Optional[List[str]] = None) -> str:
    """
    Convert a multi-tile sprite array to ASCII art with labels.
    
    Args:
        hex_bytes: All sprite data bytes
        tiles_per_row: How many tiles to show per row
        max_tiles: Maximum tiles to render
        use_unicode: Whether to use unicode characters
        tile_labels: Optional labels for each tile
        
    Returns:
        Formatted ASCII art with tile labels
    """
    # Each tile is 16 bytes (8 rows × 2 bytes per row)
    bytes_per_tile = 16
    num_tiles = min(len(hex_bytes) // bytes_per_tile, max_tiles)
    
    if num_tiles == 0:
        return "(no tile data)"
    
    # Render each tile
    tile_renders = []
    for i in range(num_tiles):
        start = i * bytes_per_tile
        end = start + bytes_per_tile
        tile_bytes = hex_bytes[start:end]
        
        label = tile_labels[i] if tile_labels and i < len(tile_labels) else f"Tile {i}"
        ascii_art = sprite_to_ascii(tile_bytes, use_unicode=use_unicode)
        
        tile_renders.append((label, ascii_art))
    
    # Format output
    output_lines = []
    
    for row_start in range(0, len(tile_renders), tiles_per_row):
        row_tiles = tile_renders[row_start:row_start + tiles_per_row]
        
        # Add labels
        labels = [f"{t[0]:^10}" for t in row_tiles]
        output_lines.append('  '.join(labels))
        output_lines.append('-' * (12 * len(row_tiles)))
        
        # Add sprite rows side by side
        sprite_rows = [t[1].split('\n') for t in row_tiles]
        max_rows = max(len(r) for r in sprite_rows)
        
        for row_idx in range(max_rows):
            row_parts = []
            for sprite in sprite_rows:
                if row_idx < len(sprite):
                    row_parts.append(f"  {sprite[row_idx]}  ")
                else:
                    row_parts.append("          ")
            output_lines.append(''.join(row_parts))
        
        output_lines.append('')  # Blank line between rows
    
    return '\n'.join(output_lines)


def create_sprite_preview(name: str, 
                          hex_bytes: List[int],
                          num_tiles: int,
                          description: str = "",
                          comments: str = "") -> str:
    """
    Create a complete sprite preview for inclusion in prompts.
    
    Args:
        name: Sprite array name
        hex_bytes: Sprite data bytes
        num_tiles: Number of tiles in the sprite
        description: Short description
        comments: Original code comments
        
    Returns:
        Formatted preview string
    """
    lines = [
        f"### Sprite: {name}",
        f"Tiles: {num_tiles} | Bytes: {len(hex_bytes)}",
    ]
    
    if description:
        lines.append(f"Description: {description}")
    
    lines.append("")
    lines.append("```")
    lines.append(sprite_array_to_ascii(hex_bytes, tiles_per_row=4, max_tiles=8))
    lines.append("```")
    
    return '\n'.join(lines)


def ascii_to_hex(ascii_art: str, char_map: dict = None) -> List[int]:
    """
    Convert ASCII art back to hex bytes (for generating new sprites).
    
    Args:
        ascii_art: ASCII representation (8 chars wide per tile)
        char_map: Optional mapping of chars to pixel values
        
    Returns:
        List of hex bytes in 2bpp format
    """
    if char_map is None:
        # Default mapping (reverse of ASCII_CHARS)
        char_map = {'.': 0, ' ': 0, '░': 1, '+': 1, '▒': 2, '#': 2, '█': 3, '@': 3}
    
    hex_bytes = []
    
    for line in ascii_art.strip().split('\n'):
        if not line or len(line) < 8:
            continue
            
        # Take first 8 characters
        row = line[:8]
        
        low_byte = 0
        high_byte = 0
        
        for i, char in enumerate(row):
            pixel = char_map.get(char, 0)
            bit_pos = 7 - i
            
            low_byte |= ((pixel & 1) << bit_pos)
            high_byte |= (((pixel >> 1) & 1) << bit_pos)
        
        hex_bytes.extend([low_byte, high_byte])
    
    return hex_bytes


def format_hex_array(hex_bytes: List[int], 
                     bytes_per_line: int = 2,
                     with_comments: bool = True) -> str:
    """
    Format hex bytes as a C array initializer.
    
    Args:
        hex_bytes: Bytes to format
        bytes_per_line: Bytes per line (default 2 = one row)
        with_comments: Add ASCII preview comments
        
    Returns:
        Formatted C code string
    """
    lines = []
    
    for i in range(0, len(hex_bytes), bytes_per_line):
        chunk = hex_bytes[i:i + bytes_per_line]
        hex_str = ', '.join(f'0x{b:02X}' for b in chunk)
        
        if with_comments and bytes_per_line == 2 and len(chunk) == 2:
            # Generate ASCII comment for this row
            pixels = []
            for bit in range(7, -1, -1):
                low_bit = (chunk[0] >> bit) & 1
                high_bit = (chunk[1] >> bit) & 1
                pixel = low_bit | (high_bit << 1)
                pixels.append(ASCII_CHARS_SIMPLE[pixel])
            
            line = f"    {hex_str},  // {''.join(pixels)}"
        else:
            line = f"    {hex_str},"
        
        lines.append(line)
    
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test with sample sprite data
    print("=== Sprite Visualizer Test ===\n")
    
    # Sample cat sprite (8x8)
    cat_sprite = [
        0x00, 0x00,  # ........
        0x70, 0x70,  # .***....
        0x88, 0x88,  # *...*...
        0xF8, 0x88,  # *****...
        0x7E, 0x72,  # .******.
        0x0F, 0x09,  # ....****
        0x0A, 0x0A,  # ....*.*.
        0x00, 0x00,  # ........
    ]
    
    print("Cat sprite (8x8):")
    print(sprite_to_ascii(cat_sprite))
    print()
    
    # Test multi-tile display
    multi_tile = cat_sprite * 3  # 3 copies
    print("Multi-tile display:")
    print(sprite_array_to_ascii(
        multi_tile, 
        tiles_per_row=3,
        tile_labels=["Idle", "Run 1", "Run 2"]
    ))
    
    # Test hex formatting
    print("\nFormatted as C code:")
    print(format_hex_array(cat_sprite, with_comments=True))
