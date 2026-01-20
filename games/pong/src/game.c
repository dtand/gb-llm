#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

// Global game state
GameState game;

// Input tracking
uint8_t prev_input = 0;
uint8_t curr_input = 0;

// Frame counter for AI timing
uint8_t frame_count = 0;

void init_game(void) {
    // Center paddles vertically
    game.paddle_left_y = 80;   // Roughly center
    game.paddle_right_y = 80;
    
    // Center ball
    game.ball_x = 84;
    game.ball_y = 80;
    
    // Initial ball direction (moving right and down)
    game.ball_dx = BALL_SPEED_INIT;
    game.ball_dy = BALL_SPEED_INIT;
    game.ball_speed = BALL_SPEED_INIT;
    
    // Reset scores
    game.score_left = 0;
    game.score_right = 0;
    
    // Game is active
    game.game_over = 0;
    game.paused = 0;
}

void handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // Check for pause toggle (START button, just pressed)
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        if (game.game_over) {
            // Restart game
            init_game();
        } else {
            game.paused = !game.paused;
        }
    }
}

void update_player_paddle(void) {
    // Player controls left paddle with D-pad
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

void update_ai_paddle(void) {
    // Simple AI: follow the ball with some delay
    // Only update every 2 frames to make it beatable
    if ((frame_count & 1) == 0) {
        uint8_t paddle_center = game.paddle_right_y + (PADDLE_HEIGHT / 2);
        uint8_t ball_center = game.ball_y + (BALL_SIZE / 2);
        
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
}

void update_ball(void) {
    // Move ball
    game.ball_x += game.ball_dx;
    game.ball_y += game.ball_dy;
    
    // Top/bottom wall collision
    if (game.ball_y <= BALL_MIN_Y) {
        game.ball_y = BALL_MIN_Y;
        game.ball_dy = -game.ball_dy;
        play_beep();
    }
    if (game.ball_y >= BALL_MAX_Y) {
        game.ball_y = BALL_MAX_Y;
        game.ball_dy = -game.ball_dy;
        play_beep();
    }
    
    // Left paddle collision
    if (game.ball_dx < 0) {  // Moving left
        if (game.ball_x <= PADDLE_LEFT_X + PADDLE_WIDTH) {
            if (game.ball_y + BALL_SIZE >= game.paddle_left_y &&
                game.ball_y <= game.paddle_left_y + PADDLE_HEIGHT) {
                // Hit paddle!
                game.ball_x = PADDLE_LEFT_X + PADDLE_WIDTH;
                game.ball_dx = (int8_t)(-game.ball_dx);
                
                // Speed up slightly (max 3)
                if (game.ball_speed < 3) {
                    game.ball_speed++;
                    if (game.ball_dx < 0) game.ball_dx = (int8_t)(-game.ball_speed);
                    else game.ball_dx = (int8_t)(game.ball_speed);
                }
                play_beep();
            }
        }
    }
    
    // Right paddle collision
    if (game.ball_dx > 0) {  // Moving right
        if (game.ball_x + BALL_SIZE >= PADDLE_RIGHT_X) {
            if (game.ball_y + BALL_SIZE >= game.paddle_right_y &&
                game.ball_y <= game.paddle_right_y + PADDLE_HEIGHT) {
                // Hit paddle!
                game.ball_x = PADDLE_RIGHT_X - BALL_SIZE;
                game.ball_dx = (int8_t)(-game.ball_dx);
                
                // Speed up slightly
                if (game.ball_speed < 3) {
                    game.ball_speed++;
                    if (game.ball_dx < 0) game.ball_dx = (int8_t)(-game.ball_speed);
                    else game.ball_dx = (int8_t)(game.ball_speed);
                }
                play_beep();
            }
        }
    }
    
    // Scoring - ball passed left edge
    if (game.ball_x <= BALL_MIN_X) {
        game.score_right++;
        if (game.score_right >= WIN_SCORE) {
            game.game_over = 1;
        } else {
            reset_ball();
        }
    }
    
    // Scoring - ball passed right edge
    if (game.ball_x >= BALL_MAX_X) {
        game.score_left++;
        if (game.score_left >= WIN_SCORE) {
            game.game_over = 1;
        } else {
            reset_ball();
        }
    }
}

void reset_ball(void) {
    // Center the ball
    game.ball_x = 84;
    game.ball_y = 80;
    
    // Reset speed
    game.ball_speed = BALL_SPEED_INIT;
    
    // Reverse horizontal direction, randomize vertical a bit
    game.ball_dx = -game.ball_dx;
    if (game.ball_dx > 0) game.ball_dx = BALL_SPEED_INIT;
    else game.ball_dx = -BALL_SPEED_INIT;
    
    // Use frame count for pseudo-random vertical direction
    game.ball_dy = (frame_count & 1) ? BALL_SPEED_INIT : -BALL_SPEED_INIT;
}

void update_game(void) {
    if (game.paused || game.game_over) {
        return;
    }
    
    frame_count++;
    
    update_player_paddle();
    update_ai_paddle();
    update_ball();
}

void render_game(void) {
    // Update ball sprite
    move_sprite(SPRITE_BALL, game.ball_x, game.ball_y);
    
    // Update left paddle (3 sprites stacked vertically)
    move_sprite(SPRITE_PADDLE_L, PADDLE_LEFT_X, game.paddle_left_y);
    move_sprite(SPRITE_PADDLE_L + 1, PADDLE_LEFT_X, game.paddle_left_y + 8);
    move_sprite(SPRITE_PADDLE_L + 2, PADDLE_LEFT_X, game.paddle_left_y + 16);
    
    // Update right paddle
    move_sprite(SPRITE_PADDLE_R, PADDLE_RIGHT_X, game.paddle_right_y);
    move_sprite(SPRITE_PADDLE_R + 1, PADDLE_RIGHT_X, game.paddle_right_y + 8);
    move_sprite(SPRITE_PADDLE_R + 2, PADDLE_RIGHT_X, game.paddle_right_y + 16);
}

void play_beep(void) {
    // Simple beep sound on channel 1
    NR52_REG = 0x80;  // Sound on
    NR51_REG = 0x11;  // Channel 1 to both speakers
    NR50_REG = 0x77;  // Max volume
    
    NR10_REG = 0x00;  // No sweep
    NR11_REG = 0x80;  // 50% duty cycle
    NR12_REG = 0xF3;  // Volume envelope: start at 15, decrease
    NR13_REG = 0x83;  // Frequency low byte
    NR14_REG = 0x87;  // Frequency high + trigger
}
