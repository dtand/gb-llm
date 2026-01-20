/**
 * @file    game.h
 * @brief   Game state and constants for Bounce
 * @game    bounce
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

#define BALL_SIZE           8
#define SPRITE_OFFSET_X     8
#define SPRITE_OFFSET_Y     16

#define BALL_MIN_X          SPRITE_OFFSET_X
#define BALL_MAX_X          (SPRITE_OFFSET_X + 160 - BALL_SIZE)
#define BALL_MIN_Y          SPRITE_OFFSET_Y
#define BALL_MAX_Y          (SPRITE_OFFSET_Y + 144 - BALL_SIZE)

// Animation
#define ANIM_FRAMES         4       // Number of animation frames
#define ANIM_SPEED          8       // Game frames per animation frame

// ============================================================
// GAME STATE
// ============================================================

typedef struct {
    // Position
    uint8_t x;
    uint8_t y;
    
    // Velocity (signed)
    int8_t dx;
    int8_t dy;
    
    // Animation
    uint8_t frame_counter;  // Increments each frame
    uint8_t anim_frame;     // Current animation frame (0-3)
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
