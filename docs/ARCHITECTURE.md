# System Architecture

## Overview

GB-LLM uses a pipeline architecture where natural language flows through several stages to produce a working GameBoy ROM, with human feedback driving iterative improvement.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GB-LLM PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │  Natural │    │  Game    │    │   Code   │    │  Build   │            │
│   │ Language │───▶│  Design  │───▶│Generator │───▶│ Pipeline │            │
│   │  Prompt  │    │  Agent   │    │  Agent   │    │  (GBDK)  │            │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘            │
│                                                         │                   │
│                                                         ▼                   │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │ Feedback │    │  Human   │    │ Emulator │    │   ROM    │            │
│   │  Agent   │◀───│  Tester  │◀───│   Test   │◀───│  Output  │            │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘            │
│        │                                                                    │
│        └────────────────────────────────────────────────────────────────┐  │
│                              ITERATION LOOP                             │  │
└─────────────────────────────────────────────────────────────────────────┴──┘
```

## Components

### 1. Natural Language Interface

**Responsibility:** Accept and parse user game descriptions

**Input Examples:**
- "Create a Pong game with two paddles and a bouncing ball"
- "Make the ball faster when it hits a paddle"
- "Add a score counter at the top of the screen"

**Output:** Structured game requirements for the Design Agent

### 2. Game Design Agent

**Responsibility:** Transform requirements into a game design document

**Capabilities:**
- Analyze game requirements for GB feasibility
- Break down into implementable components
- Define game objects, behaviors, and interactions
- Plan memory layout and resource usage

**Output:** Game Design Document (GDD) in structured format

```yaml
# Example GDD Structure
game:
  name: "Pong"
  type: "arcade"
  
objects:
  - name: "paddle_left"
    type: "sprite"
    width: 8
    height: 24
    behavior: "player_controlled"
    
  - name: "ball"
    type: "sprite"
    width: 8
    height: 8
    behavior: "physics_bounce"
    
mechanics:
  - collision_detection
  - score_tracking
  - win_condition
  
constraints:
  max_sprites: 4
  estimated_rom_size: "32KB"
```

### 3. Code Generator Agent

**Responsibility:** Generate GBDK-compatible C code from design documents

**Capabilities:**
- Select appropriate code templates
- Generate custom game logic
- Create sprite/tile data
- Assemble complete compilable project

**Templates Used:**
- Game loop structure
- Input handling
- Sprite management
- Collision detection
- Score display

**Output:** Complete source files ready for compilation

### 4. Build Pipeline

**Responsibility:** Compile generated code into ROM

**Steps:**
1. Validate source file structure
2. Compile with GBDK-2020 (`lcc`)
3. Capture and parse compiler errors
4. Generate ROM file (`.gb`)
5. Report success or failure with details

**Error Handling:**
- Compilation errors → fed back to Code Generator for fixing
- Warnings → logged but build continues
- Link errors → analyzed for missing dependencies

### 5. Emulator Integration

**Responsibility:** Launch ROM for human testing

**Supported Emulators:**
- **Primary:** BGB (Windows/Wine) - excellent debugging
- **Alternative:** SameBoy (macOS native)
- **Alternative:** mGBA (cross-platform)

**Features:**
- Auto-launch ROM after successful build
- Screenshot capture for feedback
- Debug info extraction (if available)

### 6. Feedback Agent

**Responsibility:** Process human feedback and create improvement tasks

**Input Types:**
- Bug reports: "The ball goes through the paddle"
- Feature requests: "Make the game faster"
- Polish requests: "Add a title screen"

**Output:** Prioritized list of changes for next iteration

## Data Flow

### Initial Game Creation

```
User Prompt
    │
    ▼
┌─────────────────┐
│ Parse & Validate│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate GDD    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Select Templates│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Code   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Compile ROM     │──────▶ Error? ──▶ Fix & Retry
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Launch Emulator │
└────────┬────────┘
         │
         ▼
    Human Tests
```

### Iteration Cycle

```
Human Feedback
    │
    ▼
┌─────────────────┐
│ Parse Feedback  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Identify Changes│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Modify Code     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Recompile       │
└────────┬────────┘
         │
         ▼
    Human Tests
```

## File Organization

### Per-Game Structure

```
games/{game-name}/
├── design/
│   ├── gdd.yaml           # Game design document
│   └── iterations/        # History of changes
│       ├── v1.yaml
│       └── v2.yaml
├── src/
│   ├── main.c             # Entry point
│   ├── game.c             # Game logic
│   ├── game.h
│   ├── sprites.c          # Sprite data
│   ├── sprites.h
│   ├── input.c            # Input handling
│   ├── input.h
│   └── graphics.c         # Tile/background data
├── assets/
│   ├── sprites/           # Source sprite images
│   └── tiles/             # Source tile images
├── build/
│   ├── {game-name}.gb     # Final ROM
│   └── obj/               # Intermediate files
└── Makefile
```

## State Management

### Session State

Each generation session maintains:
- Current game design document
- Source code state
- Compilation status
- Feedback history
- Iteration count

### Persistence

- Game projects saved to `games/` directory
- Design history preserved for learning
- Successful patterns extracted to templates

## Error Recovery

### Compilation Failures

1. Parse compiler output for specific errors
2. Map error to source location
3. Attempt automatic fix (common patterns)
4. If auto-fix fails, report to user with context

### Runtime Issues (from human feedback)

1. Categorize issue type (collision, rendering, logic)
2. Generate hypothesis for cause
3. Propose code changes
4. Apply and rebuild

## Extension Points

### Adding New Game Types

1. Create game type template in `src/templates/`
2. Document required components
3. Add to game type registry
4. Test with sample prompts

### Adding New Features

1. Implement feature module
2. Add template snippets
3. Update GDD schema if needed
4. Document integration points
