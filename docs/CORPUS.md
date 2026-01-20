# Training Corpus Organization

> Guide to the sample organization and taxonomy for the multi-agent system.

## Overview

The corpus is organized for **retrieval-augmented generation** - samples are tagged by the features they demonstrate, allowing the planning agent to find relevant context for any game requirement.

## Directory Structure

```
games/
├── manifest.json       # Master index with full taxonomy
└── samples/           # All code samples
    ├── pong/          # Sample ID = directory name
    ├── snake/
    ├── breakout/
    ├── runner/
    ├── bounce/
    ├── melody/
    └── clicker/
```

## Taxonomy Categories

### Graphics
Visual rendering techniques for the GameBoy's PPU.

| Feature | Description | Samples |
|---------|-------------|---------|
| `sprites` | OAM-based movable objects | pong, snake, breakout, runner, bounce |
| `backgrounds` | Background layer tiles | breakout, runner, clicker |
| `tiles` | Tile data and manipulation | breakout, runner, clicker |
| `animation` | Frame-based sprite animation | bounce |
| `scrolling` | Hardware scroll registers | runner |
| `palettes` | Color palette manipulation | (none yet) |

### Input
Controller handling patterns.

| Feature | Description | Samples |
|---------|-------------|---------|
| `dpad` | Directional pad movement | pong, snake, melody |
| `buttons` | A/B/Start/Select handling | runner, bounce, melody, clicker |
| `combos` | Multi-button combinations | (none yet) |
| `held_vs_pressed` | Edge detection vs continuous | all |

### Physics
Movement and collision systems.

| Feature | Description | Samples |
|---------|-------------|---------|
| `velocity` | Position += velocity patterns | pong, bounce, runner |
| `gravity` | Accumulating downward force | runner, bounce |
| `collision_aabb` | Axis-aligned bounding box | pong, breakout, runner |
| `collision_tile` | Tile map collision | snake, breakout |
| `bounce` | Energy-preserving reflection | bounce |

### Audio
Sound hardware usage.

| Feature | Description | Samples |
|---------|-------------|---------|
| `sfx` | Sound effects | (none yet) |
| `music` | Note sequences | melody |
| `channels` | Channel 1/2/3/4 usage | melody |
| `envelopes` | Volume envelopes | melody |

### Data
State management and persistence.

| Feature | Description | Samples |
|---------|-------------|---------|
| `game_state` | State tracking (score, lives) | pong, snake, clicker |
| `save_sram` | Battery-backed saves | clicker |
| `highscores` | Persistent high scores | clicker |
| `rng` | Random number generation | snake |

### Systems
Architectural patterns.

| Feature | Description | Samples |
|---------|-------------|---------|
| `game_loop` | Main loop structure | all |
| `state_machine` | Game state transitions | (none yet) |
| `entity_system` | Entity management | (none yet) |
| `ai` | Computer-controlled entities | pong |

### Memory
Memory management techniques.

| Feature | Description | Samples |
|---------|-------------|---------|
| `banking` | ROM/RAM bank switching | (none yet) |
| `vram` | Video RAM management | (none yet) |
| `oam` | OAM DMA and management | (none yet) |
| `buffers` | Circular/ring buffers | snake |

## Sample Metadata Schema

Each sample in `manifest.json` includes:

```json
{
    "id": "sample_id",           // Unique identifier, matches directory
    "name": "Human Name",        // Display name
    "path": "samples/sample_id", // Relative path
    "description": "...",        // One-line description
    "complexity": 1-5,           // Difficulty rating
    "status": "tested",          // tested | untested | broken
    "features": {
        "primary": [...],        // Main features demonstrated
        "secondary": [...]       // Supporting features used
    },
    "teaches": [                 // What a model learns from this
        "Concept 1",
        "Concept 2"
    ]
}
```

## Feature Index

The `feature_index` in manifest.json provides reverse lookup:

```json
{
    "gravity": ["runner", "bounce"],
    "scrolling": ["runner"],
    "save_sram": ["clicker"]
}
```

This enables queries like "find all samples that demonstrate gravity" for the planning agent.

## Adding New Samples

1. Create directory: `games/samples/{id}/`
2. Follow [CODE_STANDARDS.md](CODE_STANDARDS.md) for file structure
3. Add entry to `manifest.json` samples array
4. Update `feature_index` for each feature used
5. Test: `cd games/samples/{id} && make && make run`
6. Set status to "tested" after verification

## Missing Coverage

Features not yet covered by any sample:

- `banking` - ROM/RAM bank switching for large games
- `metasprites` - Multi-tile sprite compositions
- `parallax_scrolling` - Multi-layer scrolling effects
- `vertical_scrolling` - SCY-based scrolling
- `window_layer` - Window overlay usage
- `dma_transfer` - OAM DMA routines
- `interrupt_handlers` - VBlank/Timer/Serial interrupts
- `timer` - Hardware timer usage
- `serial_link` - Link cable communication
- `color_palettes_gbc` - Game Boy Color palettes

## Usage by Planning Agent

The planning agent should:

1. Parse user's game description for required features
2. Query `feature_index` to find relevant samples
3. Read sample code to extract implementation patterns
4. Create ordered plan referencing specific code sections
5. Pass plan + context to coding agent

Example query flow:
```
User: "platformer with jump and coins"
→ Features needed: sprites, gravity, collision_tile, animation
→ Samples: runner (gravity, sprites), bounce (gravity), breakout (collision_tile)
→ Extract: jump physics from runner, tile collision from breakout
```
