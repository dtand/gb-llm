/**
 * @file    game.h
 * @brief   Game state and constants for Timer Challenge
 * @game    timer
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

// Game states
#define STATE_TITLE         0
#define STATE_WAITING       1   // Waiting for random delay
#define STATE_READY         2   // "GO!" displayed, timing reaction
#define STATE_RESULT        3   // Showing result
#define STATE_FALSE_START   4   // Pressed too early

// Timing
#define MIN_DELAY_MS        1000    // @tunable range:500-2000 step:250 desc:"Minimum wait time in milliseconds"
#define MAX_DELAY_MS        3000    // @tunable range:2000-5000 step:500 desc:"Maximum wait time in milliseconds"
#define TIMER_FREQ_HZ       1000    // Target: ~1ms per tick

// ============================================================
// TYPES
// ============================================================

/**
 * @brief   Main game state
 */
typedef struct {
    uint8_t state;              // Current game state
    
    // Timing (volatile because modified in ISR)
    volatile uint16_t timer_ms;     // Millisecond counter
    uint16_t delay_target;          // Random delay before "GO!"
    uint16_t reaction_time;         // Measured reaction time
    
    // Best score
    uint16_t best_time;
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

// Timer interrupt handler
void timer_isr(void);

#endif
