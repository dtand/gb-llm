#!/usr/bin/env python3
"""
Workspace manager for the coding agent.

Handles project scaffolding, file operations, and build execution.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


def sanitize_project_name(name: str) -> str:
    """Sanitize project name for use in Makefiles (no spaces or special chars)."""
    # Remove spaces and keep only alphanumeric, underscore, hyphen
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(' ', ''))
    return sanitized or 'Game'


# Template Makefile for new projects
MAKEFILE_TEMPLATE = '''# GBDK-2020 Makefile
PROJECT_NAME = {project_name}

# GBDK paths
GBDK = /usr/local/gbdk
LCC = $(GBDK)/bin/lcc

# Data generator
DATA_GEN = python3 $(GBLLM_ROOT)/src/generator/data_generator.py

# Compiler flags
LCCFLAGS = -Wa-l -Wl-m -Wl-j

# Source files - auto-discover all .c files in src/ and build/
SRCS = $(wildcard src/*.c) $(wildcard build/*.c)

# Output
ROM = build/$(PROJECT_NAME).gb

all: datagen $(ROM)

# Generate data.c/data.h from schema (if _schema.json exists)
datagen:
\t@if [ -f _schema.json ]; then $(DATA_GEN) .; fi

$(ROM): $(SRCS)
\t@mkdir -p build
\t$(LCC) $(LCCFLAGS) -o $@ $^

clean:
\trm -rf build

run: $(ROM)
\topen -a SameBoy $(ROM)

.PHONY: all clean run datagen
'''

# Template main.c
MAIN_C_TEMPLATE = '''#include <gb/gb.h>
#include "game.h"
#include "sprites.h"

void main(void) {{
    // Initialize sprites
    sprites_init();
    
    // Initialize game
    game_init();
    
    // Main loop
    while(1) {{
        game_update();
        game_render();
        vsync();
    }}
}}
'''

# Template game.h
GAME_H_TEMPLATE = '''#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// Game state structure
typedef struct {{
    uint8_t initialized;
    // Add game state fields here
}} GameState;

extern GameState game;

void game_init(void);
void game_update(void);
void game_render(void);

#endif
'''

# Template game.c
GAME_C_TEMPLATE = '''#include "game.h"
#include "sprites.h"
#include <gb/gb.h>

GameState game;

void game_init(void) {{
    game.initialized = 1;
    // Initialize game state here
}}

void game_update(void) {{
    // Update game logic here
}}

void game_render(void) {{
    // Render game objects here
}}
'''

# Template sprites.h
SPRITES_H_TEMPLATE = '''#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

void sprites_init(void);

#endif
'''

# Template sprites.c
SPRITES_C_TEMPLATE = '''#include "sprites.h"
#include <gb/gb.h>

// Sprite tile data - 8x8 pixels, 2bpp
// Each row is 2 bytes (16 bytes total per tile)
const uint8_t sprite_data[] = {{
    // Empty placeholder sprite
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00
}};

void sprites_init(void) {{
    // Load sprite tiles into VRAM
    set_sprite_data(0, 1, sprite_data);
    
    // Enable sprites
    SHOW_SPRITES;
}}
'''


@dataclass
class BuildResult:
    """Result of a build attempt."""
    success: bool
    output: str
    error: str
    rom_path: Optional[Path] = None


class Workspace:
    """Manages a game project workspace."""
    
    def __init__(self, path: Path, project_name: str = "game"):
        """
        Initialize workspace.
        
        Args:
            path: Directory for the workspace
            project_name: Name of the game project
        """
        self.path = Path(path)
        self.project_name = project_name
        self.src_dir = self.path / "src"
        self.build_dir = self.path / "build"
        
    def scaffold(self) -> None:
        """Create the initial project structure with template files."""
        # Create directories
        self.path.mkdir(parents=True, exist_ok=True)
        self.src_dir.mkdir(exist_ok=True)
        self.build_dir.mkdir(exist_ok=True)
        
        # Create Makefile (sanitize name for shell compatibility)
        makefile = self.path / "Makefile"
        if not makefile.exists():
            safe_name = sanitize_project_name(self.project_name)
            makefile.write_text(MAKEFILE_TEMPLATE.format(project_name=safe_name))
        
        # Create source files
        templates = {
            "main.c": MAIN_C_TEMPLATE,
            "game.h": GAME_H_TEMPLATE,
            "game.c": GAME_C_TEMPLATE,
            "sprites.h": SPRITES_H_TEMPLATE,
            "sprites.c": SPRITES_C_TEMPLATE,
        }
        
        for filename, content in templates.items():
            filepath = self.src_dir / filename
            if not filepath.exists():
                filepath.write_text(content)
    
    def read_file(self, relative_path: str) -> Optional[str]:
        """Read a file from the workspace."""
        filepath = self.path / relative_path
        if filepath.exists():
            return filepath.read_text()
        return None
    
    def write_file(self, relative_path: str, content: str) -> None:
        """Write content to a file in the workspace."""
        filepath = self.path / relative_path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
    
    def list_files(self, pattern: str = "**/*") -> list[Path]:
        """List files in the workspace matching a pattern."""
        return [p for p in self.path.glob(pattern) if p.is_file()]
    
    def build(self, clean: bool = False) -> BuildResult:
        """
        Build the project.
        
        Args:
            clean: Whether to clean before building
            
        Returns:
            BuildResult with success status and output
        """
        try:
            if clean:
                # Run make clean first
                subprocess.run(
                    ["make", "clean"],
                    cwd=self.path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            # Run make - combine stdout and stderr for complete output
            result = subprocess.run(
                ["make"],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            rom_path = self.build_dir / f"{self.project_name}.gb"
            
            # Combine stdout and stderr for complete error context
            combined_output = result.stdout
            if result.stderr:
                combined_output += "\n" + result.stderr
            
            return BuildResult(
                success=result.returncode == 0,
                output=combined_output,
                error=result.stderr if result.returncode != 0 else None,
                rom_path=rom_path if rom_path.exists() else None
            )
            
        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                output="",
                error="Build timed out after 60 seconds"
            )
        except Exception as e:
            return BuildResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def clean(self) -> None:
        """Remove build artifacts."""
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
    
    def get_current_state(self) -> dict:
        """Get a summary of the current workspace state."""
        files = {}
        for filepath in self.src_dir.glob("**/*"):
            if filepath.is_file():
                rel_path = filepath.relative_to(self.path)
                files[str(rel_path)] = filepath.read_text()
        
        return {
            "project_name": self.project_name,
            "path": str(self.path),
            "files": files
        }
    
    def create_checkpoint(self) -> dict[str, str]:
        """
        Create a checkpoint of the current source files.
        
        Returns:
            Dict of filepath -> content for all source files
        """
        checkpoint = {}
        for filepath in self.src_dir.glob("**/*"):
            if filepath.is_file():
                rel_path = str(filepath.relative_to(self.path))
                checkpoint[rel_path] = filepath.read_text()
        return checkpoint
    
    def restore_checkpoint(self, checkpoint: dict[str, str]) -> None:
        """
        Restore workspace to a previous checkpoint state.
        
        Args:
            checkpoint: Dict of filepath -> content to restore
        """
        # Get current files
        current_files = set()
        for filepath in self.src_dir.glob("**/*"):
            if filepath.is_file():
                current_files.add(str(filepath.relative_to(self.path)))
        
        # Restore checkpoint files
        for rel_path, content in checkpoint.items():
            self.write_file(rel_path, content)
        
        # Remove files that weren't in the checkpoint
        checkpoint_files = set(checkpoint.keys())
        for rel_path in current_files - checkpoint_files:
            filepath = self.path / rel_path
            if filepath.exists():
                filepath.unlink()
