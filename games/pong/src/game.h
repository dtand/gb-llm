#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// Screen boundaries (accounting for sprite offset)
#define SCREEN_LEFT     8
#define SCREEN_RIGHT    168
#define SCREEN_TOP      16
#define SCREEN_BOTTOM   160

// Game constants
#define PADDLE_HEIGHT   24
#define PADDLE_WIDTH    8
#define BALL_SIZE       8
#define PADDLE_SPEED    2
#define BALL_SPEED_INIT 1

// Paddle positions (X coordinates)
#define PADDLE_LEFT_X   16
#define PADDLE_RIGHT_X  152

// Paddle Y bounds
#define PADDLE_MIN_Y    (SCREEN_TOP)
#define PADDLE_MAX_Y    (SCREEN_BOTTOM - PADDLE_HEIGHT)

// Ball bounds
#define BALL_MIN_X      (SCREEN_LEFT)
#define BALL_MAX_X      (SCREEN_RIGHT - BALL_SIZE)
#define BALL_MIN_Y      (SCREEN_TOP)
#define BALL_MAX_Y      (SCREEN_BOTTOM - BALL_SIZE)

// Winning score
#define WIN_SCORE       5

// Game state structure
typedef struct {
    // Paddle positions (Y only, X is fixed)
    uint8_t paddle_left_y;
    uint8_t paddle_right_y;
    
    // Ball position
    uint8_t ball_x;
    uint8_t ball_y;
    
    // Ball velocity
    int8_t ball_dx;
    int8_t ball_dy;
    
    // Ball speed (increases over time)
    uint8_t ball_speed;
    
    // Scores
    uint8_t score_left;
    uint8_t score_right;
    
    // Game state flags
    uint8_t game_over;
    uint8_t paused;
} GameState;

// Global game state
extern GameState game;

// Input state
extern uint8_t prev_input;
extern uint8_t curr_input;

// Function declarations
void init_game(void);
void handle_input(void);
void update_game(void);
void render_game(void);
void reset_ball(void);
void play_beep(void);

#endif
