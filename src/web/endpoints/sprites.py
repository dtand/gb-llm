"""
Sprite viewing and editing endpoints.
"""
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import SaveSpriteRequest
from endpoints.utils import parse_sprites_from_c, generate_sprite_c_code

router = APIRouter(prefix="/api/v2/projects/{project_id}/sprites", tags=["sprites"])


@router.get("/")
async def get_project_sprites(project_id: str):
    """
    Parse and return all sprites from the project's sprites.c file.
    
    Returns sprite data that can be rendered client-side.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Look for sprites.c in src directory
    src_dir = Path(project.path) / "src"
    sprites_file = src_dir / "sprites.c"
    
    if not sprites_file.exists():
        return {"sprites": [], "source_file": None}
    
    try:
        content = sprites_file.read_text()
        sprites = parse_sprites_from_c(content)
        
        return {
            "sprites": sprites,
            "source_file": "src/sprites.c",
            "total_bytes": sum(s["byte_count"] for s in sprites)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse sprites: {str(e)}")


@router.post("/")
async def save_project_sprite(project_id: str, request: SaveSpriteRequest):
    """
    Save a sprite to the project's sprites.c file.
    
    If replace is specified, replaces that sprite. Otherwise appends.
    """
    api = get_api()
    
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    src_dir = Path(project.path) / "src"
    sprites_file = src_dir / "sprites.c"
    sprites_header = src_dir / "sprites.h"
    
    # Generate new sprite code
    new_sprite_code = generate_sprite_c_code(
        request.name, request.width, request.height, request.data
    )
    
    if sprites_file.exists():
        content = sprites_file.read_text()
        
        if request.replace:
            # Find and replace existing sprite
            pattern = rf'/\*\*[\s\S]*?\*/\s*const\s+(?:uint8_t|unsigned\s+char)\s+{re.escape(request.replace)}\s*\[\s*\]\s*=\s*\{{[^}}]+\}};'
            
            if re.search(pattern, content):
                content = re.sub(pattern, new_sprite_code, content)
            else:
                # Sprite not found, append instead
                content = content.rstrip() + "\n\n" + new_sprite_code + "\n"
        else:
            # Append new sprite
            content = content.rstrip() + "\n\n" + new_sprite_code + "\n"
    else:
        # Create new sprites.c file
        content = f"""/**
 * @file    sprites.c
 * @brief   Sprite tile data
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

{new_sprite_code}
"""
        # Also create sprites.h if it doesn't exist
        if not sprites_header.exists():
            header_content = """/**
 * @file    sprites.h
 * @brief   Sprite definitions
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

void sprites_init(void);

#endif
"""
            sprites_header.write_text(header_content)
    
    # Write updated content
    sprites_file.write_text(content)
    
    return {"success": True, "message": f"Sprite '{request.name}' saved"}
