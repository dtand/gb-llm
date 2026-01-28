"""
Project API for managing game projects.

Provides CRUD operations, template forking, conversation tracking,
and build management for game projects.
"""

import os
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict

# Handle both package and direct imports
try:
    from .context.summary_generator import SummaryGenerator, generate_summary
    from .context.schemas import ProjectSummary
except ImportError:
    from context.summary_generator import SummaryGenerator, generate_summary
    from context.schemas import ProjectSummary


# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
GAMES_DIR = PROJECT_ROOT / "games"
PROJECTS_DIR = GAMES_DIR / "projects"
SAMPLES_DIR = GAMES_DIR / "samples"
MANIFEST_PATH = PROJECTS_DIR / "manifest.json"


def sanitize_project_name(name: str) -> str:
    """Sanitize project name for use in Makefiles (no spaces or special chars)."""
    import re
    # Remove spaces and keep only alphanumeric, underscore, hyphen
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(' ', ''))
    return sanitized or 'Game'


@dataclass
class ConversationTurn:
    """A single turn in the conversation history."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str
    metadata: dict = field(default_factory=dict)  # agent info, context used, etc.


@dataclass 
class Project:
    """Full project representation."""
    id: str
    name: str
    description: str
    status: str
    template_source: Optional[str]
    created_at: str
    updated_at: str
    path: Path
    rom_path: Optional[str] = None
    summary: Optional[ProjectSummary] = None
    conversation: list[ConversationTurn] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "template_source": self.template_source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "path": str(self.path),
            "rom_path": self.rom_path,
            "summary": self.summary.to_dict() if self.summary else None,
            "conversation": [asdict(t) for t in self.conversation]
        }


class ProjectAPI:
    """API for managing game projects."""
    
    def __init__(self):
        """Initialize the Project API."""
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_manifest()
    
    def _ensure_manifest(self):
        """Ensure the projects manifest exists."""
        if not MANIFEST_PATH.exists():
            MANIFEST_PATH.write_text(json.dumps({
                "version": "1.0.0",
                "projects": []
            }, indent=2))
    
    def _load_manifest(self) -> dict:
        """Load the projects manifest."""
        return json.loads(MANIFEST_PATH.read_text())
    
    def _save_manifest(self, manifest: dict):
        """Save the projects manifest."""
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    
    def _add_to_manifest(self, project_id: str, name: str, template: Optional[str]):
        """Add a project to the manifest."""
        manifest = self._load_manifest()
        manifest["projects"].append({
            "id": project_id,
            "name": name,
            "template_source": template,
            "created_at": datetime.now().isoformat()
        })
        self._save_manifest(manifest)
    
    # =========================================================================
    # CREATE
    # =========================================================================
    
    def create_project(
        self,
        prompt: str,
        template_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> Project:
        """
        Create a new project, optionally forking from a template.
        
        Args:
            prompt: The user's description of what they want to build
            template_id: Optional sample ID to fork from (e.g., "platformer")
            name: Optional project name (auto-generated if not provided)
            
        Returns:
            The created Project object
        """
        project_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Generate name from prompt if not provided
        if not name:
            # Take first few words of prompt
            words = prompt.split()[:3]
            name = "-".join(w.lower() for w in words if w.isalnum())
            if not name:
                name = f"project-{project_id[:8]}"
        
        project_path = PROJECTS_DIR / project_id
        
        if template_id:
            # Fork from template
            template_path = SAMPLES_DIR / template_id
            if not template_path.exists():
                raise ValueError(f"Template '{template_id}' not found")
            
            self._fork_template(template_path, project_path, name)
            template_metadata = self._load_sample_metadata(template_id)
        else:
            # Create empty scaffold
            self._scaffold_project(project_path, name)
            template_metadata = None
        
        # Create metadata.json
        metadata = {
            "id": project_id,
            "name": name,
            "description": prompt,
            "status": "created",
            "created_at": timestamp,
            "updated_at": timestamp,
            "build_attempts": 0,
            "current_step": 0,
            "total_steps": 0,
            "rom_path": None,
            "error": None,
            "verified": False,
            "verification_details": None,
            "human_feedback": [],
            "refinement_count": 0,
            "template_source": template_id
        }
        (project_path / "metadata.json").write_text(json.dumps(metadata, indent=2))
        
        # Create context folder and initial files
        context_dir = project_path / "context"
        context_dir.mkdir(exist_ok=True)
        
        # Initialize conversation.json with the initial prompt
        conversation = {
            "project_id": project_id,
            "turns": [
                {
                    "role": "user",
                    "content": prompt,
                    "timestamp": timestamp,
                    "metadata": {"type": "initial_prompt"}
                }
            ],
            "created_at": timestamp
        }
        (context_dir / "conversation.json").write_text(json.dumps(conversation, indent=2))
        
        # Generate initial summary
        generator = SummaryGenerator(str(project_path))
        summary = generator.generate(template_metadata)
        generator.save_summary(summary)
        
        # Add to manifest
        self._add_to_manifest(project_id, name, template_id)
        
        return self.get_project(project_id)
    
    def _fork_template(self, template_path: Path, project_path: Path, name: str):
        """Fork a template sample to create a new project."""
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Copy src/ directory
        src_template = template_path / "src"
        src_dest = project_path / "src"
        if src_template.exists():
            shutil.copytree(src_template, src_dest)
        
        # Copy data schema if exists
        schema_template = template_path / "_schema.json"
        if schema_template.exists():
            shutil.copy(schema_template, project_path / "_schema.json")
        
        # Copy data/ directory if exists
        data_template = template_path / "data"
        data_dest = project_path / "data"
        if data_template.exists():
            shutil.copytree(data_template, data_dest)
        
        # Copy Makefile and update project name (sanitized for shell compatibility)
        makefile_template = template_path / "Makefile"
        if makefile_template.exists():
            makefile_content = makefile_template.read_text()
            safe_name = sanitize_project_name(name)
            # Update PROJECT or PROJECT_NAME (both formats exist in samples)
            import re
            # Try PROJECT_NAME format first
            makefile_content = re.sub(
                r'PROJECT_NAME\s*=\s*\w+',
                f'PROJECT_NAME = {safe_name}',
                makefile_content
            )
            # Also try PROJECT format
            makefile_content = re.sub(
                r'PROJECT\s*=\s*\w+',
                f'PROJECT = {safe_name}',
                makefile_content
            )
            (project_path / "Makefile").write_text(makefile_content)
        
        # Create empty build/ directory
        (project_path / "build").mkdir(exist_ok=True)
    
    def _scaffold_project(self, project_path: Path, name: str):
        """Create an empty project scaffold with minimal starter code."""
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "build").mkdir(exist_ok=True)
        
        # Create minimal Makefile with data generation and symbol index support
        safe_name = sanitize_project_name(name)
        makefile = f'''# {safe_name} - GameBoy ROM Makefile

PROJECT = {safe_name}
GBDK = $(GBDK_HOME)
LCC = $(GBDK)/bin/lcc

# Tools (set GBLLM_ROOT or use relative path)
GBLLM_ROOT ?= ../../..
SCHEMA_GEN = python3 $(GBLLM_ROOT)/tools/gen_schema.py
DATA_GEN = python3 $(GBLLM_ROOT)/src/generator/data_generator.py
SYMBOL_GEN = python3 $(GBLLM_ROOT)/tools/gen_symbols.py

CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"$(PROJECT)"
SOURCES = $(wildcard src/*.c)
BUILD_DIR = build
ROM = $(BUILD_DIR)/$(PROJECT).gb
SYMBOLS = context/symbols.json

# Include data.c if schema exists
ifneq ($(wildcard _schema.json),)
DATA_SRC = build/data.c
endif

all: schema datagen $(ROM) symbols

# Generate _schema.json from @config annotations in headers
schema:
\t@$(SCHEMA_GEN) src/ _schema.json

# Generate data.c/data.h from _schema.json (if exists)
datagen: schema
\t@if [ -f _schema.json ]; then $(DATA_GEN) .; fi

# Generate symbol index for AI agents
symbols: $(SOURCES)
\t@mkdir -p context
\t@$(SYMBOL_GEN) src context/symbols.json

$(ROM): $(SOURCES) datagen
\t@mkdir -p $(BUILD_DIR)
\t$(LCC) $(CFLAGS) -o $(ROM) $(SOURCES) $(DATA_SRC)
\t@echo ""
\t@echo "Build complete: $(ROM)"
\t@ls -la $(ROM)

clean:
\trm -rf $(BUILD_DIR)
\trm -f src/*.o src/*.lst src/*.sym src/*.asm

run: $(ROM)
\topen -a SameBoy $(ROM)

run-mgba: $(ROM)
\tmgba $(ROM)

rebuild: clean all

.PHONY: all clean run run-mgba rebuild schema datagen symbols
'''
        (project_path / "Makefile").write_text(makefile)
        
        # Create context directory for symbols
        (project_path / "context").mkdir(exist_ok=True)
        
        # Create starter main.c with proper game loop structure
        main_c = '''/**
 * @file    main.c
 * @brief   Entry point for GameBoy game
 * 
 * Initializes the game and runs the main loop.
 * All game logic is delegated to game.c
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

/**
 * @brief   Main entry point
 * 
 * Initializes graphics and game state, then runs the
 * main game loop at ~60fps using vsync.
 */
void main(void) {
    // Initialize graphics and game state
    sprites_init();
    game_init();
    
    // Enable display features
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        // Wait for vertical blank (sync to ~60fps)
        wait_vbl_done();
        
        // Process input and update game
        game_handle_input();
        game_update();
        game_render();
    }
}
'''
        (project_path / "src" / "main.c").write_text(main_c)
        
        # Create sprites.h
        sprites_h = '''/**
 * @file    sprites.h
 * @brief   Sprite definitions and graphics initialization
 * 
 * Contains sprite tile data and initialization functions.
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// Sprite Constants
// ============================================================

// Screen dimensions
#define SCREEN_WIDTH    160
#define SCREEN_HEIGHT   144

// Sprite size (8x8 or 8x16 depending on LCDC settings)
#define SPRITE_WIDTH    8
#define SPRITE_HEIGHT   8

// Maximum sprites the GameBoy can display
#define MAX_SPRITES     40

// ============================================================
// Function Prototypes
// ============================================================

/**
 * @brief   Initialize sprite system
 * 
 * Loads sprite tile data into VRAM and configures
 * the sprite system for use.
 */
void sprites_init(void);

#endif /* SPRITES_H */
'''
        (project_path / "src" / "sprites.h").write_text(sprites_h)
        
        # Create sprites.c
        sprites_c = '''/**
 * @file    sprites.c
 * @brief   Sprite initialization and tile data
 * 
 * Implements sprite loading and graphics setup.
 */

#include "sprites.h"

// ============================================================
// Sprite Tile Data
// ============================================================

// Simple 8x8 placeholder sprite (filled square)
// Each row is 2 bytes: low bits, high bits for 4 colors
const uint8_t sprite_placeholder[] = {
    0xFF, 0xFF,  // Row 0: ████████
    0xFF, 0xFF,  // Row 1: ████████
    0xFF, 0xFF,  // Row 2: ████████
    0xFF, 0xFF,  // Row 3: ████████
    0xFF, 0xFF,  // Row 4: ████████
    0xFF, 0xFF,  // Row 5: ████████
    0xFF, 0xFF,  // Row 6: ████████
    0xFF, 0xFF   // Row 7: ████████
};

// ============================================================
// Function Implementations
// ============================================================

void sprites_init(void) {
    // Load placeholder sprite into tile 0
    set_sprite_data(0, 1, sprite_placeholder);
    
    // Hide all sprites initially
    for (uint8_t i = 0; i < MAX_SPRITES; i++) {
        move_sprite(i, 0, 0);
    }
}
'''
        (project_path / "src" / "sprites.c").write_text(sprites_c)
        
        # Create game.h
        game_h = '''/**
 * @file    game.h
 * @brief   Game state and logic declarations
 * 
 * Contains game state structures and function prototypes
 * for game initialization, input handling, and updates.
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// Game Constants
// ============================================================

// Game states
#define STATE_TITLE     0
#define STATE_PLAYING   1
#define STATE_GAMEOVER  2
#define STATE_PAUSED    3

// ============================================================
// Game State Structure
// ============================================================

typedef struct {
    uint8_t state;          // Current game state
    uint8_t score;          // Player score
    uint8_t frame_count;    // Frame counter for timing
} GameState;

// Global game state (defined in game.c)
extern GameState game;

// ============================================================
// Function Prototypes
// ============================================================

/**
 * @brief   Initialize game state
 * 
 * Sets up initial game state, resets score, and
 * prepares for gameplay.
 */
void game_init(void);

/**
 * @brief   Handle player input
 * 
 * Reads joypad and updates game state based on
 * button presses.
 */
void game_handle_input(void);

/**
 * @brief   Update game logic
 * 
 * Called once per frame to update game state,
 * move objects, check collisions, etc.
 */
void game_update(void);

/**
 * @brief   Render game graphics
 * 
 * Updates sprite positions and background tiles
 * to reflect current game state.
 */
void game_render(void);

#endif /* GAME_H */
'''
        (project_path / "src" / "game.h").write_text(game_h)
        
        # Create game.c
        game_c = '''/**
 * @file    game.c
 * @brief   Game state and logic implementation
 * 
 * Implements all game logic including initialization,
 * input handling, state updates, and rendering.
 */

#include "game.h"
#include "sprites.h"
#include <stdio.h>

// ============================================================
// Global State
// ============================================================

GameState game;

// ============================================================
// Initialization
// ============================================================

void game_init(void) {
    // Initialize game state
    game.state = STATE_TITLE;
    game.score = 0;
    game.frame_count = 0;
    
    // Display title message
    printf("\\n\\n   GAMEBOY GAME\\n");
    printf("\\n  Press START\\n");
}

// ============================================================
// Input Handling
// ============================================================

void game_handle_input(void) {
    uint8_t keys = joypad();
    
    switch (game.state) {
        case STATE_TITLE:
            // Start game on START button
            if (keys & J_START) {
                game.state = STATE_PLAYING;
                // Clear screen for gameplay
                printf("\\x1b[2J");  // ANSI clear screen
            }
            break;
            
        case STATE_PLAYING:
            // TODO: Add gameplay input handling
            // Example: if (keys & J_LEFT) { ... }
            
            // Pause on START
            if (keys & J_START) {
                game.state = STATE_PAUSED;
            }
            break;
            
        case STATE_PAUSED:
            // Resume on START
            if (keys & J_START) {
                game.state = STATE_PLAYING;
            }
            break;
            
        case STATE_GAMEOVER:
            // Restart on START
            if (keys & J_START) {
                game_init();
            }
            break;
    }
}

// ============================================================
// Game Logic
// ============================================================

void game_update(void) {
    // Increment frame counter
    game.frame_count++;
    
    switch (game.state) {
        case STATE_PLAYING:
            // TODO: Add game update logic
            // - Move player
            // - Update enemies
            // - Check collisions
            // - Update score
            break;
            
        default:
            // No updates in other states
            break;
    }
}

// ============================================================
// Rendering
// ============================================================

void game_render(void) {
    switch (game.state) {
        case STATE_PLAYING:
            // TODO: Add rendering logic
            // - Update sprite positions
            // - Update background tiles
            break;
            
        case STATE_PAUSED:
            // Could show pause indicator
            break;
            
        default:
            // No rendering updates
            break;
    }
}
'''
        (project_path / "src" / "game.c").write_text(game_c)
    
    def _load_sample_metadata(self, sample_id: str) -> Optional[dict]:
        """Load metadata for a sample."""
        metadata_path = SAMPLES_DIR / sample_id / "metadata.json"
        if metadata_path.exists():
            return json.loads(metadata_path.read_text())
        return None
    
    # =========================================================================
    # READ
    # =========================================================================
    
    def get_project(self, project_id: str) -> Project:
        """
        Get a project by ID.
        
        Args:
            project_id: The project's UUID
            
        Returns:
            Project object with all details
        """
        project_path = PROJECTS_DIR / project_id
        if not project_path.exists():
            raise ValueError(f"Project '{project_id}' not found")
        
        # Load metadata
        metadata_path = project_path / "metadata.json"
        if not metadata_path.exists():
            raise ValueError(f"Project '{project_id}' has no metadata")
        
        metadata = json.loads(metadata_path.read_text())
        
        # Load summary if exists
        summary = None
        summary_path = project_path / "context" / "summary.json"
        if summary_path.exists():
            summary = ProjectSummary.from_json(summary_path.read_text())
        
        # Load conversation if exists
        conversation = []
        conversation_path = project_path / "context" / "conversation.json"
        if conversation_path.exists():
            conv_data = json.loads(conversation_path.read_text())
            conversation = [
                ConversationTurn(**t) for t in conv_data.get("turns", [])
            ]
        
        return Project(
            id=metadata["id"],
            name=metadata["name"],
            description=metadata["description"],
            status=metadata["status"],
            template_source=metadata.get("template_source"),
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            path=project_path,
            rom_path=metadata.get("rom_path"),
            summary=summary,
            conversation=conversation
        )
    
    def list_projects(self, include_summary: bool = False) -> list[dict]:
        """
        List all projects.
        
        Args:
            include_summary: Whether to include full summaries (slower)
            
        Returns:
            List of project info dictionaries
        """
        projects = []
        
        for item in PROJECTS_DIR.iterdir():
            if not item.is_dir():
                continue
            
            metadata_path = item / "metadata.json"
            if not metadata_path.exists():
                continue
            
            metadata = json.loads(metadata_path.read_text())
            
            project_info = {
                "id": metadata["id"],
                "name": metadata["name"],
                "description": metadata["description"],
                "status": metadata["status"],
                "template_source": metadata.get("template_source"),
                "created_at": metadata["created_at"],
                "updated_at": metadata["updated_at"],
                "has_rom": metadata.get("rom_path") is not None
            }
            
            if include_summary:
                summary_path = item / "context" / "summary.json"
                if summary_path.exists():
                    project_info["summary"] = json.loads(summary_path.read_text())
            
            projects.append(project_info)
        
        # Sort by created_at descending
        projects.sort(key=lambda p: p["created_at"], reverse=True)
        return projects
    
    def list_templates(self) -> list[dict]:
        """
        List all available templates (samples).
        
        Returns:
            List of template info dictionaries
        """
        templates = []
        
        for item in SAMPLES_DIR.iterdir():
            if not item.is_dir():
                continue
            
            metadata_path = item / "metadata.json"
            if not metadata_path.exists():
                continue
            
            metadata = json.loads(metadata_path.read_text())
            
            templates.append({
                "id": item.name,
                "name": metadata.get("name", item.name),
                "description": metadata.get("description", ""),
                "complexity": metadata.get("complexity", 1),
                "features": metadata.get("features", []),
                "techniques": metadata.get("techniques", [])
            })
        
        # Sort by complexity then name
        templates.sort(key=lambda t: (t["complexity"], t["name"]))
        return templates
    
    # =========================================================================
    # SNAPSHOTS (Rollback Support)
    # =========================================================================
    
    def create_snapshot(self, project_id: str, description: str = "") -> dict:
        """
        Create a snapshot of the project's src/ directory for rollback.
        
        Args:
            project_id: The project's UUID
            description: Optional description of what changed
            
        Returns:
            Snapshot info dict with id, timestamp, and description
        """
        project_path = PROJECTS_DIR / project_id
        if not project_path.exists():
            raise ValueError(f"Project '{project_id}' not found")
        
        # Create snapshots directory
        snapshots_dir = project_path / "snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        
        # Load or create snapshot index
        index_path = snapshots_dir / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text())
        else:
            index = {"snapshots": []}
        
        # Create snapshot ID (incrementing number)
        snapshot_id = len(index["snapshots"]) + 1
        timestamp = datetime.now().isoformat()
        
        # Copy src/ to snapshot folder
        snapshot_dir = snapshots_dir / str(snapshot_id)
        src_dir = project_path / "src"
        
        if src_dir.exists():
            shutil.copytree(src_dir, snapshot_dir / "src")
        
        # Also copy metadata.json state
        metadata_path = project_path / "metadata.json"
        if metadata_path.exists():
            shutil.copy(metadata_path, snapshot_dir / "metadata.json")
        
        # Copy data schema and data files if they exist
        schema_path = project_path / "_schema.json"
        if schema_path.exists():
            shutil.copy(schema_path, snapshot_dir / "_schema.json")
        
        data_dir = project_path / "data"
        if data_dir.exists():
            shutil.copytree(data_dir, snapshot_dir / "data")
        
        # Update index
        snapshot_info = {
            "id": snapshot_id,
            "timestamp": timestamp,
            "description": description,
            "file_count": len(list((snapshot_dir / "src").glob("**/*"))) if (snapshot_dir / "src").exists() else 0
        }
        index["snapshots"].append(snapshot_info)
        index_path.write_text(json.dumps(index, indent=2))
        
        return snapshot_info
    
    def list_snapshots(self, project_id: str) -> list[dict]:
        """
        List all snapshots for a project.
        
        Args:
            project_id: The project's UUID
            
        Returns:
            List of snapshot info dicts
        """
        project_path = PROJECTS_DIR / project_id
        index_path = project_path / "snapshots" / "index.json"
        
        if not index_path.exists():
            return []
        
        index = json.loads(index_path.read_text())
        return index.get("snapshots", [])
    
    def rollback_to_snapshot(self, project_id: str, snapshot_id: int) -> dict:
        """
        Rollback project src/ to a previous snapshot.
        
        Args:
            project_id: The project's UUID
            snapshot_id: The snapshot ID to restore
            
        Returns:
            Result dict with success status and message
        """
        project_path = PROJECTS_DIR / project_id
        snapshot_dir = project_path / "snapshots" / str(snapshot_id)
        
        if not snapshot_dir.exists():
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        # First create a snapshot of current state (auto-backup)
        self.create_snapshot(project_id, f"Auto-backup before rollback to snapshot {snapshot_id}")
        
        # Remove current src/
        src_dir = project_path / "src"
        if src_dir.exists():
            shutil.rmtree(src_dir)
        
        # Restore from snapshot
        snapshot_src = snapshot_dir / "src"
        if snapshot_src.exists():
            shutil.copytree(snapshot_src, src_dir)
        else:
            src_dir.mkdir()
        
        # Restore schema and data if in snapshot
        snapshot_schema = snapshot_dir / "_schema.json"
        project_schema = project_path / "_schema.json"
        if snapshot_schema.exists():
            shutil.copy(snapshot_schema, project_schema)
        elif project_schema.exists():
            # Remove schema if snapshot didn't have one
            project_schema.unlink()
        
        snapshot_data = snapshot_dir / "data"
        project_data = project_path / "data"
        if snapshot_data.exists():
            if project_data.exists():
                shutil.rmtree(project_data)
            shutil.copytree(snapshot_data, project_data)
        elif project_data.exists():
            # Remove data dir if snapshot didn't have one
            shutil.rmtree(project_data)
        
        # Update metadata
        metadata_path = project_path / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["updated_at"] = datetime.now().isoformat()
        metadata["status"] = "scaffolded"  # Reset to scaffolded since we're rolling back
        metadata["rom_path"] = None
        metadata["error"] = None
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        # Update summary
        self.update_summary(project_id)
        
        return {
            "success": True,
            "message": f"Rolled back to snapshot {snapshot_id}",
            "snapshot_id": snapshot_id
        }
    
    # =========================================================================
    # UPDATE
    # =========================================================================
    
    def clear_conversation(self, project_id: str) -> dict:
        """
        Clear the conversation history and start fresh.
        
        Args:
            project_id: The project's UUID
            
        Returns:
            Empty conversation dict
        """
        project_path = PROJECTS_DIR / project_id
        conversation_path = project_path / "context" / "conversation.json"
        
        # Get project name for initial message
        project = self.get_project(project_id)
        
        # Create fresh conversation with just an initial message
        conv_data = {
            "project_id": project_id,
            "turns": [
                {
                    "role": "user",
                    "content": f"New chat started for: {project.name}",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {"type": "initial_prompt"}
                }
            ],
            "created_at": datetime.now().isoformat()
        }
        
        conversation_path.write_text(json.dumps(conv_data, indent=2))
        return conv_data
    
    def add_conversation_turn(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ConversationTurn:
        """
        Add a turn to the conversation history.
        
        Args:
            project_id: The project's UUID
            role: "user", "assistant", or "system"
            content: The message content
            metadata: Optional metadata (agent info, context used, etc.)
            
        Returns:
            The created ConversationTurn
        """
        project_path = PROJECTS_DIR / project_id
        conversation_path = project_path / "context" / "conversation.json"
        
        if not conversation_path.exists():
            # Create conversation file
            (project_path / "context").mkdir(exist_ok=True)
            conv_data = {
                "project_id": project_id,
                "turns": [],
                "created_at": datetime.now().isoformat()
            }
        else:
            conv_data = json.loads(conversation_path.read_text())
        
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        conv_data["turns"].append(asdict(turn))
        conversation_path.write_text(json.dumps(conv_data, indent=2))
        
        return turn
    
    def update_status(self, project_id: str, status: str, error: Optional[str] = None):
        """Update project status."""
        project_path = PROJECTS_DIR / project_id
        metadata_path = project_path / "metadata.json"
        
        metadata = json.loads(metadata_path.read_text())
        metadata["status"] = status
        metadata["updated_at"] = datetime.now().isoformat()
        if error is not None:
            metadata["error"] = error
        
        metadata_path.write_text(json.dumps(metadata, indent=2))
    
    def update_summary(self, project_id: str) -> ProjectSummary:
        """
        Regenerate the summary from current source files.
        
        Args:
            project_id: The project's UUID
            
        Returns:
            The updated ProjectSummary
        """
        project_path = PROJECTS_DIR / project_id
        
        # Load template metadata if available
        metadata = json.loads((project_path / "metadata.json").read_text())
        template_id = metadata.get("template_source")
        template_metadata = self._load_sample_metadata(template_id) if template_id else None
        
        # Regenerate
        generator = SummaryGenerator(str(project_path))
        summary = generator.generate(template_metadata)
        generator.save_summary(summary)
        
        return summary
    
    # =========================================================================
    # AGENT CONFIG
    # =========================================================================
    
    # Default agent configuration
    DEFAULT_AGENT_CONFIG = {
        "designer": {
            "enabled": True,
            "model": "claude-sonnet-4-20250514",
            "description": "Analyzes requests and assembles context for implementation"
        },
        "coder": {
            "enabled": True,
            "model": "claude-sonnet-4-20250514",
            "description": "Implements code changes based on designer's plan"
        },
        "reviewer": {
            "enabled": False,
            "model": "claude-sonnet-4-20250514",
            "description": "Reviews code changes for bugs and issues"
        },
        "cleanup": {
            "enabled": False,
            "model": "claude-sonnet-4-20250514",
            "description": "Refactors code to reduce duplication and complexity"
        }
    }
    
    # Available models
    AVAILABLE_MODELS = [
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "tier": "premium"},
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "tier": "standard"},
        {"id": "claude-haiku-3-5-20241022", "name": "Claude Haiku 3.5", "tier": "fast"},
    ]
    
    def get_agent_config(self, project_id: str) -> dict:
        """
        Get agent configuration for a project.
        
        Returns merged config: project overrides on top of defaults.
        """
        project_path = PROJECTS_DIR / project_id
        metadata_path = project_path / "metadata.json"
        
        if not metadata_path.exists():
            raise ValueError(f"Project '{project_id}' not found")
        
        metadata = json.loads(metadata_path.read_text())
        project_config = metadata.get("agent_config", {})
        
        # Merge with defaults (project config overrides defaults)
        merged = {}
        for agent_name, defaults in self.DEFAULT_AGENT_CONFIG.items():
            merged[agent_name] = {**defaults}
            if agent_name in project_config:
                merged[agent_name].update(project_config[agent_name])
        
        return {
            "agents": merged,
            "available_models": self.AVAILABLE_MODELS
        }
    
    def update_agent_config(self, project_id: str, agent_name: str, config: dict) -> dict:
        """
        Update configuration for a specific agent.
        
        Args:
            project_id: The project's UUID
            agent_name: Name of agent ("designer", "coder", "reviewer")
            config: Dict with "enabled" and/or "model" keys
            
        Returns:
            The updated full agent config
        """
        if agent_name not in self.DEFAULT_AGENT_CONFIG:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        project_path = PROJECTS_DIR / project_id
        metadata_path = project_path / "metadata.json"
        
        if not metadata_path.exists():
            raise ValueError(f"Project '{project_id}' not found")
        
        metadata = json.loads(metadata_path.read_text())
        
        # Initialize agent_config if not present
        if "agent_config" not in metadata:
            metadata["agent_config"] = {}
        
        # Initialize this agent's config if not present
        if agent_name not in metadata["agent_config"]:
            metadata["agent_config"][agent_name] = {}
        
        # Update allowed fields
        if "enabled" in config:
            metadata["agent_config"][agent_name]["enabled"] = bool(config["enabled"])
        if "model" in config:
            # Validate model
            valid_models = [m["id"] for m in self.AVAILABLE_MODELS]
            if config["model"] not in valid_models:
                raise ValueError(f"Invalid model: {config['model']}")
            metadata["agent_config"][agent_name]["model"] = config["model"]
        
        metadata["updated_at"] = datetime.now().isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        return self.get_agent_config(project_id)
    
    def add_feedback(
        self,
        project_id: str,
        feedback: str,
        rating: str  # "approved", "needs_work", "rejected"
    ):
        """Add human feedback to a project."""
        project_path = PROJECTS_DIR / project_id
        metadata_path = project_path / "metadata.json"
        
        metadata = json.loads(metadata_path.read_text())
        
        if metadata.get("human_feedback") is None:
            metadata["human_feedback"] = []
        
        metadata["human_feedback"].append({
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "rating": rating
        })
        
        metadata["updated_at"] = datetime.now().isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        # Also update the summary with the new issue
        self.update_summary(project_id)
    
    # =========================================================================
    # BUILD
    # =========================================================================
    
    def trigger_build(self, project_id: str) -> dict:
        """
        Build the project and return the result.
        
        Args:
            project_id: The project's UUID
            
        Returns:
            Dict with success, output, error, and rom_path
        """
        project_path = PROJECTS_DIR / project_id
        
        # Run make
        result = subprocess.run(
            ["make", "rebuild"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0
        
        # Update metadata
        metadata_path = project_path / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["build_attempts"] = metadata.get("build_attempts", 0) + 1
        metadata["updated_at"] = datetime.now().isoformat()
        
        rom_path = None
        if success:
            # Find the ROM
            for rom in (project_path / "build").glob("*.gb"):
                rom_path = str(rom)
                break
            
            metadata["status"] = "compiled"
            metadata["rom_path"] = rom_path
            metadata["error"] = None
        else:
            metadata["status"] = "build_failed"
            metadata["error"] = result.stderr or result.stdout
        
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        # Update summary
        self.update_summary(project_id)
        
        return {
            "success": success,
            "output": result.stdout,
            "error": result.stderr,
            "rom_path": rom_path
        }
    
    # =========================================================================
    # DELETE
    # =========================================================================
    
    def delete_project(self, project_id: str):
        """
        Delete a project and all its files.
        
        Args:
            project_id: The project's UUID
        """
        project_path = PROJECTS_DIR / project_id
        
        if not project_path.exists():
            raise ValueError(f"Project '{project_id}' not found")
        
        # Remove from manifest
        manifest = self._load_manifest()
        manifest["projects"] = [
            p for p in manifest["projects"] if p["id"] != project_id
        ]
        self._save_manifest(manifest)
        
        # Delete directory
        shutil.rmtree(project_path)


# Singleton instance
_api_instance: Optional[ProjectAPI] = None


def get_api() -> ProjectAPI:
    """Get the singleton ProjectAPI instance."""
    global _api_instance
    if _api_instance is None:
        _api_instance = ProjectAPI()
    return _api_instance
