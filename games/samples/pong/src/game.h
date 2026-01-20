/**
 * @file    game.h
 * @brief   Game state and constants for Pong
 * @game    pong
 * 
 * Defines the GameState structure, screen boundaries,
 * game constants, and function declarations.
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// SCREEN BOUNDARIES
// ============================================================
// Note: Sprites have an 8px X offset and 16px Y offset from screen coordinates

#define SCREEN_LEFT     8
#define SCREEN_RIGHT    168
#define SCREEN_TOP      16
#define SCREEN_BOTTOM   160

// ============================================================
// GAME CONSTANTS
// ============================================================

#define PADDLE_HEIGHT   24      // Paddle is 3 tiles tall (3 * 8px)
#define PADDLE_WIDTH    8       // Paddle is 1 tile wide
#define BALL_SIZE       8       // Ball is 1 tile (8x8)
#define PADDLE_SPEED    2       // Pixels per frame when moving
#define BALL_SPEED_INIT 1       // Starting ball speed

// Paddle X positions (fixed, paddles only move vertically)
#define PADDLE_LEFT_X   16
#define PADDLE_RIGHT_X  152

// Paddle Y movement bounds
#define PADDLE_MIN_Y    (SCREEN_TOP)
#define PADDLE_MAX_Y    (SCREEN_BOTTOM - PADDLE_HEIGHT)

// Ball movement bounds
#define BALL_MIN_X      (SCREEN_LEFT)
#define BALL_MAX_X      (SCREEN_RIGHT - BALL_SIZE)
#define BALL_MIN_Y      (SCREEN_TOP)
#define BALL_MAX_Y      (SCREEN_BOTTOM - BALL_SIZE)

// Win condition
#define WIN_SCORE       5

// ============================================================
// GAME STATE
// ============================================================

/**
 * @brief   Complete game state structure
 * 
 * Contains all mutable game data: positions, velocities,
 * scores, and state flags.
 */
typedef struct {
    // Paddle positions (Y only, X is fixed)
    uint8_t paddle_left_y;
    uint8_t paddle_right_y;
    
    // Ball position
    uint8_t ball_x;
    uint8_t ball_y;
    
    // Ball velocity (signed for direction)
    int8_t ball_dx;
    int8_t ball_dy;
    
    // Ball speed magnitude (increases on paddle hits)
    uint8_t ball_speed;
    
    // Player scores
    uint8_t score_left;
    uint8_t score_right;
    
    // State flags
    uint8_t game_over;
    uint8_t paused;
} GameState;

// Global game state instance
extern GameState game;

// Input tracking (current and previous frame)
extern uint8_t prev_input;
extern uint8_t curr_input;

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/** @brief Initialize game state to starting values */
void game_init(void);

/** @brief Read and store current joypad input */
void game_handle_input(void);

/** @brief Update all game logic (paddles, ball, collisions) */
void game_update(void);

/** @brief Update sprite positions to match game state */
void game_render(void);

/** @brief Reset ball to center after scoring */
void game_reset_ball(void);

/** @brief Play a short beep sound effect */
void sound_play_beep(void);

#endif
