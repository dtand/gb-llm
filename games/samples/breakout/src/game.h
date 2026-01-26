/**
 * @file    game.h
 * @brief   Game state and constants for Breakout
 * @game    breakout
 * 
 * Defines the game state structure, brick layout,
 * ball physics, and screen boundaries.
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// SCREEN CONSTANTS
// ============================================================

#define SCREEN_WIDTH        160
#define SCREEN_HEIGHT       144

// Sprite offset (GB sprites are positioned with 8,16 as top-left visible)
#define SPRITE_OFFSET_X     8
#define SPRITE_OFFSET_Y     16

// ============================================================
// BRICK LAYOUT
// ============================================================

#define BRICK_ROWS          5       // @tunable range:3-6 step:1 desc:"Number of brick rows"
#define BRICK_COLS          10      // @tunable range:8-10 step:1 desc:"Number of bricks per row"
#define BRICK_WIDTH         16      // Pixels (2 tiles)
#define BRICK_HEIGHT        8       // Pixels (1 tile)
#define BRICK_START_Y       24      // Y position of top brick row (in pixels)

// Total bricks
#define TOTAL_BRICKS        (BRICK_ROWS * BRICK_COLS)

// ============================================================
// PADDLE CONSTANTS
// ============================================================

#define PADDLE_WIDTH        16      // Pixels (2 sprites)
#define PADDLE_HEIGHT       8
#define PADDLE_Y            128     // Fixed Y position
#define PADDLE_SPEED        3       // @tunable range:1-5 step:1 desc:"Paddle movement speed in pixels per frame"

// Paddle screen boundaries (for sprite position)
#define PADDLE_MIN_X        SPRITE_OFFSET_X
#define PADDLE_MAX_X        (SPRITE_OFFSET_X + SCREEN_WIDTH - PADDLE_WIDTH)

// ============================================================
// BALL CONSTANTS
// ============================================================

#define BALL_SIZE           8       // 8x8 pixels
#define BALL_SPEED          2       // @tunable range:1-4 step:1 desc:"Ball base speed in pixels per frame"

// Ball boundaries (for sprite position)
#define BALL_MIN_X          SPRITE_OFFSET_X
#define BALL_MAX_X          (SPRITE_OFFSET_X + SCREEN_WIDTH - BALL_SIZE)
#define BALL_MIN_Y          SPRITE_OFFSET_Y
#define BALL_MAX_Y          (SPRITE_OFFSET_Y + SCREEN_HEIGHT)

// ============================================================
// GAME STATE
// ============================================================

#define INITIAL_LIVES       3       // @tunable range:1-5 step:1 desc:"Starting number of lives"

/**
 * @brief   Complete game state
 */
typedef struct {
    // Paddle state
    uint8_t paddle_x;           // Sprite X position
    
    // Ball state
    uint8_t ball_x;             // Sprite X position
    uint8_t ball_y;             // Sprite Y position
    int8_t ball_dx;             // X velocity (signed)
    int8_t ball_dy;             // Y velocity (signed)
    uint8_t ball_active;        // Ball is in play (not waiting)
    
    // Brick state (1 = present, 0 = destroyed)
    uint8_t bricks[BRICK_ROWS][BRICK_COLS];
    uint8_t bricks_remaining;
    
    // Score and lives
    uint8_t score;
    uint8_t lives;
    
    // State flags
    uint8_t game_over;
    uint8_t game_won;
} GameState;

// Global game state instance
extern GameState game;

// Input tracking
extern uint8_t prev_input;
extern uint8_t curr_input;

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/** @brief Initialize game state and brick layout */
void game_init(void);

/** @brief Read and process joypad input */
void game_handle_input(void);

/** @brief Update ball, paddle, and collision */
void game_update(void);

/** @brief Update sprite positions */
void game_render(void);

/** @brief Set up initial brick layout on background */
void game_setup_bricks(void);

#endif
