/**
 * @file    game.h
 * @brief   Game state and constants for Memory Card Game
 * @game    memory
 */

#ifndef GAME_H
#define GAME_H

#include <stdint.h>

// ============================================================
// GAME CONSTANTS
// ============================================================

// Game states
#define STATE_SELECTING_FIRST   0   // Selecting first card
#define STATE_SELECTING_SECOND  1   // Selecting second card
#define STATE_SHOWING_CARDS     2   // Showing both cards briefly
#define STATE_VICTORY           3   // All pairs matched

// Card states
#define CARD_FACE_DOWN      0
#define CARD_FACE_UP        1
#define CARD_MATCHED        2

// Timing
#define SHOW_DELAY          45  // @tunable range:30-90 step:15 desc:"Frames to show mismatched cards"

// ============================================================
// DATA STRUCTURES
// ============================================================

/**
 * @brief   Individual card data
 */
typedef struct {
    uint8_t symbol;     // Card symbol (0-7)
    uint8_t state;      // FACE_DOWN, FACE_UP, or MATCHED
} Card;

/**
 * @brief   Complete game state
 */
typedef struct {
    Card cards[16];         // 4x4 grid of cards
    
    uint8_t cursor_x;       // Cursor grid position (0-3)
    uint8_t cursor_y;       // Cursor grid position (0-3)
    
    uint8_t first_card;     // Index of first selected card (0-15)
    uint8_t second_card;    // Index of second selected card (0-15)
    
    uint8_t state;          // Current game state
    uint8_t show_timer;     // Timer for showing mismatched cards
    
    uint8_t pairs_matched;  // Number of pairs found
    uint8_t moves;          // Number of moves (pairs attempted)
} GameState;

// ============================================================
// GLOBAL STATE
// ============================================================

extern GameState game;

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/**
 * @brief   Initialize game state for new game
 */
void game_init(void);

/**
 * @brief   Handle player input
 */
void game_handle_input(void);

/**
 * @brief   Update game logic
 */
void game_update(void);

/**
 * @brief   Render game state to screen
 */
void game_render(void);

#endif /* GAME_H */
