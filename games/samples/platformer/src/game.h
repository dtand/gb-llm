/**
 * @file    game.h
 * @brief   Game state and constants for Platformer
 * @game    platformer
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

// Screen dimensions
#define SCREEN_WIDTH        160
#define SCREEN_HEIGHT       144
#define SCREEN_TILES_X      20
#define SCREEN_TILES_Y      18

// Sprite offsets
#define SPRITE_X_OFFSET     8
#define SPRITE_Y_OFFSET     16

// Player constants
#define PLAYER_WIDTH        8
#define PLAYER_HEIGHT       8
#define PLAYER_START_X      20
#define PLAYER_START_Y      120
#define PLAYER_SPEED        2       // @tunable range:1-4 step:1 desc:"Horizontal movement speed"

// Physics
#define GRAVITY             1       // @tunable range:1-3 step:1 desc:"Downward acceleration per frame"
#define JUMP_VELOCITY       (-6)    // @tunable range:-8--4 step:1 desc:"Initial jump velocity (more negative = higher)"
#define JUMP_HOLD_REDUCTION 1       // @tunable range:1-2 step:1 desc:"Gravity reduction while holding jump"
#define TERMINAL_VELOCITY   4       // @tunable range:3-6 step:1 desc:"Maximum falling speed"
#define MAX_JUMP_HOLD       10      // @tunable range:5-15 step:1 desc:"Frames to hold A for max jump height"

// Level boundaries
#define MIN_X               0
#define MAX_X               (SCREEN_WIDTH - PLAYER_WIDTH)
#define MIN_Y               0
#define MAX_Y               (SCREEN_HEIGHT - PLAYER_HEIGHT)

// ============================================================
// TYPES
// ============================================================

/**
 * @brief   Main game state
 */
typedef struct {
    // Player position (in pixels)
    uint8_t player_x;
    int16_t player_y;       // Signed for calculations
    
    // Physics
    int8_t velocity_y;
    uint8_t on_ground;
    
    // Jump state
    uint8_t jumping;        // Currently in a jump
    uint8_t jump_held;      // A button still held since jump start
    uint8_t jump_timer;     // Frames A has been held
} GameState;

extern GameState game;
extern uint8_t prev_input;
extern uint8_t curr_input;

// ============================================================
// FUNCTIONS
// ============================================================

void game_init(void);
void game_handle_input(void);
void game_update(void);
void game_render(void);

#endif
