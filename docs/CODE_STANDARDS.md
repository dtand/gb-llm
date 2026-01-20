# GameBoy Code Standards

> Strict guidelines for all generated code to ensure high-quality training data.

## Purpose

Every game in this repository serves as training data for a fine-tuned GameBoy programming model. Code must be:
- **Consistent** - Same patterns across all games
- **Documented** - Clear comments explaining intent
- **Annotated** - Metadata linking prompts to code
- **Idiomatic** - Best practices for GB development
- **Complete** - No partial implementations or TODOs

---

## File Structure (Mandatory)

Every game MUST follow this exact structure:

```
games/{game-name}/
├── README.md           # Game description + prompt that generated it
├── Makefile            # Standard build file
├── metadata.json       # Training metadata
└── src/
    ├── main.c          # Entry point only
    ├── game.h          # Game state + constants
    ├── game.c          # Core game logic
    ├── sprites.h       # Sprite declarations
    ├── sprites.c       # Sprite tile data
    ├── input.h         # (optional) Complex input handling
    ├── input.c         # (optional)
    ├── sound.h         # (optional) Sound routines
    └── sound.c         # (optional)
```

---

## Naming Conventions

### Files
- All lowercase
- Underscore for multi-word: `player_ship.c`
- No abbreviations unless standard: `bkg` (background), `spr` (sprite)

### Functions
```c
// snake_case for all functions
void update_player(void);
void check_collision(void);
void render_game(void);

// Prefix with module name for non-static functions
void game_init(void);
void game_update(void);
void sprites_init(void);
void sound_play_beep(void);
```

### Variables
```c
// snake_case for variables
uint8_t player_x;
uint8_t ball_velocity;

// UPPER_SNAKE_CASE for constants/defines
#define PLAYER_SPEED    2
#define MAX_ENEMIES     8
#define SCREEN_WIDTH    160
```

### Types
```c
// PascalCase for structs/typedefs
typedef struct {
    uint8_t x;
    uint8_t y;
} Position;

typedef struct {
    uint8_t score;
    uint8_t lives;
} GameState;
```

---

## Code Style

### Braces
```c
// Opening brace on same line
void update_game(void) {
    if (condition) {
        // code
    } else {
        // code
    }
}
```

### Indentation
- 4 spaces (no tabs)
- Consistent throughout

### Line Length
- Maximum 80 characters
- Break long lines logically

### Includes Order
```c
// 1. System headers
#include <gb/gb.h>
#include <stdint.h>

// 2. Project headers (alphabetical)
#include "game.h"
#include "sprites.h"
```

---

## Documentation Requirements

### File Headers (Mandatory)
Every `.c` and `.h` file MUST start with:

```c
/**
 * @file    game.c
 * @brief   Core game logic for Pong
 * @game    pong
 * 
 * Handles ball movement, paddle control, collision detection,
 * and score tracking.
 */
```

### Function Documentation (Mandatory)
Every function MUST have a doc comment:

```c
/**
 * @brief   Update the ball position and handle collisions
 * 
 * Moves the ball by its velocity, bounces off walls and paddles,
 * and triggers scoring when ball passes a paddle.
 */
void update_ball(void) {
    // implementation
}
```

### Inline Comments
```c
// Explain WHY, not WHAT
// BAD:  Increment x
// GOOD: Move right by speed (capped at screen edge)

player_x += PLAYER_SPEED;
if (player_x > SCREEN_RIGHT) {
    player_x = SCREEN_RIGHT;  // Clamp to screen boundary
}
```

### Section Markers
Use clear section markers in longer files:

```c
// ============================================================
// INITIALIZATION
// ============================================================

void game_init(void) { ... }
void sprites_init(void) { ... }

// ============================================================
// UPDATE LOGIC
// ============================================================

void update_player(void) { ... }
void update_enemies(void) { ... }

// ============================================================
// RENDERING
// ============================================================

void render_game(void) { ... }
```

---

## Type Requirements

### Always Use Fixed-Width Types
```c
// REQUIRED - use stdint types
uint8_t  player_x;      // 0 to 255
int8_t   velocity;      // -128 to 127
uint16_t score;         // 0 to 65535

// FORBIDDEN - never use these
int x;                  // ambiguous size
unsigned char y;        // use uint8_t instead
```

### Prefer Smallest Type
```c
// Use uint8_t when possible (fastest on GB)
uint8_t sprite_count;   // Good: max 40 sprites anyway
uint16_t sprite_count;  // Bad: wastes memory and cycles
```

---

## GameBoy-Specific Rules

### Memory Efficiency
```c
// REQUIRED: Use 'const' for ROM data
const uint8_t sprite_tiles[] = { ... };

// REQUIRED: Use HRAM for frequently accessed variables
// (document with comment)
__at(0xFF80) uint8_t frame_counter;  // HRAM: fast access
```

### Avoid Expensive Operations
```c
// FORBIDDEN: Division and modulo (very slow)
x = value / 3;
y = value % 4;

// REQUIRED: Use bit shifts and masks
x = value >> 2;         // Divide by 4
y = value & 0x03;       // Modulo 4 (power of 2 only)
```

### Sprite Limits
```c
// REQUIRED: Comment sprite allocation
// Sprites used: 0=ball, 1-3=paddle_left, 4-6=paddle_right
// Total: 7 sprites (max 40, max 10 per scanline)

#define SPRITE_BALL     0
#define SPRITE_PADDLE_L 1   // Uses 1, 2, 3
#define SPRITE_PADDLE_R 4   // Uses 4, 5, 6
```

---

## Metadata Requirements

### metadata.json (Mandatory)
Every game MUST have a `metadata.json`:

```json
{
    "name": "pong",
    "version": "1.0.0",
    "prompt": "Create a Pong game with two paddles, a bouncing ball, and simple AI opponent",
    "description": "Classic Pong arcade game",
    "complexity": 2,
    "features": [
        "sprites",
        "collision_detection", 
        "simple_ai",
        "sound_effects",
        "game_state_machine"
    ],
    "controls": {
        "dpad_up": "Move paddle up",
        "dpad_down": "Move paddle down",
        "start": "Pause/unpause"
    },
    "sprites_used": 7,
    "rom_size_kb": 32,
    "files": [
        "src/main.c",
        "src/game.h",
        "src/game.c",
        "src/sprites.h",
        "src/sprites.c"
    ],
    "techniques": [
        "AABB collision",
        "Fixed-point velocity",
        "Frame-based AI throttling"
    ]
}
```

### README.md (Mandatory)
Every game MUST have a README:

```markdown
# Game Name

> One-line description

## Prompt

The exact prompt that should generate this game:

\`\`\`
Create a [game description]
\`\`\`

## How to Play

- Control descriptions

## Technical Notes

- Implementation details useful for training

## Screenshots

(optional but helpful)
```

---

## Anti-Patterns (Forbidden)

### Never Do These

```c
// FORBIDDEN: Magic numbers
if (x > 160) { ... }

// REQUIRED: Named constants
#define SCREEN_WIDTH 160
if (x > SCREEN_WIDTH) { ... }
```

```c
// FORBIDDEN: Unclear variable names
uint8_t a, b, c;

// REQUIRED: Descriptive names
uint8_t ball_x, ball_y, ball_speed;
```

```c
// FORBIDDEN: Complex expressions
if (x + w > px && x < px + pw && y + h > py && y < py + ph) { ... }

// REQUIRED: Extract to function with clear name
if (check_rectangle_collision(x, y, w, h, px, py, pw, ph)) { ... }
```

```c
// FORBIDDEN: Incomplete code
void update_enemies(void) {
    // TODO: implement later
}

// REQUIRED: Complete implementations only
```

```c
// FORBIDDEN: Platform-specific hacks without documentation
*((uint8_t*)0xFF80) = value;

// REQUIRED: Documented with purpose
// Write to HRAM for fast interrupt access
*((uint8_t*)0xFF80) = value;
```

---

## Pre-Commit Checklist

Before adding any game, verify:

- [ ] All files follow naming conventions
- [ ] All functions have doc comments
- [ ] All constants are defined (no magic numbers)
- [ ] Fixed-width types used throughout
- [ ] `metadata.json` is complete and accurate
- [ ] `README.md` includes prompt and description
- [ ] Code compiles without warnings
- [ ] Game runs correctly in emulator
- [ ] No TODOs or incomplete implementations

---

## Training Data Quality Goals

Each game should demonstrate:

1. **One clear concept** - Don't mix too many new ideas
2. **Progressive complexity** - Simple games first, build up
3. **Reusable patterns** - Same collision code style, same game loop
4. **Clean boundaries** - Clear separation between modules
5. **Reproducibility** - Same prompt should yield similar code

This consistency allows the model to learn:
- "When user asks for collision, use this pattern"
- "When user asks for sprites, structure like this"
- "When user asks for AI, implement this way"
