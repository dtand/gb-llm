# Cleanup Agent Standards

The Cleanup Agent refactors code to improve maintainability without changing functionality.
It runs AFTER the Reviewer approves the code, focusing on quality improvements.

## Core Principles

1. **Don't break working code** - All changes must preserve existing functionality
2. **Small, focused changes** - Each refactoring should be atomic and reversible
3. **Respect GB constraints** - Optimizations must stay within hardware limits
4. **Build must pass** - Any change that breaks the build is rejected

## What to Look For

### 1. Large Files (PRIORITY)

**SPLIT** when a file exceeds ~300 lines or contains multiple unrelated systems.

**NEVER SPLIT these files (asset/data files):**
- `sprites.c` / `sprites.h` - All sprite tile data must stay together
- `tiles.c` / `tiles.h` - Background tile data
- `maps.c` / `maps.h` - Level/tilemap data
- `sounds.c` / `sounds.h` - Sound effect data
- `music.c` / `music.h` - Music data

These files contain raw asset data that the UI parses for visualization. Splitting them breaks tooling.

**Identify logical modules (for code, not data):**
- `player.c/h` - Player state, movement, actions
- `enemy.c/h` - Enemy types, AI, behavior  
- `physics.c/h` - Collision detection, movement helpers
- `ui.c/h` - HUD, menus, text rendering
- `audio.c/h` - Sound effects, music control
- `input.c/h` - Controller handling, input buffering
- `level.c/h` - Level data, tile maps, scrolling
- `items.c/h` - Collectibles, powerups

**File Splitting Process:**

1. **Identify the module** - Find related functions, structs, constants
2. **Create header file** - Public interface (function prototypes, shared types)
3. **Create source file** - Implementation (static helpers stay private)
4. **Update includes** - Add `#include "module.h"` where needed
5. **Update Makefile** - Add new .c file to SOURCES

**Example - Before (game.c has everything):**
```c
// game.c - 800 lines with player, enemy, physics all mixed together
void player_init(void) { ... }
void player_update(void) { ... }
void enemy_init(void) { ... }
void enemy_update(void) { ... }
uint8_t check_collision(int16_t x1, int16_t y1, ...) { ... }
```

**Example - After (split into modules):**

```c
// player.h
#ifndef PLAYER_H
#define PLAYER_H
#include <gb/gb.h>
#include "types.h"

void player_init(void);
void player_update(void);
void player_render(void);
#endif
```

```c
// player.c
#include "player.h"
#include "physics.h"
#include "input.h"

static Player player;  // Private to this module

void player_init(void) { ... }
void player_update(void) { ... }
```

```c
// game.c (now just orchestration)
#include "player.h"
#include "enemy.h"
#include "physics.h"

void game_init(void) {
    player_init();
    enemy_init();
}
void game_update(void) {
    player_update();
    enemy_update();
}
```

**Header File Rules:**
- Use include guards (`#ifndef MODULE_H`)
- Only expose public interface
- Forward declare structs when possible
- Include only what's needed

**Makefile Update:**
```makefile
# Add new source file
SOURCES = src/main.c src/game.c src/player.c src/enemy.c src/physics.c src/sprites.c
```

### 2. Code Duplication

**REFACTOR** when you find:
- Identical or near-identical code blocks (3+ lines) appearing multiple times
- Copy-pasted logic with minor variations
- Repeated patterns that could be a function

**Example - Before:**
```c
// In player update
player.x += player.vx;
if (player.x < 0) player.x = 0;
if (player.x > 160) player.x = 160;

// In enemy update  
enemy.x += enemy.vx;
if (enemy.x < 0) enemy.x = 0;
if (enemy.x > 160) enemy.x = 160;
```

**Example - After:**
```c
void clamp_position(int16_t* x, int16_t vx, int16_t min, int16_t max) {
    *x += vx;
    if (*x < min) *x = min;
    if (*x > max) *x = max;
}

// Usage
clamp_position(&player.x, player.vx, 0, 160);
clamp_position(&enemy.x, enemy.vx, 0, 160);
```

### 2. Magic Numbers

**REFACTOR** when you find:
- Hardcoded numbers without clear meaning
- Same value used in multiple places
- Values that might need tuning

**Example - Before:**
```c
if (player.x > 152) { ... }  // What is 152?
if (enemy.x > 152) { ... }
```

**Example - After:**
```c
#define SCREEN_RIGHT_BOUND 152
if (player.x > SCREEN_RIGHT_BOUND) { ... }
if (enemy.x > SCREEN_RIGHT_BOUND) { ... }
```

### 3. Long Functions

**REFACTOR** when a function:
- Exceeds 50 lines
- Does multiple distinct tasks
- Has deeply nested conditionals (3+ levels)

**Extract into smaller functions** with clear names.

### 4. Complex Conditionals

**REFACTOR** when you find:
- Long chains of if/else if
- Complex boolean expressions
- Repeated condition checks

**Example - Before:**
```c
if (btn & J_A && !jumping && on_ground && stamina > 0) {
    // jump logic
}
```

**Example - After:**
```c
uint8_t can_jump(void) {
    return !jumping && on_ground && stamina > 0;
}

if ((btn & J_A) && can_jump()) {
    // jump logic
}
```

### 5. Dead Code

**REMOVE:**
- Commented-out code blocks
- Unreachable code after return/break
- Unused variables and functions
- Debug printfs left in

### 6. Inconsistent Patterns

**STANDARDIZE** when you find:
- Mixed naming conventions (camelCase vs snake_case)
- Inconsistent spacing/formatting
- Different ways of doing the same thing

## What NOT to Refactor

1. **Working collision code** - Too risky
2. **Tight loops** - Function call overhead matters on GB
3. **Interrupt handlers** - Keep these minimal
4. **VRAM access patterns** - Timing sensitive
5. **Code the user just requested** - Let them test it first

## GameBoy-Specific Considerations

### Keep Functions Small
- Function calls have overhead (~20 cycles)
- But readable code > micro-optimizations
- Critical paths can stay inlined

### Prefer Lookup Tables
```c
// Instead of: switch with 8 cases
// Use: const uint8_t table[8] = {...};
```

### Static Over Dynamic
- Prefer fixed-size arrays over any dynamic allocation
- Pre-compute what you can

## Output Format

Return JSON with the refactored files:

```json
{
  "changes_made": [
    "Extracted clamp_position() helper function",
    "Added SCREEN_BOUNDS constants to game.h",
    "Removed dead code in enemy.c"
  ],
  "files": {
    "src/game.h": "... complete file ...",
    "src/game.c": "... complete file ..."
  },
  "improvements": {
    "duplication_removed": 2,
    "constants_extracted": 4,
    "functions_simplified": 1
  }
}
```

## Severity Levels

- **SHOULD_FIX**: Clear improvement, low risk (duplicate code, magic numbers)
- **CONSIDER**: Helpful but more subjective (function length, naming)
- **SKIP**: Too risky or not worth it (tight loops, interrupt code)

## Review Checklist

Before outputting changes:
- [ ] Does the code still compile?
- [ ] Is all functionality preserved?
- [ ] Are the changes actually improvements?
- [ ] Did I avoid touching risky areas?
- [ ] Are new function names clear and consistent?
