/**
 * @file    game.h
 * @brief   Game state and constants for Falling Block Puzzle
 * @game    puzzle
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

// Playfield dimensions (in grid cells)
#define GRID_WIDTH          10
#define GRID_HEIGHT         18  // Screen is 18 tiles tall (144px / 8)

// Playfield position on screen (in tiles)
#define GRID_OFFSET_X       5   // Center the 10-wide grid on 20-wide screen
#define GRID_OFFSET_Y       0

// Piece types
#define PIECE_I             0
#define PIECE_O             1
#define PIECE_T             2
#define PIECE_S             3
#define PIECE_Z             4
#define PIECE_L             5
#define PIECE_J             6
#define NUM_PIECES          7

// Timing (in frames)
#define DROP_SPEED_NORMAL   30  // @tunable range:15-60 step:5 desc:"Frames between drops (higher = slower)"
#define DROP_SPEED_FAST     3   // @tunable range:1-5 step:1 desc:"Fast drop speed in frames"

// ============================================================
// TYPES
// ============================================================

/**
 * @brief   Current falling piece state
 */
typedef struct {
    uint8_t type;           // Piece type (0-6)
    uint8_t rotation;       // Rotation state (0-3)
    int8_t x;               // Grid X position
    int8_t y;               // Grid Y position
} Piece;

/**
 * @brief   Main game state
 */
typedef struct {
    // Playfield grid (0 = empty, 1 = filled)
    uint8_t grid[GRID_HEIGHT][GRID_WIDTH];
    
    // Current falling piece
    Piece current;
    
    // Next piece preview
    uint8_t next_piece;
    
    // Timing
    uint8_t drop_timer;
    uint8_t drop_speed;
    
    // Score
    uint16_t score;
    uint16_t lines;
    
    // State
    uint8_t game_over;
    uint8_t needs_redraw;
    
    // Previous piece position for flicker-free rendering
    int8_t prev_x;
    int8_t prev_y;
    uint8_t prev_type;
    uint8_t prev_rotation;
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
