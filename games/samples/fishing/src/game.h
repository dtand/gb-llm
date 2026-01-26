#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include "sprites.h"

// Game states
#define STATE_TITLE     0
#define STATE_IDLE      1   // Waiting to cast
#define STATE_CAST      2   // Casting animation
#define STATE_WAITING   3   // Line in water, waiting for bite
#define STATE_BITE      4   // Fish is biting!
#define STATE_CATCH     5   // Successfully caught
#define STATE_MISS      6   // Missed the fish
#define STATE_REEL      7   // Reeling in animation

// Bobber position
#define BOBBER_X        10
#define BOBBER_Y_IDLE   6
#define BOBBER_Y_WATER  10

// Game state structure
typedef struct {
    uint8_t state;
    
    // Fish catch count
    uint8_t fish_caught;
    uint8_t fish_missed;
    
    // Timing
    uint16_t wait_timer;     // Time until bite
    uint16_t bite_timer;     // Time remaining to react
    uint16_t anim_timer;     // Animation timer
    
    // Bobber animation
    uint8_t bobber_y;
    uint8_t bobber_frame;
    
    // Water animation
    uint8_t water_frame;
    uint8_t water_timer;
    
    // RNG
    uint16_t seed;
    
    // Input
    uint8_t joypad_prev;
} GameState;

extern GameState game;

// Functions
void game_init(void);
void game_update(void);
void draw_scene(void);
void draw_hud(void);
void draw_bobber(void);
void clear_bobber(void);
void draw_bite_indicator(void);
void clear_bite_indicator(void);
void start_cast(void);
void start_waiting(void);

#endif
