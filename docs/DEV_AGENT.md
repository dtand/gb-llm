# GameBoy Developer Agent Instructions

> Essential rules for generating GBDK-2020 GameBoy code.

---

## ⚠️ CRITICAL: Code Preservation Rules

**YOU MUST PRESERVE ALL EXISTING FUNCTIONALITY** unless explicitly told to remove it.

When modifying files:
1. **Keep all existing functions** - Don't delete functions that aren't mentioned in the task
2. **Keep all existing variables/structs** - Don't remove state that other code depends on
3. **Keep all existing includes** - Other modules may depend on them
4. **Add, don't replace** - New features should ADD to existing code, not REPLACE it
5. **Surgical changes only** - Modify only the specific code needed for the task

### What "modify this feature" means:
- ✅ Change the specific behavior mentioned
- ✅ Add new code to implement the change
- ❌ Delete unrelated functions
- ❌ Remove existing features not mentioned
- ❌ Rewrite the entire file "for cleanliness"

### Example:
Task: "Make the barrier taller"
- ✅ Change the barrier height constant or loop bounds
- ✅ Adjust barrier drawing code
- ❌ Remove player rendering code
- ❌ Delete enemy spawn logic
- ❌ Remove existing sprites

---

## @config Data Tables (UI-Editable Data)

When creating **data tables** that users should be able to edit via the UI (units, enemies, items, levels, etc.), use `@config` annotations instead of hardcoding data.

### How @config Works:
1. You define the **schema** (struct + annotations) in a `.h` file
2. The build system generates `build/data.c` from `data/*.json`
3. Users can edit values in the UI without regenerating code

### Rules for @config Tables:

**DO:**
- ✅ Create `.h` file with struct and `@config`/`@field` annotations
- ✅ Declare `get_tablename()` accessor function prototype
- ✅ Add helper functions in `.c` file (validation, utilities)

**DO NOT:**
- ❌ Create hardcoded data arrays in `.c` files for @config tables
- ❌ Define `get_tablename()` function body (it's auto-generated)
- ❌ Use `extern` for the data array (it comes from build/data.c)

### @config Example:

```c
// units.h - SCHEMA ONLY, no hardcoded data
#ifndef UNITS_H
#define UNITS_H

#include <gb/gb.h>

#define UNIT_COUNT 10
#define UNIT_NAME_MAX_LENGTH 16

// @config table:unit_data description:"Unit type definitions"
// @field id uint8 auto description:"Unique unit identifier"
// @field name string length:16 description:"Display name"
// @field hp uint8 min:1 max:255 default:20 description:"Hit points"
// @field atk uint8 min:1 max:255 default:10 description:"Attack power"
typedef struct {
    uint8_t id;
    char name[UNIT_NAME_MAX_LENGTH];
    uint8_t hp;
    uint8_t atk;
} UnitData;

// Accessor - implemented in build/data.c (auto-generated)
const UnitData* get_unit_data(uint8_t id);

// Helper functions - implement these in units.c
uint8_t is_valid_unit_id(uint8_t unit_id);

#endif
```

```c
// units.c - HELPERS ONLY, no data arrays
#include "units.h"

// Note: unit_data[] and get_unit_data() are in build/data.c

uint8_t is_valid_unit_id(uint8_t unit_id) {
    return (unit_id >= 1 && unit_id <= UNIT_COUNT) ? 1 : 0;
}
```

### @field Annotation Reference:

| Attribute | Example | Description |
|-----------|---------|-------------|
| `type` | `uint8`, `string`, `enum` | Field data type |
| `auto` | `@field id uint8 auto` | Auto-increment ID |
| `length:N` | `length:16` | Max string length |
| `min:N` / `max:N` | `min:1 max:255` | Value range |
| `default:N` | `default:10` | Default value |
| `values:[...]` | `values:["normal","boss"]` | Enum options |
| `description:"..."` | `description:"Hit points"` | UI label |

---

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
- PRESERVE ALL existing code that isn't directly related to the change
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

## Sprite Data Definition (STRICT)

Every sprite MUST be defined as its own separate `const uint8_t` array with row-by-row visual comments.

### Required Format

```c
// [Sprite Name] ([dimensions])
// [Brief description of the sprite]
const uint8_t sprite_name[] = {
    0xHH, 0xHH,  // Row 0: [visual] ([description])
    0xHH, 0xHH,  // Row 1: [visual] ([description])
    0xHH, 0xHH,  // Row 2: [visual] ([description])
    0xHH, 0xHH,  // Row 3: [visual] ([description])
    0xHH, 0xHH,  // Row 4: [visual] ([description])
    0xHH, 0xHH,  // Row 5: [visual] ([description])
    0xHH, 0xHH,  // Row 6: [visual] ([description])
    0xHH, 0xHH   // Row 7: [visual] ([description])
};
```

### Visual Comment Legend
- `█` = pixel ON (bit set)
- `.` or ` ` = pixel OFF (bit clear)
- Comments MUST align for readability

### Complete Example

```c
// Mage character sprite (8x8)
// Simple design: pointed hat, robe, staff
const uint8_t sprite_mage[] = {
    0x18, 0x18,  // Row 0:   ██      (hat tip)
    0x3C, 0x3C,  // Row 1:  ████     (hat)
    0x7E, 0x7E,  // Row 2: ██████    (hat brim)
    0x42, 0x7E,  // Row 3: █ ██ █    (face)
    0x42, 0x7E,  // Row 4: █ ██ █    (eyes)
    0x7E, 0x7E,  // Row 5: ██████    (robe top)
    0x66, 0x66,  // Row 6: █ ██ █    (robe)
    0x18, 0x18   // Row 7:   ██      (staff base)
};

// Ground tile pattern (8x8)
// Simple textured ground with grass/dirt pattern
const uint8_t tile_ground[] = {
    0x00, 0x00,  // Row 0: ........  (sky/air above)
    0x00, 0x00,  // Row 1: ........  (sky/air above)
    0x55, 0x55,  // Row 2: █.█.█.█.  (grass blades)
    0xAA, 0xAA,  // Row 3: .█.█.█.█  (grass blades)
    0x3C, 0x3C,  // Row 4:  ████     (dirt layer)
    0x66, 0x66,  // Row 5: █ ██ █    (dirt texture)
    0xFF, 0xFF,  // Row 6: ████████  (solid ground)
    0xFF, 0xFF   // Row 7: ████████  (solid ground)
};
```

### Rules (Mandatory)

| Rule | Requirement |
|------|-------------|
| Separate arrays | Each sprite MUST be its own `const uint8_t` array |
| Naming | Use `sprite_` prefix for sprites, `tile_` prefix for background tiles |
| Visual comments | Every row MUST have a comment showing the visual pattern |
| Row labels | Comments MUST include `Row N:` for each line |
| Descriptions | Optional but recommended: describe what each row represents |
| Alignment | Visual patterns MUST be aligned across all rows |
| No inline data | NEVER define sprite data inline in function calls |

### Forbidden Patterns

```c
// ❌ No visual comments
const uint8_t sprite_bad[] = {
    0x18, 0x18, 0x3C, 0x3C, 0x7E, 0x7E, 0x42, 0x7E,
    0x42, 0x7E, 0x7E, 0x7E, 0x66, 0x66, 0x18, 0x18
};

// ❌ Inline data in function call
set_sprite_data(0, 1, (uint8_t[]){0x18, 0x18, 0x3C, 0x3C, ...});

// ❌ Combined sprites in single array
const uint8_t all_sprites[] = { /* multiple sprites */ };
```

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

## Build Error Troubleshooting

When your code fails to compile, carefully read the error messages and apply these fixes:

### Common SDCC/GBDK Errors

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `undefined identifier 'X'` | Variable/function not declared | Add `#include` for the header that declares it, or add declaration |
| `syntax error` | Missing semicolon, brace, or paren | Check the line number and previous line for missing `;` `}` `)` |
| `conflicting types for 'X'` | Function signature in .c doesn't match .h | Make sure parameter types and return type match exactly |
| `expected ';'` or `expected ')'` | Missing token | Add the missing character at the indicated location |
| `lvalue required` | Trying to assign to a constant or expression | Use a variable instead of a literal or expression on left side of `=` |
| `too many arguments` | Function called with wrong number of args | Check function declaration for correct parameter count |
| `implicit declaration of function` | Function used before declared | Add `#include` for the header or add forward declaration |

### Linker Errors (ASlink)

Linker errors appear AFTER compilation succeeds. They indicate missing function implementations:

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `Undefined Global '_func_name'` | Function declared but never implemented | Add the function body in a .c file, or remove the call |
| `referenced by module 'X'` | Module X is calling a missing function | Check which file is missing the implementation |

**Example:**
```
?ASlink-Warning-Undefined Global '_get_ai_spell' referenced by module 'game'
```

This means `game.c` calls `get_ai_spell()` but no .c file contains the implementation. Either:
1. Add the function implementation to the appropriate .c file
2. Remove the call if the function isn't needed

### Header/Source Matching

The most common error pattern is mismatched declarations:

```c
// ❌ WRONG - signatures don't match
// game.h
void update_player(uint8_t speed);

// game.c  
void update_player(int16_t speed) { ... }  // Different type!

// ✅ CORRECT - exact match
// game.h
void update_player(uint8_t speed);

// game.c
void update_player(uint8_t speed) { ... }  // Same signature
```

### Include Order Matters

```c
// ❌ WRONG - game.h may depend on gb/gb.h types
#include "game.h"
#include <gb/gb.h>

// ✅ CORRECT - system headers first
#include <gb/gb.h>
#include "game.h"
```

### When Fixing Errors

1. **Read the exact file and line number** in the error message
2. **Fix only what's broken** - don't make unrelated changes
3. **Check both .h and .c files** - they must stay in sync
4. **Verify all includes** are present for types you use

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
