# Game Patterns & Templates

> Reusable code patterns for common game elements. These templates form the building blocks for generated games.

## Pattern Index

1. [Project Structure](#project-structure)
2. [Game Loop](#game-loop)
3. [Input Handling](#input-handling)
4. [Sprite Management](#sprite-management)
5. [Collision Detection](#collision-detection)
6. [Score Display](#score-display)
7. [Game States](#game-states)
8. [Simple AI](#simple-ai)
9. [Fixed-Point Math](#fixed-point-math)
10. [Sound Effects](#sound-effects)

---

## Project Structure

### Minimal Game Project

```
game/
├── Makefile
├── src/
│   ├── main.c          # Entry point, game loop
│   ├── game.h          # Game state, constants
│   ├── game.c          # Game logic
│   ├── sprites.h       # Sprite declarations
│   └── sprites.c       # Sprite tile data
└── build/
    └── game.gb         # Output ROM
```

### Standard Makefile

```makefile
# Game Boy ROM Makefile

# Configuration
GBDK_HOME = /opt/gbdk
PROJECT   = game
SOURCES   = src/main.c src/game.c src/sprites.c

# Compiler
LCC = $(GBDK_HOME)/bin/lcc
CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"$(PROJECT)"

# Build
all: build/$(PROJECT).gb

build/$(PROJECT).gb: $(SOURCES)
	@mkdir -p build
	$(LCC) $(CFLAGS) -o $@ $^

clean:
	rm -rf build/ src/*.o src/*.lst src/*.sym

run: build/$(PROJECT).gb
	open -a SameBoy $<

.PHONY: all clean run
```

---

## Game Loop

### Basic Loop Pattern

```c
// main.c
#include <gb/gb.h>
#include "game.h"
#include "sprites.h"

void main(void) {
    // One-time initialization
    init_graphics();
    init_game();
    
    // Enable display features
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        // Wait for vertical blank (sync to 60fps)
        wait_vbl_done();
        
        // Process input
        handle_input();
        
        // Update game state
        update_game();
        
        // Render changes
        render_game();
    }
}
```

### Loop with Delta Time (Advanced)

```c
UINT8 frame_counter = 0;

void main(void) {
    init_game();
    
    while(1) {
        wait_vbl_done();
        frame_counter++;
        
        // Process input every frame
        handle_input();
        
        // Update logic (can skip frames for slower objects)
        update_game();
        
        // Heavy operations every N frames
        if ((frame_counter & 0x03) == 0) {  // Every 4 frames
            update_ai();
        }
        
        render_game();
    }
}
```

---

## Input Handling

### Basic Input Reading

```c
// game.c
#include <gb/gb.h>

// Store previous frame's input for edge detection
UINT8 previous_input = 0;
UINT8 current_input = 0;

void handle_input(void) {
    previous_input = current_input;
    current_input = joypad();
}

// Check if button is currently held
UINT8 button_held(UINT8 button) {
    return current_input & button;
}

// Check if button was just pressed this frame
UINT8 button_pressed(UINT8 button) {
    return (current_input & button) && !(previous_input & button);
}

// Check if button was just released this frame
UINT8 button_released(UINT8 button) {
    return !(current_input & button) && (previous_input & button);
}
```

### Input Constants

```c
// Available button constants (from gb/gb.h)
// J_UP, J_DOWN, J_LEFT, J_RIGHT
// J_A, J_B, J_START, J_SELECT
```

### Movement Example

```c
#define PLAYER_SPEED 2

void update_player(void) {
    if (button_held(J_UP) && player_y > MIN_Y) {
        player_y -= PLAYER_SPEED;
    }
    if (button_held(J_DOWN) && player_y < MAX_Y) {
        player_y += PLAYER_SPEED;
    }
    if (button_held(J_LEFT) && player_x > MIN_X) {
        player_x -= PLAYER_SPEED;
    }
    if (button_held(J_RIGHT) && player_x < MAX_X) {
        player_x += PLAYER_SPEED;
    }
}
```

---

## Sprite Management

### Sprite Data Definition

```c
// sprites.c
#include <gb/gb.h>

// 8x8 sprite tile (16 bytes per tile)
// Each row is 2 bytes: low bits, high bits
const UINT8 ball_tile[] = {
    0x3C, 0x3C,  // ..####..
    0x7E, 0x7E,  // .######.
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0x7E, 0x7E,  // .######.
    0x3C, 0x3C   // ..####..
};

// 8x24 paddle (3 tiles = 48 bytes)
const UINT8 paddle_tiles[] = {
    // Tile 0 (top)
    0x7E, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    // Tile 1 (middle)
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    // Tile 2 (bottom)
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x7E
};
```

### Sprite Loading

```c
// sprites.h
#define TILE_BALL      0
#define TILE_PADDLE    1  // Uses tiles 1, 2, 3

#define SPRITE_BALL    0
#define SPRITE_PADDLE1 1  // Uses sprites 1, 2, 3
#define SPRITE_PADDLE2 4  // Uses sprites 4, 5, 6

void init_sprites(void) {
    // Load tile data into VRAM
    set_sprite_data(TILE_BALL, 1, ball_tile);
    set_sprite_data(TILE_PADDLE, 3, paddle_tiles);
    
    // Assign tiles to sprites
    set_sprite_tile(SPRITE_BALL, TILE_BALL);
    
    // Multi-tile paddle (8x24)
    set_sprite_tile(SPRITE_PADDLE1, TILE_PADDLE);
    set_sprite_tile(SPRITE_PADDLE1 + 1, TILE_PADDLE + 1);
    set_sprite_tile(SPRITE_PADDLE1 + 2, TILE_PADDLE + 2);
}
```

### Sprite Movement

```c
// Move single sprite
void move_ball(UINT8 x, UINT8 y) {
    move_sprite(SPRITE_BALL, x, y);
}

// Move multi-tile sprite (3 tiles vertical)
void move_paddle(UINT8 sprite_base, UINT8 x, UINT8 y) {
    move_sprite(sprite_base, x, y);
    move_sprite(sprite_base + 1, x, y + 8);
    move_sprite(sprite_base + 2, x, y + 16);
}
```

### Sprite Position Notes

```c
// IMPORTANT: Screen coordinates have offsets!
// Sprite X: 8 = left edge of screen
// Sprite Y: 16 = top edge of screen

#define SCREEN_X_OFFSET 8
#define SCREEN_Y_OFFSET 16

// To place sprite at screen position (0,0):
move_sprite(0, SCREEN_X_OFFSET, SCREEN_Y_OFFSET);
```

---

## Collision Detection

### Rectangle Collision (AABB)

```c
// Check if two rectangles overlap
UINT8 check_collision(
    UINT8 x1, UINT8 y1, UINT8 w1, UINT8 h1,
    UINT8 x2, UINT8 y2, UINT8 w2, UINT8 h2
) {
    return (x1 < x2 + w2) &&
           (x1 + w1 > x2) &&
           (y1 < y2 + h2) &&
           (y1 + h1 > y2);
}

// Example usage
if (check_collision(ball_x, ball_y, 8, 8,
                    paddle_x, paddle_y, 8, 24)) {
    // Collision detected!
    on_paddle_hit();
}
```

### Optimized Collision (Common Case)

```c
// When one dimension is fixed (e.g., paddle at edge)
UINT8 check_ball_paddle_collision(void) {
    // Ball approaching left paddle?
    if (ball_dx < 0 && ball_x <= PADDLE_LEFT_X + 8) {
        // Check Y overlap
        if (ball_y + 8 > paddle_left_y &&
            ball_y < paddle_left_y + PADDLE_HEIGHT) {
            return 1;
        }
    }
    return 0;
}
```

---

## Score Display

### Using Background Tiles for Numbers

```c
// Number tiles (0-9) - simple block numbers
const UINT8 number_tiles[] = {
    // 0
    0x3C, 0x3C, 0x66, 0x66, 0x66, 0x66, 0x66, 0x66,
    0x66, 0x66, 0x66, 0x66, 0x3C, 0x3C, 0x00, 0x00,
    // 1
    0x18, 0x18, 0x38, 0x38, 0x18, 0x18, 0x18, 0x18,
    0x18, 0x18, 0x18, 0x18, 0x3C, 0x3C, 0x00, 0x00,
    // ... tiles 2-9
};

#define TILE_NUM_0 10  // Starting tile index for numbers

void init_number_tiles(void) {
    set_bkg_data(TILE_NUM_0, 10, number_tiles);
}

// Display single digit at tile position
void draw_digit(UINT8 x, UINT8 y, UINT8 digit) {
    UINT8 tile = TILE_NUM_0 + digit;
    set_bkg_tile_xy(x, y, tile);
}

// Display two-digit score
void draw_score(UINT8 x, UINT8 y, UINT8 score) {
    draw_digit(x, y, score / 10);      // Tens
    draw_digit(x + 1, y, score % 10);  // Ones
}
```

### Score in Window Layer (Alternative)

```c
void setup_score_window(void) {
    // Position window at top of screen
    move_win(7, 0);  // X=7 is left edge, Y=0 is top
    
    // Load number tiles to window
    set_win_data(0, 10, number_tiles);
    
    SHOW_WIN;
}

void update_score_display(UINT8 left_score, UINT8 right_score) {
    // Draw at window positions
    set_win_tile_xy(2, 0, left_score % 10);
    set_win_tile_xy(16, 0, right_score % 10);
}
```

---

## Game States

### State Machine Pattern

```c
// game.h
typedef enum {
    STATE_TITLE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAME_OVER
} GameState;

// game.c
GameState current_state = STATE_TITLE;

void update_game(void) {
    switch (current_state) {
        case STATE_TITLE:
            update_title();
            break;
        case STATE_PLAYING:
            update_playing();
            break;
        case STATE_PAUSED:
            update_paused();
            break;
        case STATE_GAME_OVER:
            update_game_over();
            break;
    }
}

void update_title(void) {
    if (button_pressed(J_START)) {
        current_state = STATE_PLAYING;
        init_playing();
    }
}

void update_playing(void) {
    if (button_pressed(J_START)) {
        current_state = STATE_PAUSED;
        return;
    }
    
    // Normal game logic...
    update_ball();
    update_paddles();
    check_collisions();
}

void update_paused(void) {
    if (button_pressed(J_START)) {
        current_state = STATE_PLAYING;
    }
}
```

---

## Simple AI

### Basic Following AI

```c
// AI paddle follows ball with some delay
#define AI_SPEED 1
#define AI_REACTION_THRESHOLD 4

void update_ai_paddle(void) {
    INT8 diff = ball_y - ai_paddle_y - (PADDLE_HEIGHT / 2);
    
    // Only move if ball is far enough away
    if (diff > AI_REACTION_THRESHOLD) {
        ai_paddle_y += AI_SPEED;
    } else if (diff < -AI_REACTION_THRESHOLD) {
        ai_paddle_y -= AI_SPEED;
    }
    
    // Clamp to screen bounds
    if (ai_paddle_y < MIN_PADDLE_Y) ai_paddle_y = MIN_PADDLE_Y;
    if (ai_paddle_y > MAX_PADDLE_Y) ai_paddle_y = MAX_PADDLE_Y;
}
```

### Difficulty Scaling

```c
UINT8 ai_difficulty = 1;  // 1 = easy, 3 = hard

void update_ai_paddle(void) {
    // Only update AI every N frames (lower = harder)
    if ((frame_counter % (4 - ai_difficulty)) != 0) {
        return;
    }
    
    // AI speed scales with difficulty
    UINT8 speed = ai_difficulty;
    
    if (ball_y > ai_paddle_y + PADDLE_HEIGHT / 2) {
        ai_paddle_y += speed;
    } else {
        ai_paddle_y -= speed;
    }
}
```

---

## Fixed-Point Math

### 8.8 Fixed Point

```c
// game.h
typedef INT16 fixed;

#define FP_SHIFT 8
#define FP_ONE (1 << FP_SHIFT)

// Conversion macros
#define INT_TO_FP(x) ((fixed)(x) << FP_SHIFT)
#define FP_TO_INT(x) ((x) >> FP_SHIFT)

// Math operations
#define FP_MUL(a, b) (((a) * (b)) >> FP_SHIFT)
#define FP_DIV(a, b) (((a) << FP_SHIFT) / (b))
```

### Usage Example (Smooth Ball Movement)

```c
// Ball position in fixed point
fixed ball_x_fp, ball_y_fp;
fixed ball_dx_fp, ball_dy_fp;

void init_ball(void) {
    ball_x_fp = INT_TO_FP(80);   // Screen center
    ball_y_fp = INT_TO_FP(72);
    ball_dx_fp = INT_TO_FP(1) + 128;  // 1.5 pixels per frame
    ball_dy_fp = INT_TO_FP(1);
}

void update_ball(void) {
    // Update position with sub-pixel precision
    ball_x_fp += ball_dx_fp;
    ball_y_fp += ball_dy_fp;
    
    // Convert to integer for sprite position
    UINT8 screen_x = FP_TO_INT(ball_x_fp);
    UINT8 screen_y = FP_TO_INT(ball_y_fp);
    
    move_sprite(SPRITE_BALL, screen_x + 8, screen_y + 16);
}
```

---

## Sound Effects

### Basic Sound Effect

```c
#include <gb/gb.h>

// Simple beep on channel 1
void play_beep(void) {
    // Enable channel 1
    NR52_REG = 0x80;  // Sound on
    NR51_REG = 0x11;  // Channel 1 to both speakers
    NR50_REG = 0x77;  // Max volume
    
    // Channel 1 settings
    NR10_REG = 0x00;  // No sweep
    NR11_REG = 0x80;  // 50% duty, no length
    NR12_REG = 0xF0;  // Max volume, no envelope
    NR13_REG = 0x00;  // Frequency low
    NR14_REG = 0x87;  // Frequency high + trigger
}

// Different pitch for paddle hit vs wall hit
void play_paddle_hit(void) {
    NR52_REG = 0x80;
    NR51_REG = 0x11;
    NR50_REG = 0x77;
    NR10_REG = 0x00;
    NR11_REG = 0x80;
    NR12_REG = 0xF3;  // Quick decay
    NR13_REG = 0x73;  // Higher pitch
    NR14_REG = 0x86;
}

void play_wall_hit(void) {
    NR52_REG = 0x80;
    NR51_REG = 0x11;
    NR50_REG = 0x77;
    NR10_REG = 0x00;
    NR11_REG = 0x40;  // 25% duty
    NR12_REG = 0xF1;
    NR13_REG = 0xD6;  // Lower pitch
    NR14_REG = 0x86;
}

void play_score(void) {
    // Descending tone using sweep
    NR52_REG = 0x80;
    NR51_REG = 0x11;
    NR50_REG = 0x77;
    NR10_REG = 0x79;  // Sweep down
    NR11_REG = 0x80;
    NR12_REG = 0xF0;
    NR13_REG = 0x00;
    NR14_REG = 0x87;
}
```

---

## Complete Mini-Game: Pong

### Combining Patterns

```c
// main.c - Complete Pong Example
#include <gb/gb.h>
#include "game.h"
#include "sprites.h"

void main(void) {
    // Initialize
    init_sprites();
    init_game();
    
    SHOW_SPRITES;
    DISPLAY_ON;
    
    while(1) {
        wait_vbl_done();
        handle_input();
        update_game();
        render_game();
    }
}

// game.c - Core Game Logic
#include <gb/gb.h>
#include "game.h"

// Game state
UINT8 paddle1_y, paddle2_y;
UINT8 ball_x, ball_y;
INT8 ball_dx, ball_dy;
UINT8 score1, score2;

UINT8 prev_joy, curr_joy;

void init_game(void) {
    paddle1_y = 72;
    paddle2_y = 72;
    ball_x = 80;
    ball_y = 72;
    ball_dx = 1;
    ball_dy = 1;
    score1 = 0;
    score2 = 0;
}

void handle_input(void) {
    prev_joy = curr_joy;
    curr_joy = joypad();
}

void update_game(void) {
    // Player 1 paddle
    if ((curr_joy & J_UP) && paddle1_y > 24) paddle1_y -= 2;
    if ((curr_joy & J_DOWN) && paddle1_y < 120) paddle1_y += 2;
    
    // AI paddle
    if (ball_y > paddle2_y + 12) paddle2_y++;
    if (ball_y < paddle2_y + 12) paddle2_y--;
    
    // Ball movement
    ball_x += ball_dx;
    ball_y += ball_dy;
    
    // Wall bounce
    if (ball_y <= 16 || ball_y >= 136) ball_dy = -ball_dy;
    
    // Paddle collision
    if (ball_x <= 16 && ball_y >= paddle1_y && ball_y <= paddle1_y + 24) {
        ball_dx = -ball_dx;
        ball_x = 17;
    }
    if (ball_x >= 144 && ball_y >= paddle2_y && ball_y <= paddle2_y + 24) {
        ball_dx = -ball_dx;
        ball_x = 143;
    }
    
    // Scoring
    if (ball_x < 8) {
        score2++;
        ball_x = 80;
        ball_y = 72;
    }
    if (ball_x > 152) {
        score1++;
        ball_x = 80;
        ball_y = 72;
    }
}

void render_game(void) {
    // Update sprite positions
    move_sprite(0, ball_x + 8, ball_y + 16);
    
    // Paddle 1 (3 sprites)
    move_sprite(1, 16, paddle1_y + 16);
    move_sprite(2, 16, paddle1_y + 24);
    move_sprite(3, 16, paddle1_y + 32);
    
    // Paddle 2 (3 sprites)
    move_sprite(4, 152, paddle2_y + 16);
    move_sprite(5, 152, paddle2_y + 24);
    move_sprite(6, 152, paddle2_y + 32);
}
```

---

## Template Checklist

When creating a new game, ensure:

- [ ] Project structure created
- [ ] Makefile configured
- [ ] `main.c` with game loop
- [ ] Sprite data defined
- [ ] Input handling implemented
- [ ] Game state management
- [ ] Collision detection (if needed)
- [ ] Score display (if needed)
- [ ] Sound effects (if needed)
- [ ] Compiles without errors
- [ ] Runs in emulator
