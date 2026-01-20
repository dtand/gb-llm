/**
 * @file    game.h
 * @brief   Game state and constants for Runner
 * @game    runner
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

#define PLAYER_X            24      // Fixed X position (sprite coords)
#define GROUND_Y            120     // Ground level (sprite coords)
#define GRAVITY             1       // Pixels per frame squared
#define JUMP_VELOCITY       (-8)    // Initial jump velocity
#define SCROLL_SPEED        1       // Pixels per frame

// Background map is 32 tiles wide = 256 pixels
#define BKG_MAP_WIDTH       32
#define GROUND_TILE_Y       17      // Tile row for ground (17 * 8 = 136)

// ============================================================
// GAME STATE
// ============================================================

typedef struct {
    // Player state
    uint8_t player_y;       // Sprite Y position
    int8_t velocity_y;      // Vertical velocity (negative = up)
    uint8_t on_ground;      // Is player on ground?
    
    // Scrolling
    uint8_t scroll_x;       // Current SCX value (0-255, wraps)
    
    // Score (frames survived)
    uint16_t score;
    
    // State flags
    uint8_t game_over;
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
void game_setup_background(void);

#endif
