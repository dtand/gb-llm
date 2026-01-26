/**
 * @file    game.h
 * @brief   Game state and constants for Parallax Scroller
 * @game    parallax
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

// Screen dimensions in tiles
#define SCREEN_TILES_X      20
#define SCREEN_TILES_Y      18

// Parallax layer scanline boundaries
#define SKY_START           0
#define MOUNTAIN_START      32
#define HILLS_START         64
#define GROUND_START        96
#define SCREEN_END          144

// Scroll speeds (as bit shifts for division)
// Ground = full speed, hills = half, mountains = quarter
#define SCROLL_SPEED        2       // @tunable range:1-4 step:1 desc:"Base scroll speed in pixels per frame"

// ============================================================
// TYPES
// ============================================================

/**
 * @brief   Main game state
 */
typedef struct {
    // Master scroll position (16-bit for smooth sub-pixel)
    int16_t scroll_x;
    
    // Computed layer scroll values
    uint8_t scroll_sky;
    uint8_t scroll_mountain;
    uint8_t scroll_hills;
    uint8_t scroll_ground;
    
    // Input state
    uint8_t moving;
    int8_t direction;   // -1 = left, 0 = still, 1 = right
    uint8_t fast_mode;
} GameState;

extern GameState game;
extern uint8_t prev_input;
extern uint8_t curr_input;

// Layer scroll values (accessed by interrupt)
extern volatile uint8_t layer_scroll_mountain;
extern volatile uint8_t layer_scroll_hills;
extern volatile uint8_t layer_scroll_ground;

// ============================================================
// FUNCTIONS
// ============================================================

void game_init(void);
void game_handle_input(void);
void game_update(void);
void game_render(void);

// LCD interrupt handler
void lcd_isr(void);

#endif
