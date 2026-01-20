# Code Generation Strategy

## Overview

This document defines how natural language prompts are transformed into compilable GameBoy code using a template-based generation approach augmented by LLM reasoning.

## Generation Philosophy

### Principle 1: Templates First
Use proven, tested code templates for common patterns. The LLM's role is to:
- Select appropriate templates
- Customize template parameters
- Fill in game-specific logic
- Connect components together

### Principle 2: Compilation is Non-Negotiable
Every iteration must produce code that compiles. If it doesn't compile, it's not done.

### Principle 3: Incremental Complexity
Start with the simplest working version, then iterate based on feedback.

## Prompt Processing Pipeline

### Stage 1: Intent Classification

Determine what the user wants:

| Intent | Example | Action |
|--------|---------|--------|
| New Game | "Create a Pong game" | Full generation pipeline |
| Modify | "Make the ball faster" | Targeted code change |
| Add Feature | "Add a title screen" | Component addition |
| Fix Bug | "Ball goes through paddle" | Debug and repair |
| Explain | "How does scoring work?" | Documentation only |

### Stage 2: Game Analysis

For new games, extract:

```yaml
game_analysis:
  type: "pong"                    # Game category
  objects:                        # Entities in game
    - paddle (2x)
    - ball
    - score_display
  mechanics:                      # Core behaviors
    - paddle_movement
    - ball_physics
    - collision_detection
    - score_tracking
  visual_requirements:            # Display needs
    - sprite_count: 4
    - background: simple
    - text_display: yes
  complexity_score: 2/10          # Feasibility check
```

### Stage 3: Template Selection

Map game requirements to templates:

```
Game Type: Pong
├── Core Template: arcade_game
├── Object Templates:
│   ├── player_paddle → sprite_player_controlled
│   ├── ai_paddle → sprite_ai_simple
│   └── ball → sprite_physics_bounce
├── Mechanic Templates:
│   ├── collision → rect_collision
│   └── scoring → simple_score_display
└── Structure Template: single_screen_game
```

### Stage 4: Code Assembly

1. Generate project structure from template
2. Customize main game file
3. Generate sprite/tile data
4. Wire up game logic
5. Add game-specific code

## Template System

### Template Types

#### 1. Structure Templates
Define overall game architecture:

```
single_screen_game/
├── main.c          # Init, game loop
├── game.h          # Game state structure
├── game.c          # Core game logic
├── sprites.h       # Sprite declarations
├── sprites.c       # Sprite data
└── Makefile        # Build configuration
```

#### 2. Object Templates
Define game entities:

```c
// Template: sprite_player_controlled
// Parameters: SPRITE_ID, TILE_ID, SPEED, BOUNDS

void update_{{name}}(void) {
    // Read input
    UINT8 joy = joypad();
    
    // Movement
    if (joy & J_UP && {{name}}_y > {{min_y}}) {
        {{name}}_y -= {{speed}};
    }
    if (joy & J_DOWN && {{name}}_y < {{max_y}}) {
        {{name}}_y += {{speed}};
    }
    
    // Update sprite position
    move_sprite({{sprite_id}}, {{name}}_x, {{name}}_y);
}
```

#### 3. Mechanic Templates
Define behaviors:

```c
// Template: rect_collision
// Parameters: obj1, obj2, widths, heights

UINT8 check_collision_{{obj1}}_{{obj2}}(void) {
    if ({{obj1}}_x < {{obj2}}_x + {{obj2_width}} &&
        {{obj1}}_x + {{obj1_width}} > {{obj2}}_x &&
        {{obj1}}_y < {{obj2}}_y + {{obj2_height}} &&
        {{obj1}}_y + {{obj1_height}} > {{obj2}}_y) {
        return 1;
    }
    return 0;
}
```

#### 4. Asset Templates
Sprite and tile data:

```c
// Template: sprite_8x8_simple
// Generated from description or default patterns

const UINT8 {{name}}_tiles[] = {
    0x3C, 0x3C,  // Row 0:   ####
    0x7E, 0x7E,  // Row 1:  ######
    0xFF, 0xFF,  // Row 2: ########
    0xFF, 0xFF,  // Row 3: ########
    0xFF, 0xFF,  // Row 4: ########
    0xFF, 0xFF,  // Row 5: ########
    0x7E, 0x7E,  // Row 6:  ######
    0x3C, 0x3C   // Row 7:   ####
};
```

## Generation Examples

### Example 1: New Pong Game

**Prompt:** "Create a simple Pong game"

**Analysis:**
```yaml
type: pong
objects: [left_paddle, right_paddle, ball]
mechanics: [paddle_input, ball_bounce, scoring]
```

**Generated Files:**

`main.c`:
```c
#include <gb/gb.h>
#include "game.h"
#include "sprites.h"

void main(void) {
    // Initialize
    init_game();
    load_sprites();
    
    // Main loop
    while(1) {
        wait_vbl_done();
        update_game();
        render_game();
    }
}
```

`game.c`:
```c
#include <gb/gb.h>
#include "game.h"

// Game state
GameState game;

// Constants
#define PADDLE_SPEED 2
#define BALL_SPEED 1
#define PADDLE_HEIGHT 24
#define BALL_SIZE 8

void init_game(void) {
    // Initialize positions
    game.paddle_left_y = 72;   // Center
    game.paddle_right_y = 72;
    game.ball_x = 80;
    game.ball_y = 72;
    game.ball_dx = BALL_SPEED;
    game.ball_dy = BALL_SPEED;
    game.score_left = 0;
    game.score_right = 0;
}

void update_game(void) {
    update_paddles();
    update_ball();
    check_collisions();
    check_scoring();
}

// ... additional implementation
```

### Example 2: Modification Request

**Prompt:** "Make the ball faster after each paddle hit"

**Analysis:**
- Intent: Modify
- Target: ball_speed / collision_response
- Change type: Incremental value adjustment

**Code Change:**
```c
// Before
void on_paddle_collision(void) {
    game.ball_dx = -game.ball_dx;
}

// After
void on_paddle_collision(void) {
    game.ball_dx = -game.ball_dx;
    
    // Increase speed slightly (max 4)
    if (game.ball_speed < 4) {
        game.ball_speed++;
    }
}
```

## Error Handling

### Compilation Errors

When code fails to compile, the generator:

1. **Parses error message:**
   ```
   game.c:45: error: 'ball_velocity' undeclared
   ```

2. **Identifies cause:**
   - Typo in variable name
   - Missing declaration
   - Type mismatch

3. **Applies fix:**
   ```c
   // Fix: Use correct variable name
   game.ball_dx  // not ball_velocity
   ```

4. **Recompiles and validates**

### Common Error Patterns

| Error Type | Example | Auto-Fix Strategy |
|------------|---------|-------------------|
| Undeclared variable | `'foo' undeclared` | Check game state, add if missing |
| Type mismatch | `incompatible types` | Cast or correct type |
| Missing include | `undefined reference` | Add required #include |
| Syntax error | `expected ';'` | Parse context, add punctuation |

## Feedback Integration

### Processing Human Feedback

**Input:** "The ball moves too fast to see"

**Analysis:**
1. Identify component: ball
2. Identify property: speed/movement
3. Identify direction: decrease
4. Locate relevant code: `BALL_SPEED` constant, `update_ball()`

**Response Options:**
1. Reduce `BALL_SPEED` constant
2. Add frame-based movement limiting
3. Implement ball trail effect for visibility

**Applied Change:**
```c
// Reduce initial ball speed
#define BALL_SPEED 1  // Was 2

// Optionally add speed cap
#define MAX_BALL_SPEED 3
```

### Feedback Categories

| Category | Example | Typical Fix |
|----------|---------|-------------|
| Too fast/slow | "Ball too fast" | Adjust speed constants |
| Not working | "Can't move paddle" | Check input handling |
| Missing feature | "No score display" | Add component |
| Visual issue | "Sprite flickers" | Optimize sprite usage |
| Game balance | "AI too easy" | Adjust AI parameters |

## Quality Assurance

### Pre-Compilation Checks

Before attempting compilation:
- [ ] All variables declared
- [ ] All functions have prototypes
- [ ] Includes are complete
- [ ] Sprite data is valid (16 bytes per 8x8 tile)
- [ ] No obvious infinite loops

### Post-Compilation Checks

After successful compilation:
- [ ] ROM size within limits
- [ ] No linker warnings
- [ ] Entry point exists

### Runtime Expectations

Document expected behavior for human tester:
- What controls should work
- What should appear on screen
- Expected game flow
- Known limitations

## Iteration Protocol

### Standard Iteration Cycle

1. **Generate/Modify** code based on prompt
2. **Compile** and fix any errors
3. **Launch** in emulator
4. **Report** to human what to test
5. **Receive** feedback
6. **Analyze** feedback for changes
7. **Return to step 1**

### When to Stop Iterating

- Human indicates satisfaction
- Feature is working as specified
- Bug is confirmed fixed
- Request is out of scope (document why)
