# GameBoy Developer Agent Instructions

> Essential rules for generating GBDK-2020 GameBoy code.

## Output Format

Output ONLY a JSON code block. No explanatory text before or after.

```json
{
  "files": {
    "src/enemies.h": "... complete file contents ...",
    "src/enemies.c": "... complete file contents ..."
  },
  "changes_made": ["Created enemies.h with Enemy struct"],
  "features_implemented": ["enemy_system"]
}
```

**Critical:**
- Output COMPLETE file contents for any file you modify or create
- PRESERVE existing code that isn't related to the change
- No partial implementations or TODOs

---

## File Organization

Do NOT put all code in game.c. Create SEPARATE FILES for each system:

| File | Purpose |
|------|---------|
| `main.c` | Entry point only |
| `game.h/c` | Core game state, main loop, initialization |
| `sprites.h/c` | Sprite tile data and declarations |
| `enemies.h/c` | Enemy system (spawning, movement, types) |
| `player.h/c` | Player stats, inventory, movement |
| `ui.h/c` | HUD, menus, text display |
| `items.h/c` | Item system, pickups |

**Each .c file should be under 300 lines.**

### New File Template

```c
// enemies.h
#ifndef ENEMIES_H
#define ENEMIES_H

#include <gb/gb.h>
#include "game.h"

// Constants with @tunable annotations
// @tunable difficulty range:1-10 Maximum enemies on screen
#define MAX_ENEMIES 8

typedef struct {
    int16_t x, y;
    uint8_t type;
    uint8_t active;
} Enemy;

void enemies_init(void);
void enemies_update(void);
void enemies_render(void);

#endif
```

```c
// enemies.c
#include "enemies.h"

Enemy enemies[MAX_ENEMIES];

void enemies_init(void) {
    for (uint8_t i = 0; i < MAX_ENEMIES; i++) {
        enemies[i].active = 0;
    }
}
```

### Integration

When adding a new module to game.c:
1. Add `#include "module.h"` at top
2. Call `module_init()` in `game_init()`
3. Call `module_update()` in `game_update()`
4. Call `module_render()` in `game_render()`

---

## GBDK-2020 Constraints

### Memory & Types
- No floating point - integers only
- No malloc - static arrays only
- 8KB WRAM limit
- Use `uint8_t`/`int8_t` for most variables
- Use `int16_t` for positions that may exceed 127
- Use `const` for ROM data

### Sprites
- 40 sprites max (8x8 or 8x16)
- Max 10 sprites per scanline
- Sprites need +8 X offset, +16 Y offset
- VRAM writes only during VBlank

### Performance
- Avoid division/modulo (use bit shifts: `>> 2` for /4, `& 0x03` for %4)
- Keep functions small
- Minimize function calls in tight loops

---

## Tunable Parameters (@tunable)

ALL gameplay-affecting constants MUST have `@tunable` annotations for UI adjustment.

### Syntax

```c
// @tunable category range:MIN-MAX Description
#define CONSTANT_NAME value
```

### Categories

| Category | Examples |
|----------|----------|
| `player` | Movement speed, jump strength, lives, health |
| `physics` | Gravity, friction, acceleration, bounce |
| `difficulty` | Enemy count, spawn rates, obstacle counts |
| `timing` | Animation delays, cooldowns, invincibility frames |
| `scoring` | Points per action, bonuses, multipliers |
| `enemies` | Patrol range, attack speed, damage |

### Examples

```c
// @tunable player range:1-8 Movement speed in pixels per frame
#define PLAYER_SPEED 2

// @tunable physics range:0-4 Gravity acceleration per frame
#define GRAVITY 1

// @tunable difficulty range:1-10 Maximum enemies on screen
#define MAX_ENEMIES 5

// @tunable timing range:30-180 Frames between enemy spawns
#define SPAWN_RATE 60

// @tunable scoring range:10-100 Points for defeating an enemy
#define ENEMY_POINTS 25
```

### Always Mark as Tunable
- Movement speeds (player, enemies, projectiles)
- Physics values (gravity, friction, bounce)
- Spawn rates and intervals
- Lives, health, damage values
- Point values and scoring
- Timing delays and cooldowns

### Range Guidelines
- `uint8_t`: range:0-255
- `int8_t`: range:-128-127
- Speeds: typically range:1-8
- Timing: 60 frames = 1 second

---

## Config Tables (@config)

For arrays of structured data (enemy types, items, levels), use `@config` annotations. Schema defined in code, data stored in JSON files.

### When to Use

| Use Case | Solution |
|----------|----------|
| Single global value (gravity, speed) | `@tunable` |
| Multiple instances with same structure | `@config` |
| "How the game feels" | `@tunable` |
| "What exists in the game" | `@config` |

### Syntax (in header file)

```c
// @config table:enemy_types description:"Enemy type definitions"
// @field id uint8 auto description:"Unique identifier"
// @field name string length:12 description:"Display name"
// @field hp uint8 min:1 max:255 default:10 description:"Hit points"
// @field speed uint8 min:1 max:8 default:2 description:"Movement speed"
// @field element enum values:["none","fire","water","earth"] default:"none"
// @field damage uint8 min:1 max:50 default:5 description:"Attack damage"
typedef struct {
    uint8_t id;
    char name[12];
    uint8_t hp;
    uint8_t speed;
    uint8_t element;
    uint8_t damage;
} EnemyType;

// Data loaded from data/enemy_types.json
extern const EnemyType enemy_types[];
extern const uint8_t ENEMY_TYPE_COUNT;
```

### Field Types

| Type | C Type | Required Attributes |
|------|--------|---------------------|
| `uint8`, `int8`, `uint16`, `int16` | numeric | `min`, `max` (optional) |
| `string` | `char[N]` | `length` (required) |
| `enum` | `uint8_t` | `values:["a","b","c"]` (required) |
| `bool` | `uint8_t` | — |
| `ref` | `uint8_t` | `target:table_name` (required) |

### Field Attributes
- `auto` - auto-increment ID
- `min:N`, `max:N` - numeric range
- `length:N` - string max length
- `values:["a","b"]` - enum options
- `default:X` - default value
- `required` - cannot be null
- `nullable` - ref can be 0/null
- `description:"text"` - shown in UI

### Use @config For
- Enemy/monster types and stats
- Item definitions (weapons, potions)
- Level/stage configurations
- Character stats and abilities
- Dialogue or text entries

---

## Naming Conventions

### Functions
```c
// snake_case, prefixed with module name
void game_init(void);
void enemies_update(void);
void player_move(int8_t dx, int8_t dy);
```

### Variables
```c
uint8_t player_x;           // snake_case
uint8_t ball_velocity;
```

### Constants
```c
#define PLAYER_SPEED 2      // UPPER_SNAKE_CASE
#define MAX_ENEMIES 8
```

### Types
```c
typedef struct {            // PascalCase
    uint8_t x, y;
} Position;
```

---

## Documentation (REQUIRED)

### File Headers (Mandatory)
Every `.c` and `.h` file MUST start with:
```c
/**
 * @file    enemies.c
 * @brief   Enemy spawning and behavior
 */
```

### Function Comments (Mandatory)
Every function MUST have a Doxygen-style doc comment:
```c
/**
 * @brief   Spawn a new enemy at random position
 * 
 * Finds an inactive slot and initializes a new enemy
 * at a random valid spawn point.
 */
void spawn_enemy(void) { ... }

/**
 * @brief   Update all active enemies
 * 
 * Moves enemies according to their AI pattern and
 * checks for collision with player.
 */
void enemies_update(void) { ... }
```

### Section Markers (for longer files)
```c
// ============================================================
// INITIALIZATION
// ============================================================

// ============================================================
// UPDATE LOGIC  
// ============================================================

// ============================================================
// RENDERING
// ============================================================
```

---

## Anti-Patterns (Forbidden)

```c
// ❌ Magic numbers
if (x > 160) { ... }

// ✅ Named constants
if (x > SCREEN_WIDTH) { ... }
```

```c
// ❌ Unclear names
uint8_t a, b, c;

// ✅ Descriptive names
uint8_t ball_x, ball_y, ball_speed;
```

```c
// ❌ Division (slow)
x = value / 4;

// ✅ Bit shift
x = value >> 2;
```

```c
// ❌ Incomplete code
void update_enemies(void) {
    // TODO: implement
}

// ✅ Complete implementations only
```

---

## Quick Reference

### Sprite Positioning
```c
// Screen position to sprite position
move_sprite(0, screen_x + 8, screen_y + 16);
```

### Collision Detection
```c
// AABB collision
uint8_t collides(uint8_t x1, uint8_t y1, uint8_t w1, uint8_t h1,
                 uint8_t x2, uint8_t y2, uint8_t w2, uint8_t h2) {
    return (x1 < x2 + w2 && x1 + w1 > x2 &&
            y1 < y2 + h2 && y1 + h1 > y2);
}
```

### Input Handling
```c
uint8_t joy = joypad();
uint8_t pressed = joy & ~joy_prev;  // Just pressed this frame
joy_prev = joy;

if (pressed & J_A) { /* A just pressed */ }
if (joy & J_UP) { /* UP held */ }
```

### VBlank Sync
```c
void game_loop(void) {
    while (1) {
        wait_vbl_done();  // Wait for VBlank before updates
        update_game();
        render_game();
    }
}
```
