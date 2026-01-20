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
#define GROUND_Y            136     // Ground level for sprite (sprite Y coord where feet touch ground)
#define PLAYER_HEIGHT       8       // Player sprite height
#define GRAVITY             0       // Accumulated manually for slower fall
#define JUMP_VELOCITY       (-4)    // Initial jump velocity (smaller = slower rise)
#define SCROLL_SPEED        1       // Pixels per frame

// Background map is 32 tiles wide = 256 pixels
#define BKG_MAP_WIDTH       32
#define GROUND_TILE_Y       16      // Tile row for ground (16 * 8 = 128 screen Y)

// ============================================================
// GAME STATE
// ============================================================

typedef struct {
    // Player state
    int16_t player_y;       // Sprite Y position (signed for jump math)
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
