// Simon - Game Logic Header

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include "sprites.h"

// ===========================================
// GAME STATES
// ===========================================

#define STATE_TITLE         0   // Press START to begin
#define STATE_SHOW_PATTERN  1   // Computer showing pattern
#define STATE_PLAYER_INPUT  2   // Player repeating pattern
#define STATE_CORRECT       3   // Brief pause after correct input
#define STATE_GAME_OVER     4   // Wrong input - game over
#define STATE_WIN           5   // Completed max sequence

// ===========================================
// GAME STATE STRUCTURE
// ===========================================

typedef struct {
    // Pattern
    uint8_t sequence[MAX_SEQUENCE];     // The pattern to remember
    uint8_t sequence_length;            // Current pattern length
    uint8_t current_step;               // Current step being shown/input
    
    // Timing
    uint8_t flash_timer;                // Timer for button flash
    uint8_t pause_timer;                // Timer between flashes
    uint8_t input_timer;                // Timeout for player input
    
    // Input
    uint8_t lit_button;                 // Which button is currently lit (-1 for none)
    uint8_t last_keys;                  // Previous frame's key state
    
    // Score
    uint8_t score;                      // Rounds completed (sequence_length - 1)
    uint8_t high_score;                 // Best score this session
    
    // Game flow
    uint8_t state;                      // Current game state
    
} GameState;

// ===========================================
// BUTTON SCREEN POSITIONS (in tiles)
// ===========================================

// Each button is 4x4 tiles
#define BTN_SIZE    4

// Button positions (top-left corner of each 4x4 button)
#define BTN_UP_X    8
#define BTN_UP_Y    3

#define BTN_DOWN_X  8
#define BTN_DOWN_Y  11

#define BTN_LEFT_X  4
#define BTN_LEFT_Y  7

#define BTN_RIGHT_X 12
#define BTN_RIGHT_Y 7

// ===========================================
// FUNCTION DECLARATIONS
// ===========================================

void game_init(void);
void game_update(void);
void game_handle_input(void);
void game_draw(void);

// Button display
void draw_button(uint8_t button, uint8_t lit);
void draw_all_buttons(void);
void light_button(uint8_t button);
void unlight_button(uint8_t button);

// Pattern
void add_to_sequence(void);
void start_show_pattern(void);

// HUD
void draw_hud(void);
void draw_number(uint8_t x, uint8_t y, uint8_t num, uint8_t digits);
void draw_message(uint8_t msg);

// Messages
#define MSG_NONE    0
#define MSG_WATCH   1
#define MSG_PLAY    2
#define MSG_GAME_OVER 3
#define MSG_WIN     4

// Global game state
extern GameState game;

#endif
