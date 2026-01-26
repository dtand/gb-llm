#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include "sprites.h"

// Game states
#define STATE_TITLE     0
#define STATE_IDLE      1
#define STATE_SPINNING  2
#define STATE_STOPPING  3
#define STATE_RESULT    4
#define STATE_GAMEOVER  5

// Reel positions
#define REEL1_X         3
#define REEL2_X         9
#define REEL3_X         15
#define REELS_Y         7

// Spin timing
#define SPIN_FRAMES     8       // @tunable range:4-16 step:2 desc:"Frames between symbol changes"
#define MIN_SPINS       20      // @tunable range:10-40 step:5 desc:"Minimum spins before stopping"
#define STOP_DELAY      15      // @tunable range:10-30 step:5 desc:"Delay between each reel stopping"

// Starting coins
#define START_COINS     100     // @tunable range:50-500 step:50 desc:"Initial coin balance"
#define BET_AMOUNT      10      // @tunable range:5-25 step:5 desc:"Coins per spin"

// Game state structure
typedef struct {
    uint8_t state;
    
    // Current reel symbols (0-4)
    uint8_t reel1;
    uint8_t reel2;
    uint8_t reel3;
    
    // Spin counters
    uint8_t spin_timer;
    uint8_t spin_count1;
    uint8_t spin_count2;
    uint8_t spin_count3;
    uint8_t stop_timer;
    
    // Which reels are still spinning
    uint8_t reel1_spinning;
    uint8_t reel2_spinning;
    uint8_t reel3_spinning;
    
    // Player coins
    uint16_t coins;
    
    // Last win amount
    uint16_t last_win;
    
    // RNG state
    uint16_t seed;
    
    // Result display timer
    uint8_t result_timer;
    
    // Input state
    uint8_t joypad_prev;
} GameState;

extern GameState game;

// Function declarations
void game_init(void);
void game_update(void);
void draw_reels(void);
void draw_coins(void);
void draw_win(uint16_t amount);
void clear_win(void);
void start_spin(void);
uint16_t calculate_payout(void);

#endif
