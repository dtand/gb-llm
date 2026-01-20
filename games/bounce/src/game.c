/**
 * @file    game.c
 * @brief   Core game logic for Bounce
 * @game    bounce
 * 
 * Demonstrates sprite animation with frame cycling.
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

// ============================================================
// GLOBAL STATE
// ============================================================

GameState game;
uint8_t prev_input = 0;
uint8_t curr_input = 0;

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    // Center ball horizontally, start near bottom
    game.x = SPRITE_OFFSET_X + 80 - (BALL_SIZE >> 1);
    game.y = BALL_MAX_Y - 20;
    
    // Initial velocity - toss it up and to the right
    game.dx = 2;
    game.dy = -6;
    
    // Animation
    game.frame_counter = 0;
    game.anim_frame = 0;
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Handle input
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // START: reset
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        game_init();
    }
    
    // A button: kick the ball upward
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        game.dy = KICK_VELOCITY;
    }
    
    // D-pad: apply horizontal force
    if (curr_input & J_LEFT) {
        if (game.dx > -MAX_VELOCITY) game.dx--;
    }
    if (curr_input & J_RIGHT) {
        if (game.dx < MAX_VELOCITY) game.dx++;
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update ball position and animation
 */
void game_update(void) {
    int16_t new_x, new_y;
    
    // Update animation frame
    game.frame_counter++;
    game.anim_frame = (game.frame_counter / ANIM_SPEED) % ANIM_FRAMES;
    
    // Apply gravity (accumulating velocity)
    game.dy += GRAVITY;
    
    // Cap terminal velocity
    if (game.dy > MAX_VELOCITY) game.dy = MAX_VELOCITY;
    if (game.dy < -MAX_VELOCITY) game.dy = -MAX_VELOCITY;
    
    // Calculate new position
    new_x = game.x + game.dx;
    new_y = game.y + game.dy;
    
    // Bounce off left/right walls
    if (new_x <= BALL_MIN_X) {
        new_x = BALL_MIN_X;
        game.dx = -game.dx;
    } else if (new_x >= BALL_MAX_X) {
        new_x = BALL_MAX_X;
        game.dx = -game.dx;
    }
    
    // Bounce off ceiling
    if (new_y <= BALL_MIN_Y) {
        new_y = BALL_MIN_Y;
        game.dy = -game.dy;
    }
    
    // Bounce off floor with energy loss
    if (new_y >= BALL_MAX_Y) {
        new_y = BALL_MAX_Y;
        // Reverse and reduce velocity (energy loss)
        game.dy = -game.dy;
        game.dy = (game.dy * (4 - BOUNCE_DAMPING)) >> 2;
        // Also reduce horizontal velocity slightly
        if (game.dx > 0) game.dx--;
        else if (game.dx < 0) game.dx++;
    }
    
    game.x = (uint8_t)new_x;
    game.y = (uint8_t)new_y;
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Update sprite position and animation frame
 */
void game_render(void) {
    // Update sprite tile to current animation frame
    set_sprite_tile(SPRITE_BALL, TILE_BALL_0 + game.anim_frame);
    
    // Update position
    move_sprite(SPRITE_BALL, game.x, game.y);
}
