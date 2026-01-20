/**
 * @file    game.c
 * @brief   Core game logic for Pong
 * @game    pong
 * 
 * Handles player input, ball physics, AI opponent,
 * collision detection, scoring, and game state management.
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

// Frame counter for AI timing and pseudo-random
static uint8_t frame_count = 0;

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state to starting values
 * 
 * Centers paddles and ball, sets initial velocity,
 * resets scores, and clears state flags.
 */
void game_init(void) {
    // Center paddles vertically
    game.paddle_left_y = 80;
    game.paddle_right_y = 80;
    
    // Center ball on screen
    game.ball_x = 84;
    game.ball_y = 80;
    
    // Initial ball direction: moving right and down
    game.ball_dx = BALL_SPEED_INIT;
    game.ball_dy = BALL_SPEED_INIT;
    game.ball_speed = BALL_SPEED_INIT;
    
    // Reset scores
    game.score_left = 0;
    game.score_right = 0;
    
    // Clear state flags
    game.game_over = 0;
    game.paused = 0;
}

/**
 * @brief   Reset ball to center after a point is scored
 * 
 * Centers the ball, resets speed to initial value,
 * and reverses horizontal direction.
 */
void game_reset_ball(void) {
    game.ball_x = 84;
    game.ball_y = 80;
    game.ball_speed = BALL_SPEED_INIT;
    
    // Reverse horizontal direction from last point
    game.ball_dx = (game.ball_dx > 0) ? -BALL_SPEED_INIT : BALL_SPEED_INIT;
    
    // Use frame count for pseudo-random vertical direction
    game.ball_dy = (frame_count & 1) ? BALL_SPEED_INIT : -BALL_SPEED_INIT;
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Read and store current joypad input
 * 
 * Saves previous frame's input for edge detection,
 * then reads current joypad state. Also handles
 * START button for pause/restart.
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // START button: pause toggle or restart after game over
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        if (game.game_over) {
            game_init();
        } else {
            game.paused = !game.paused;
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update player-controlled left paddle
 * 
 * Moves paddle up/down based on D-pad input,
 * clamped to screen boundaries.
 */
static void update_player_paddle(void) {
    if (curr_input & J_UP) {
        if (game.paddle_left_y > PADDLE_MIN_Y) {
            game.paddle_left_y -= PADDLE_SPEED;
        }
    }
    if (curr_input & J_DOWN) {
        if (game.paddle_left_y < PADDLE_MAX_Y) {
            game.paddle_left_y += PADDLE_SPEED;
        }
    }
}

/**
 * @brief   Update AI-controlled right paddle
 * 
 * Simple AI that follows the ball's Y position.
 * Throttled to update every 2 frames and has a
 * dead zone to make it beatable.
 */
static void update_ai_paddle(void) {
    // Only update every 2 frames to make AI beatable
    if ((frame_count & 1) != 0) {
        return;
    }
    
    uint8_t paddle_center = game.paddle_right_y + (PADDLE_HEIGHT >> 1);
    uint8_t ball_center = game.ball_y + (BALL_SIZE >> 1);
    
    // Dead zone of 4 pixels to avoid jitter
    if (ball_center > paddle_center + 4) {
        if (game.paddle_right_y < PADDLE_MAX_Y) {
            game.paddle_right_y += 1;
        }
    } else if (ball_center < paddle_center - 4) {
        if (game.paddle_right_y > PADDLE_MIN_Y) {
            game.paddle_right_y -= 1;
        }
    }
}

/**
 * @brief   Update ball position and handle collisions
 * 
 * Moves ball by current velocity, bounces off walls,
 * checks paddle collisions, and handles scoring.
 */
static void update_ball(void) {
    // Move ball by velocity
    game.ball_x += game.ball_dx;
    game.ball_y += game.ball_dy;
    
    // ---- Wall collisions (top/bottom) ----
    if (game.ball_y <= BALL_MIN_Y) {
        game.ball_y = BALL_MIN_Y;
        game.ball_dy = -game.ball_dy;
        sound_play_beep();
    }
    if (game.ball_y >= BALL_MAX_Y) {
        game.ball_y = BALL_MAX_Y;
        game.ball_dy = -game.ball_dy;
        sound_play_beep();
    }
    
    // ---- Left paddle collision ----
    if (game.ball_dx < 0 && game.ball_x <= PADDLE_LEFT_X + PADDLE_WIDTH) {
        // Check Y overlap with paddle
        if (game.ball_y + BALL_SIZE >= game.paddle_left_y &&
            game.ball_y <= game.paddle_left_y + PADDLE_HEIGHT) {
            
            game.ball_x = PADDLE_LEFT_X + PADDLE_WIDTH;
            game.ball_dx = (int8_t)(-game.ball_dx);
            
            // Increase speed on paddle hit (max 3)
            if (game.ball_speed < 3) {
                game.ball_speed++;
                game.ball_dx = (game.ball_dx < 0) 
                    ? (int8_t)(-game.ball_speed) 
                    : (int8_t)(game.ball_speed);
            }
            sound_play_beep();
        }
    }
    
    // ---- Right paddle collision ----
    if (game.ball_dx > 0 && game.ball_x + BALL_SIZE >= PADDLE_RIGHT_X) {
        // Check Y overlap with paddle
        if (game.ball_y + BALL_SIZE >= game.paddle_right_y &&
            game.ball_y <= game.paddle_right_y + PADDLE_HEIGHT) {
            
            game.ball_x = PADDLE_RIGHT_X - BALL_SIZE;
            game.ball_dx = (int8_t)(-game.ball_dx);
            
            // Increase speed on paddle hit (max 3)
            if (game.ball_speed < 3) {
                game.ball_speed++;
                game.ball_dx = (game.ball_dx < 0) 
                    ? (int8_t)(-game.ball_speed) 
                    : (int8_t)(game.ball_speed);
            }
            sound_play_beep();
        }
    }
    
    // ---- Scoring: ball passed left edge ----
    if (game.ball_x <= BALL_MIN_X) {
        game.score_right++;
        if (game.score_right >= WIN_SCORE) {
            game.game_over = 1;
        } else {
            game_reset_ball();
        }
    }
    
    // ---- Scoring: ball passed right edge ----
    if (game.ball_x >= BALL_MAX_X) {
        game.score_left++;
        if (game.score_left >= WIN_SCORE) {
            game.game_over = 1;
        } else {
            game_reset_ball();
        }
    }
}

/**
 * @brief   Update all game logic
 * 
 * Main update function called once per frame.
 * Skips updates when paused or game over.
 */
void game_update(void) {
    if (game.paused || game.game_over) {
        return;
    }
    
    frame_count++;
    
    update_player_paddle();
    update_ai_paddle();
    update_ball();
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Update sprite positions to match game state
 * 
 * Moves all sprites (ball and both paddles) to their
 * current positions in the game state.
 */
void game_render(void) {
    // Ball sprite
    move_sprite(SPRITE_BALL, game.ball_x, game.ball_y);
    
    // Left paddle: 3 sprites stacked vertically
    move_sprite(SPRITE_PADDLE_L, PADDLE_LEFT_X, game.paddle_left_y);
    move_sprite(SPRITE_PADDLE_L + 1, PADDLE_LEFT_X, game.paddle_left_y + 8);
    move_sprite(SPRITE_PADDLE_L + 2, PADDLE_LEFT_X, game.paddle_left_y + 16);
    
    // Right paddle: 3 sprites stacked vertically
    move_sprite(SPRITE_PADDLE_R, PADDLE_RIGHT_X, game.paddle_right_y);
    move_sprite(SPRITE_PADDLE_R + 1, PADDLE_RIGHT_X, game.paddle_right_y + 8);
    move_sprite(SPRITE_PADDLE_R + 2, PADDLE_RIGHT_X, game.paddle_right_y + 16);
}

// ============================================================
// SOUND
// ============================================================

/**
 * @brief   Play a short beep sound effect
 * 
 * Uses channel 1 (square wave) with quick decay.
 * Called on wall and paddle collisions.
 */
void sound_play_beep(void) {
    NR52_REG = 0x80;    // Sound on
    NR51_REG = 0x11;    // Channel 1 to both speakers
    NR50_REG = 0x77;    // Max volume both sides
    
    NR10_REG = 0x00;    // No sweep
    NR11_REG = 0x80;    // 50% duty cycle
    NR12_REG = 0xF3;    // Volume 15, decrease, step 3
    NR13_REG = 0x83;    // Frequency low byte
    NR14_REG = 0x87;    // Frequency high + trigger
}
