/**
 * @file    game.h
 * @brief   Game state and constants for Snake
 * @game    snake
 * 
 * Defines the game state structure, snake body buffer,
 * screen boundaries, and movement constants.
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// SCREEN BOUNDARIES (grid-based)
// ============================================================
// Game area: 160x144 pixels = 20x18 grid cells (8x8 each)
// Sprites offset: X+8, Y+16

#define GRID_SIZE       8       // Pixels per grid cell
#define GRID_WIDTH      20      // Cells across (160/8)
#define GRID_HEIGHT     18      // Cells down (144/8)

// Screen boundaries in pixels (accounting for sprite offset)
#define SCREEN_LEFT     8
#define SCREEN_TOP      16
#define SCREEN_RIGHT    (SCREEN_LEFT + GRID_WIDTH * GRID_SIZE)
#define SCREEN_BOTTOM   (SCREEN_TOP + GRID_HEIGHT * GRID_SIZE)

// ============================================================
// GAME CONSTANTS
// ============================================================

#define SNAKE_MAX_LENGTH    64      // Maximum snake segments
#define SNAKE_START_LENGTH  3       // Initial snake length
#define MOVE_DELAY          8       // Frames between moves (lower = faster)

// ============================================================
// DIRECTION CONSTANTS
// ============================================================

#define DIR_NONE    0
#define DIR_UP      1
#define DIR_DOWN    2
#define DIR_LEFT    3
#define DIR_RIGHT   4

// ============================================================
// DATA STRUCTURES
// ============================================================

/**
 * @brief   Position on the grid
 */
typedef struct {
    uint8_t x;      // Grid X (0 to GRID_WIDTH-1)
    uint8_t y;      // Grid Y (0 to GRID_HEIGHT-1)
} Position;

/**
 * @brief   Complete game state
 */
typedef struct {
    // Snake body stored as circular buffer
    Position body[SNAKE_MAX_LENGTH];
    uint8_t head_idx;       // Index of head in buffer
    uint8_t tail_idx;       // Index of tail in buffer
    uint8_t length;         // Current snake length
    
    // Movement
    uint8_t direction;      // Current direction
    uint8_t next_direction; // Buffered next direction
    uint8_t move_timer;     // Frames until next move
    
    // Food position
    Position food;
    
    // Score
    uint8_t score;
    
    // State flags
    uint8_t game_over;
    uint8_t paused;
} GameState;

// Global game state instance
extern GameState game;

// Input tracking
extern uint8_t prev_input;
extern uint8_t curr_input;

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/** @brief Initialize game state to starting values */
void game_init(void);

/** @brief Read and store current joypad input */
void game_handle_input(void);

/** @brief Update all game logic (movement, collision, food) */
void game_update(void);

/** @brief Update sprite positions to match game state */
void game_render(void);

/** @brief Spawn food at random empty position */
void game_spawn_food(void);

/** @brief Get pseudo-random number (0-255) */
uint8_t random_byte(void);

#endif
